/* MM.panel: panel-only behaviour (docs/08-ui-modules.md): toast bridge, copy button, select-all,
   search panel, live money hints. */
(function (MM) {
  "use strict";

  /* HX-Trigger: {"mm:toast": {"message": "...", "level": "success"}} */
  document.addEventListener("mm:toast", function (event) {
    var detail = event.detail || {};
    if (detail.message) MM.ui.toast(detail.message, { level: detail.level || "info" });
  });

  /* ----- money hints: «۱٬۲۵۰٬۰۰۰ تومان» under a [data-toman-hint] field; [data-discount-from] adds the percent ----- */
  function amount(input) {
    var digits = MM.fmt.enDigits(input.value).replace(/[^0-9]/g, "");
    return digits ? parseInt(digits, 10) : 0;
  }
  function grouped(number) {
    return MM.fmt.faDigits(String(number).replace(/\B(?=(\d{3})+(?!\d))/g, "٬"));
  }
  function hint(input) {
    var out = input.parentNode.querySelector("[data-money-out]");
    if (!out) {
      out = document.createElement("p");
      out.setAttribute("data-money-out", "");
      out.className = "text-label text-ink-3 mt-1 min-h-5";
      input.insertAdjacentElement("afterend", out);
    }
    var value = amount(input);
    var text = value ? grouped(value) + " تومان" : "";
    if (value && input.hasAttribute("data-discount-from") && input.form) {
      var price = input.form.querySelector("[name='price']");
      var sale = price ? amount(price) : 0;
      if (sale > 0 && value > sale) {
        text += " — " + MM.fmt.faDigits(Math.round(((value - sale) * 100) / value)) + "٪ تخفیف";
      }
    }
    out.textContent = text;
  }

  document.addEventListener("input", function (event) {
    var el = event.target;
    if (!el.matches || !el.matches("[data-toman-hint]")) return;
    hint(el);
    if (el.name === "price" && el.form) {
      var compare = el.form.querySelector("[data-discount-from]");
      if (compare) hint(compare);
    }
  });

  MM.init("panel-money", function (root) {
    MM.each(root, "[data-toman-hint]", hint);
  });

  /* ----- clicks: copy, select-all, search panel ----- */
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!target.closest) return;

    var copy = target.closest("[data-copy]");
    if (copy) {
      var source = document.getElementById(copy.getAttribute("data-copy"));
      if (!source || !navigator.clipboard) {
        MM.ui.toast("کپی نشد؛ متن را دستی انتخاب کنید", { level: "error" });
        return;
      }
      navigator.clipboard.writeText(source.value !== undefined ? source.value : source.textContent).then(
        function () { MM.ui.toast("مشخصات کپی شد", { level: "success" }); },
        function () { MM.ui.toast("کپی نشد؛ متن را دستی انتخاب کنید", { level: "error" }); }
      );
      return;
    }

    var all = target.closest("[data-check-all]");
    if (all && all.form) {
      all.form.querySelectorAll("input[name='order']:not(:disabled)").forEach(function (box) { box.checked = all.checked; });
      return;
    }

    var panel = document.getElementById("search-results");
    if (panel && !target.closest("[data-panel-search]")) panel.classList.add("hidden");
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    var swapped = event.detail && event.detail.target;
    if (swapped && swapped.id === "search-results") swapped.classList.toggle("hidden", !swapped.innerHTML.trim());
  });
})(window.MM);
