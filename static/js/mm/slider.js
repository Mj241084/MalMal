/* MM.slider: scroll-snap carousel with arrows, dots and calm autoplay (docs/02 §8.1, docs/04 §7). */
(function (MM) {
  "use strict";
  var ACTIVE = "bg-base-content";
  var IDLE = "bg-base-300";

  function setup(root) {
    if (root.dataset.sliderReady === "1") return;
    root.dataset.sliderReady = "1";

    var track = root.querySelector("[data-slider-track]");
    if (!track) return;
    var slides = Array.prototype.slice.call(track.children);
    var dots = Array.prototype.slice.call(root.querySelectorAll("[data-slider-dot]"));
    if (slides.length < 2) return;

    var interval = parseInt(root.getAttribute("data-autoplay") || "0", 10);
    var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    var timer = null;
    var paused = false;
    var visible = true;
    var current = 0;
    var ticking = false;

    function nearest() {
      var origin = track.getBoundingClientRect().left;
      var best = 0;
      var bestDistance = Infinity;
      slides.forEach(function (slide, index) {
        var distance = Math.abs(slide.getBoundingClientRect().left - origin);
        if (distance < bestDistance) { best = index; bestDistance = distance; }
      });
      return best;
    }

    function mark(index) {
      current = index;
      dots.forEach(function (dot, i) {
        var on = i === index;
        dot.setAttribute("aria-current", on ? "true" : "false");
        var circle = dot.firstElementChild;
        if (circle) { circle.classList.toggle(ACTIVE, on); circle.classList.toggle(IDLE, !on); }
      });
    }

    function go(index) {
      var target = (index + slides.length) % slides.length;
      var delta = slides[target].getBoundingClientRect().left - track.getBoundingClientRect().left;
      track.scrollBy({ left: delta, behavior: reduced ? "auto" : "smooth" });
    }

    track.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { ticking = false; mark(nearest()); });
    }, { passive: true });

    var prev = root.querySelector("[data-slider-prev]");
    var next = root.querySelector("[data-slider-next]");
    if (prev) prev.addEventListener("click", function () { go(current - 1); });
    if (next) next.addEventListener("click", function () { go(current + 1); });
    dots.forEach(function (dot, i) { dot.addEventListener("click", function () { go(i); }); });

    track.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      var rtl = window.getComputedStyle(root).direction === "rtl";
      var forward = (event.key === "ArrowLeft") === rtl; /* in RTL the next slide is on the left */
      go(current + (forward ? 1 : -1));
      event.preventDefault();
    });

    ["pointerenter", "focusin"].forEach(function (name) { root.addEventListener(name, function () { paused = true; }); });
    ["pointerleave", "focusout"].forEach(function (name) { root.addEventListener(name, function () { paused = false; }); });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) { visible = entries[0].isIntersecting; }).observe(root);
    }

    if (interval && !reduced) {
      timer = window.setInterval(function () {
        if (!root.isConnected) { window.clearInterval(timer); return; }
        if (!paused && visible && !document.hidden) go(current + 1);
      }, interval);
    }
    mark(0);
  }

  MM.init("slider", function (root) { MM.each(root, "[data-slider]", setup); });
})(window.MM);
