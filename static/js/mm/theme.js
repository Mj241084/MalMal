/* MM.theme: light/dark/system preference synced to localStorage and OS media query. */
(function (MM) {
  "use strict";
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

  MM.init("theme", function () {
    syncThemeButtons(document.documentElement.dataset.themePref || getSavedTheme());
  });
})(window.MM);
