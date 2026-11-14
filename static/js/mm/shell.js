/* MM.shell: cart badge count, search suggestion panel, and styleguide demos. */
(function (MM) {
  "use strict";

  /* Cart badge: hidden at zero, Persian digits, no layout shift (P3 wires the data). */
  window.malmalSetCartCount = function (count) {
    var numeric = Number(count) || 0;
    document.querySelectorAll("[data-cart-count]").forEach(function (el) {
      el.textContent = MM.fmt.faDigits(numeric);
      el.classList.toggle("invisible", numeric <= 0);
    });
  };

  /* Live search suggestions: show the panel only when it has content */
  function syncSuggestPanel() {
    var panel = document.getElementById("search-suggest");
    if (!panel) return;
    var hasContent = panel.innerHTML.trim().length > 0;
    panel.classList.toggle("hidden", !hasContent);
  }

  document.addEventListener("click", function (e) {
    var panel = document.getElementById("search-suggest");
    if (panel && !panel.classList.contains("hidden")) {
      var form = panel.closest("form");
      if (form && !form.contains(e.target)) {
        panel.classList.add("hidden");
      }
    }

    var toastTrigger = e.target.closest ? e.target.closest("[data-demo-toast]") : null;
    if (toastTrigger) {
      MM.ui.toast(
        toastTrigger.getAttribute("data-demo-toast") || "تغییرات ذخیره شد",
        { level: toastTrigger.getAttribute("data-demo-toast-level") || "info" }
      );
      return;
    }

    var confirmTrigger = e.target.closest ? e.target.closest("[data-demo-confirm]") : null;
    if (confirmTrigger) {
      MM.ui.confirm({
        title: confirmTrigger.getAttribute("data-confirm-title") || "",
        message: confirmTrigger.getAttribute("data-demo-confirm") || "آیا مطمئن هستید؟",
        confirmLabel: confirmTrigger.getAttribute("data-confirm-label") || "",
        cancelLabel: confirmTrigger.getAttribute("data-confirm-cancel") || "",
        tone: confirmTrigger.getAttribute("data-confirm-tone") || "",
      }).then(function (ok) {
        if (ok) MM.ui.toast("تایید شد", { level: "success" });
      });
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var panel = document.getElementById("search-suggest");
    if (panel) panel.classList.add("hidden");
  });

  MM.init("shell", function (root) {
    MM.each(root, "#search-suggest", syncSuggestPanel);
  });
})(window.MM);
