/* MM.scroll: eased mouse-wheel scrolling and smooth in-page anchors (docs/08-ui-modules.md).
   Mouse wheels only: trackpads, touch, keyboard and scrollbar drags stay native. */
(function (MM) {
  "use strict";
  var EASE = 0.14; /* share of the remaining distance covered per 60fps frame */
  var FRAME = 1000 / 60;
  var MIN_WHEEL = 40; /* smaller wheel deltas come from trackpads: leave them native */
  var LINE_PX = 32;
  var SYNC_PX = 3; /* a bigger gap between scrollY and our position means someone else scrolled */
  var ANCHOR_GAP = 8;

  var reduced = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var root = document.documentElement;
  var current = 0;
  var target = 0;
  var raf = 0;
  var last = 0;

  function off() { return !!(reduced && reduced.matches); }
  function maxY() { return Math.max(0, root.scrollHeight - window.innerHeight); }
  function clamp(y) { return Math.min(Math.max(y, 0), maxY()); }
  function put(y) { window.scrollTo({ top: y, behavior: "instant" }); }

  function stop() {
    if (raf) window.cancelAnimationFrame(raf);
    raf = 0;
  }

  function sync() {
    stop();
    current = target = window.scrollY;
  }

  function tick(now) {
    var dt = Math.min(now - last, 50);
    last = now;
    target = clamp(target);
    current += (target - current) * (1 - Math.pow(1 - EASE, dt / FRAME));
    if (Math.abs(target - current) < 0.5) {
      current = target;
      raf = 0;
      put(current);
      return;
    }
    put(current);
    raf = window.requestAnimationFrame(tick);
  }

  function glideTo(y) {
    if (!raf) current = window.scrollY;
    target = clamp(y);
    if (!raf) {
      last = window.performance.now();
      raf = window.requestAnimationFrame(tick);
    }
  }

  /* The page must not move while a modal is open or the viewport is locked */
  function locked() {
    return (
      window.getComputedStyle(root).overflowY === "hidden" ||
      window.getComputedStyle(document.body).overflowY === "hidden"
    );
  }

  /* True when the wheel belongs to an inner scroller (rail, menu, modal) that can still move that way */
  function nestedScroller(node, dy) {
    var el = node instanceof Element ? node : null;
    while (el && el !== document.body && el !== root) {
      if (el.tagName === "DIALOG" && el.open) return true;
      var overflow = window.getComputedStyle(el).overflowY;
      if ((overflow === "auto" || overflow === "scroll") && el.scrollHeight > el.clientHeight + 1) {
        var room = dy > 0 ? el.scrollHeight - el.clientHeight - el.scrollTop > 1 : el.scrollTop > 0;
        if (room) return true;
      }
      el = el.parentElement;
    }
    return false;
  }

  function pixels(event) {
    if (event.deltaMode === 1) return event.deltaY * LINE_PX;
    if (event.deltaMode === 2) return event.deltaY * window.innerHeight;
    return event.deltaY;
  }

  function onWheel(event) {
    if (event.defaultPrevented || off()) return;
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
    var dy = pixels(event);
    if (Math.abs(dy) < MIN_WHEEL || locked() || nestedScroller(event.target, dy)) return;
    event.preventDefault();
    glideTo((raf ? target : window.scrollY) + dy);
  }

  function headerGap() {
    var header = document.querySelector("header.sticky");
    return (header ? header.getBoundingClientRect().height : 0) + ANCHOR_GAP;
  }

  function onClick(event) {
    if (event.defaultPrevented || off() || event.button !== 0) return;
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    var link = event.target instanceof Element ? event.target.closest("a[href^='#']") : null;
    if (!link) return;
    var hash = link.getAttribute("href").slice(1);
    var dest = null;
    try {
      dest = hash ? document.getElementById(decodeURIComponent(hash)) : null;
    } catch (err) {
      dest = null;
    }
    if (!dest) return;
    event.preventDefault();
    glideTo(dest.getBoundingClientRect().top + window.scrollY - headerGap());
    if (window.history.pushState) window.history.pushState(null, "", "#" + hash);
    if (!dest.hasAttribute("tabindex")) dest.setAttribute("tabindex", "-1");
    dest.focus({ preventScroll: true });
  }

  /* Anything that scrolls the page without us (keyboard, scrollbar, trackpad) wins and resets our position */
  window.addEventListener("scroll", function () {
    if (raf) {
      if (Math.abs(window.scrollY - current) > SYNC_PX) sync();
    } else {
      current = target = window.scrollY;
    }
  }, { passive: true });

  document.addEventListener("wheel", onWheel, { passive: false });
  document.addEventListener("click", onClick);

  MM.scroll = {
    to: function (y) {
      if (off()) put(clamp(y));
      else glideTo(y);
    },
  };
})(window.MM);
