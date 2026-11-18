/* MM.forms: Persian digits while typing (server normalizes to ASCII), focus management after swaps. */
(function (MM) {
  "use strict";

  function convert(input) {
    var start = input.selectionStart;
    var end = input.selectionEnd;
    var next = MM.fmt.faDigits(MM.fmt.enDigits(input.value));
    if (input.hasAttribute("data-digits-only")) next = next.replace(/[^۰-۹]/g, "");
    if (input.hasAttribute("data-number-only")) next = next.replace(/[^۰-۹٫.\-]/g, "");
    if (next === input.value) return;
    input.value = next;
    try {
      if (start != null) input.setSelectionRange(Math.min(start, next.length), Math.min(end, next.length));
    } catch (e) { /* input types without selection support */ }
  }

  document.addEventListener("input", function (event) {
    var el = event.target;
    if (el && el.matches && el.matches("[data-fa-digits]")) convert(el);
  });

  /* The URL and the server only ever see ASCII digits, even for a field the user types into with Persian ones. */
  document.addEventListener("htmx:configRequest", function (event) {
    var root = event.detail.elt;
    if (!root || !root.querySelectorAll) return;
    var fields = root.matches && root.matches("[data-fa-digits][name]") ? [root] : root.querySelectorAll("[data-fa-digits][name]");
    Array.prototype.forEach.call(fields, function (field) {
      var value = event.detail.parameters[field.name];
      if (typeof value === "string") event.detail.parameters[field.name] = MM.fmt.enDigits(value);
    });
  });

  function focusFirst(root) {
    if (!root || !root.querySelector) return;
    var target = root.querySelector("[aria-invalid='true'], [data-autofocus]");
    if (!target && root !== document.body) {
      var scope = root.matches && root.matches("[data-focus-on-swap]") ? root : root.querySelector("[data-focus-on-swap]");
      if (scope) target = scope.querySelector("input:not([type='hidden']), select, textarea");
    }
    if (target && target.focus) target.focus();
  }

  MM.init("forms", function (root) {
    MM.each(root, "[data-fa-digits]", convert);
    focusFirst(root);
  });
})(window.MM);