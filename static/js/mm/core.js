/* MM namespace: tiny helpers shared by every UI module (docs/08-ui-modules.md). */
(function () {
  "use strict";
  var MM = (window.MM = window.MM || {});
  var FA = "۰۱۲۳۴۵۶۷۸۹";
  var AR = "٠١٢٣٤٥٦٧٨٩";

  MM.fmt = {
    faDigits: function (value) {
      return String(value == null ? "" : value).replace(/[0-9]/g, function (d) { return FA.charAt(+d); });
    },
    enDigits: function (value) {
      return String(value == null ? "" : value)
        .replace(/[۰-۹]/g, function (d) { return String(FA.indexOf(d)); })
        .replace(/[٠-٩]/g, function (d) { return String(AR.indexOf(d)); });
    },
  };

  /* Run fn(root) on first load and after every HTMX swap. htmx fires onLoad for the NEW root element,
     so selectors must include the root itself: use MM.each. Initializers must be idempotent. */
  MM.init = function (name, fn) {
    MM.init.registry[name] = fn;
    if (window.htmx) window.htmx.onLoad(fn);
    else document.addEventListener("DOMContentLoaded", function () { fn(document.body); });
  };
  MM.init.registry = {};

  MM.each = function (root, selector, fn) {
    if (!root || !root.querySelectorAll) return;
    if (root.matches && root.matches(selector)) fn(root);
    root.querySelectorAll(selector).forEach(fn);
  };
})();
