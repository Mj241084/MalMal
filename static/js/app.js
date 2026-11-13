/* MAL MAL core client behaviors: theme persistence, HTMX error toasts, and focus management. */
(function () {
  var THEME_KEY = "malmal.theme";
  var mql = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function resolveDark(pref) {
    if (pref === "dark") return true;
    if (pref === "light") return false;
    return !!(mql && mql.matches);
  }

  function applyTheme(pref) {
    var normalized = pref === "light" || pref === "dark" ? pref : "system";
    var dark = resolveDark(normalized);
    document.documentElement.setAttribute("data-theme", dark ? "malmal-dark" : "malmal");
    document.documentElement.dataset.themePref = normalized;
    syncThemeButtons(normalized);
  }

  function syncThemeButtons(pref) {
    document.querySelectorAll("[data-theme-choice]").forEach(function (btn) {
      var active = btn.getAttribute("data-theme-choice") === pref;
      btn.setAttribute("aria-pressed", active ? "true" : "false");
      btn.classList.toggle("bg-base-300", active);
      btn.classList.toggle("text-base-content", active);
    });
  }

  function setTheme(pref) {
    try {
      localStorage.setItem(THEME_KEY, pref);
    } catch (e) {
      /* Storage unavailable (private mode / blocked): still apply in memory. */
    }
    applyTheme(pref);
  }

  function getSavedTheme() {
    try {
      return localStorage.getItem(THEME_KEY) || "system";
    } catch (e) {
      return "system";
    }
  }

  if (mql && mql.addEventListener) {
    mql.addEventListener("change", function () {
      if (getSavedTheme() === "system") {
        applyTheme("system");
      }
    });
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("[data-theme-choice]") : null;
    if (btn) {
      setTheme(btn.getAttribute("data-theme-choice"));
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    syncThemeButtons(document.documentElement.dataset.themePref || getSavedTheme());
  });

  /* Toast notifications */
  function showToast(message, level) {
    var container = document.getElementById("toasts");
    if (!container) return;
    var alertClass = "alert";
    if (level === "error") alertClass += " alert-error";
    else if (level === "success") alertClass += " alert-success";
    else if (level === "warning") alertClass += " alert-warning";
    else alertClass += " alert-info";

    var box = document.createElement("div");
    box.setAttribute("role", "alert");
    box.className = alertClass + " surface-float text-small max-w-sm";

    var span = document.createElement("span");
    span.textContent = message;
    box.appendChild(span);

    container.appendChild(box);
    window.setTimeout(function () {
      if (box.parentNode) {
        box.parentNode.removeChild(box);
      }
    }, 5000);
  }

  window.malmalToast = showToast;

  document.addEventListener("click", function (e) {
    var trigger = e.target.closest ? e.target.closest("[data-demo-toast]") : null;
    if (trigger) {
      showToast(
        trigger.getAttribute("data-demo-toast") || "تغییرات ذخیره شد",
        trigger.getAttribute("data-demo-toast-level") || "info"
      );
    }
  });

  /* HTMX global error handlers */
  document.body.addEventListener("htmx:responseError", function () {
    showToast("ارتباط برقرار نشد. دوباره تلاش کنید", "error");
  });
  document.body.addEventListener("htmx:sendError", function () {
    showToast("ارتباط برقرار نشد. دوباره تلاش کنید", "error");
  });

  /* Move focus into swapped modal/form target when appropriate */
  document.body.addEventListener("htmx:afterSwap", function (e) {
    var target = e.detail && e.detail.target;
    if (!target || !target.querySelector) return;
    if (target.closest("dialog") || target.hasAttribute("data-focus-on-swap")) {
      var focusEl = target.querySelector("[aria-invalid='true'], input:not([type='hidden']), select, textarea, button");
      if (focusEl && focusEl.focus) {
        focusEl.focus();
      }
    }
  });
})();
