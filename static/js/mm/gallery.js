/* MM.gallery: product gallery (arrows, thumbnails, counter) and a zoomable lightbox (docs/08-ui-modules.md). */
(function (MM) {
  "use strict";
  var LIGHTBOX = "gallery-lightbox";
  var MAX_SCALE = 4;
  var TAP_SCALE = 2.5;
  var STEP = 1.5;
  var EASE = "transform 200ms cubic-bezier(0.22, 1, 0.36, 1)";
  var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var openLightbox = null; /* assigned by setupLightbox */

  function isRtl(el) { return window.getComputedStyle(el).direction === "rtl"; }
  function counterText(index, total) { return MM.fmt.faDigits(index + 1) + " / " + MM.fmt.faDigits(total); }

  /* ---------- page gallery ---------- */
  function setupGallery(root) {
    if (root.dataset.galleryReady === "1") return;
    root.dataset.galleryReady = "1";

    var track = root.querySelector("[data-gallery-track]");
    if (!track) return;
    var slides = Array.prototype.slice.call(root.querySelectorAll("[data-gallery-slide]"));
    var thumbs = Array.prototype.slice.call(root.querySelectorAll("[data-gallery-thumb]"));
    var counter = root.querySelector("[data-gallery-counter]");
    var current = 0;
    var ticking = false;

    function nearest() {
      var origin = track.getBoundingClientRect().left;
      var best = 0;
      var bestDistance = Infinity;
      slides.forEach(function (slide, i) {
        var distance = Math.abs(slide.getBoundingClientRect().left - origin);
        if (distance < bestDistance) { best = i; bestDistance = distance; }
      });
      return best;
    }

    /* Scroll only the thumbnail strip, never the page. */
    function reveal(thumb) {
      var strip = thumb.parentNode;
      if (!strip || strip.scrollWidth <= strip.clientWidth) return;
      var s = strip.getBoundingClientRect();
      var t = thumb.getBoundingClientRect();
      strip.scrollBy({ left: t.left - s.left - (s.width - t.width) / 2, behavior: "auto" });
    }

    function mark(index) {
      current = index;
      thumbs.forEach(function (thumb, i) {
        var on = i === index;
        thumb.classList.toggle("border-base-content", on);
        thumb.classList.toggle("opacity-60", !on);
        thumb.setAttribute("aria-current", on ? "true" : "false");
        if (on) reveal(thumb);
      });
      if (counter) counter.textContent = counterText(index, slides.length);
    }

    function go(index) {
      var target = (index + slides.length) % slides.length;
      var delta = slides[target].getBoundingClientRect().left - track.getBoundingClientRect().left;
      track.scrollBy({ left: delta, behavior: reduced ? "auto" : "smooth" });
    }

    var api = {
      go: go,
      images: function () {
        return slides.map(function (slide) {
          var img = slide.querySelector("img");
          return { src: img.getAttribute("data-full") || img.currentSrc || img.src, alt: img.alt || "" };
        });
      },
    };

    track.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { ticking = false; mark(nearest()); });
    }, { passive: true });

    var prev = root.querySelector("[data-gallery-prev]");
    var next = root.querySelector("[data-gallery-next]");
    if (prev) prev.addEventListener("click", function () { go(current - 1); });
    if (next) next.addEventListener("click", function () { go(current + 1); });
    thumbs.forEach(function (thumb, i) { thumb.addEventListener("click", function () { go(i); }); });

    track.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      var forward = (event.key === "ArrowLeft") === isRtl(root); /* in RTL the next image is on the left */
      go(current + (forward ? 1 : -1));
      event.preventDefault();
    });

    track.addEventListener("click", function (event) {
      if (event.target.closest("[data-gallery-slide]") && openLightbox) openLightbox(api, current);
    });
    var zoom = root.querySelector("[data-gallery-zoom]");
    if (zoom) zoom.addEventListener("click", function () { if (openLightbox) openLightbox(api, current); });

    mark(0);
  }

  /* ---------- lightbox with zoom ---------- */
  function setupLightbox(dialog) {
    if (dialog.dataset.lbReady === "1") return;
    dialog.dataset.lbReady = "1";

    var stage = dialog.querySelector("[data-lb-stage]");
    var img = dialog.querySelector("[data-lb-image]");
    var counter = dialog.querySelector("[data-lb-counter]");
    var prev = dialog.querySelector("[data-lb-prev]");
    var next = dialog.querySelector("[data-lb-next]");
    var zoomIn = dialog.querySelector("[data-lb-zoom-in]");
    var zoomOut = dialog.querySelector("[data-lb-zoom-out]");
    if (!stage || !img) return;

    var owner = null;
    var images = [];
    var index = 0;
    var scale = 1;
    var tx = 0;
    var ty = 0;
    var pointers = {};
    var gesture = null;

    function apply(animate) {
      img.style.transition = animate ? EASE : "none";
      img.style.transform = "translate(" + tx + "px, " + ty + "px) scale(" + scale + ")";
      stage.classList.toggle("cursor-grab", scale > 1);
      stage.classList.toggle("cursor-zoom-in", scale <= 1);
      if (zoomOut) zoomOut.disabled = scale <= 1;
      if (zoomIn) zoomIn.disabled = scale >= MAX_SCALE;
    }

    function clampPan() {
      var mx = Math.max(0, (stage.clientWidth * scale - stage.clientWidth) / 2);
      var my = Math.max(0, (stage.clientHeight * scale - stage.clientHeight) / 2);
      tx = Math.min(mx, Math.max(-mx, tx));
      ty = Math.min(my, Math.max(-my, ty));
    }

    /* cx, cy: the point that stays fixed, relative to the stage center */
    function zoomTo(value, cx, cy, animate) {
      var target = Math.min(MAX_SCALE, Math.max(1, value));
      var ratio = target / scale;
      tx = cx - (cx - tx) * ratio;
      ty = cy - (cy - ty) * ratio;
      scale = target;
      if (scale === 1) { tx = 0; ty = 0; }
      clampPan();
      apply(animate);
    }

    function relative(x, y) {
      var r = stage.getBoundingClientRect();
      return { x: x - r.left - r.width / 2, y: y - r.top - r.height / 2 };
    }

    function show(i) {
      index = (i + images.length) % images.length;
      img.src = images[index].src;
      img.alt = images[index].alt;
      scale = 1;
      tx = 0;
      ty = 0;
      apply(false);
      if (counter) counter.textContent = counterText(index, images.length);
      var single = images.length < 2;
      if (prev) prev.hidden = single;
      if (next) next.hidden = single;
    }

    function pair() {
      var ids = Object.keys(pointers);
      return ids.length >= 2 ? [pointers[ids[0]], pointers[ids[1]]] : null;
    }
    function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y) || 1; }
    function mid(a, b) { return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; }

    stage.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      try { stage.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      var two = pair();
      if (two) {
        gesture = { pinch: true, moved: true, dPrev: dist(two[0], two[1]), midPrev: mid(two[0], two[1]) };
      } else {
        gesture = { pinch: false, moved: false, x0: e.clientX, y0: e.clientY, tx0: tx, ty0: ty };
      }
    });

    stage.addEventListener("pointermove", function (e) {
      if (!pointers[e.pointerId] || !gesture) return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      var two = pair();
      if (gesture.pinch) {
        if (!two) return;
        var d = dist(two[0], two[1]);
        var m = mid(two[0], two[1]);
        var p = relative(m.x, m.y);
        zoomTo(scale * d / gesture.dPrev, p.x, p.y, false);
        tx += m.x - gesture.midPrev.x;
        ty += m.y - gesture.midPrev.y;
        clampPan();
        apply(false);
        gesture.dPrev = d;
        gesture.midPrev = m;
        return;
      }
      var dx = e.clientX - gesture.x0;
      var dy = e.clientY - gesture.y0;
      if (Math.abs(dx) > 6 || Math.abs(dy) > 6) gesture.moved = true;
      if (scale > 1 && gesture.moved) {
        tx = gesture.tx0 + dx;
        ty = gesture.ty0 + dy;
        clampPan();
        apply(false);
      }
    });

    function release(e) {
      if (!pointers[e.pointerId]) return;
      var ended = gesture;
      delete pointers[e.pointerId];
      var left = Object.keys(pointers);
      if (left.length === 1 && ended && ended.pinch) { /* one finger stays: continue as a pan */
        var rest = pointers[left[0]];
        gesture = { pinch: false, moved: true, x0: rest.x, y0: rest.y, tx0: tx, ty0: ty };
        return;
      }
      if (left.length) return;
      gesture = null;
      if (!ended || ended.pinch || e.type === "pointercancel") return;
      var dx = e.clientX - ended.x0;
      var dy = e.clientY - ended.y0;
      if (!ended.moved) { /* tap or click: toggle zoom at that point */
        var p = relative(e.clientX, e.clientY);
        zoomTo(scale > 1 ? 1 : TAP_SCALE, p.x, p.y, true);
      } else if (scale === 1 && Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) { /* swipe to the next image */
        var forward = isRtl(dialog) ? dx > 0 : dx < 0;
        show(index + (forward ? 1 : -1));
      }
    }
    stage.addEventListener("pointerup", release);
    stage.addEventListener("pointercancel", release);

    stage.addEventListener("wheel", function (e) {
      e.preventDefault();
      var p = relative(e.clientX, e.clientY);
      zoomTo(scale * Math.exp(-e.deltaY * 0.0015), p.x, p.y, false);
    }, { passive: false });

    if (zoomIn) zoomIn.addEventListener("click", function () { zoomTo(scale * STEP, 0, 0, true); });
    if (zoomOut) zoomOut.addEventListener("click", function () { zoomTo(scale / STEP, 0, 0, true); });
    if (prev) prev.addEventListener("click", function () { show(index - 1); });
    if (next) next.addEventListener("click", function () { show(index + 1); });

    dialog.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        if (images.length < 2) return;
        var forward = (e.key === "ArrowLeft") === isRtl(dialog);
        show(index + (forward ? 1 : -1));
        e.preventDefault();
      } else if (e.key === "+" || e.key === "=") {
        zoomTo(scale * STEP, 0, 0, true);
      } else if (e.key === "-") {
        zoomTo(scale / STEP, 0, 0, true);
      } else if (e.key === "0") {
        zoomTo(1, 0, 0, true);
      }
    });

    dialog.addEventListener("close", function () {
      pointers = {};
      gesture = null;
      if (owner) owner.go(index); /* the page gallery follows the last image seen */
      owner = null;
      img.removeAttribute("src");
    });

    openLightbox = function (gallery, start) {
      images = gallery.images();
      if (!images.length) return;
      owner = gallery;
      show(start);
      MM.ui.dialog.open(LIGHTBOX);
    };
  }

  MM.init("gallery", function (root) {
    MM.each(root, "[data-lightbox]", setupLightbox);
    MM.each(root, "[data-gallery]", setupGallery);
  });
})(window.MM);
