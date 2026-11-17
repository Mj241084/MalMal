/* MM.shell: cart badge count, search suggestion panel, dropdown menus, rail arrows, styleguide demos. */
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

  /* An open <details class="dropdown"> closes on outside click and on Escape. */
  function closeDropdowns(except) {
    document.querySelectorAll("details.dropdown[open]").forEach(function (d) {
      if (d !== except) d.removeAttribute("open");
    });
  }

  document.addEventListener("click", function (e) {
    var panel = document.getElementById("search-suggest");
    if (panel && !panel.classList.contains("hidden")) {
      var form = panel.closest("form");
      if (form && !form.contains(e.target)) {
        panel.classList.add("hidden");
      }
    }

    closeDropdowns(e.target.closest ? e.target.closest("details.dropdown") : null);

    var rail = e.target.closest ? e.target.closest("[data-rail-scroll]") : null;
    if (rail) {
      var track = document.getElementById(rail.getAttribute("data-rail"));
      if (track) {
        var rtl = window.getComputedStyle(track).direction === "rtl";
        var dir = parseInt(rail.getAttribute("data-rail-scroll"), 10) * (rtl ? -1 : 1);
        var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        track.scrollBy({ left: dir * track.clientWidth * 0.8, behavior: reduced ? "auto" : "smooth" });
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
    closeDropdowns(null);
  });

  /* The suggestion panel is swapped as a child of #search-suggest, so MM.init on the new root misses it. */
  document.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail && event.detail.target;
    if (target && target.id === "search-suggest") syncSuggestPanel();
  });

  /* [data-share="<url>"]: copy a link. The Clipboard API needs https or localhost; otherwise a hidden textarea. */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var box = document.createElement("textarea");
      var ok = false;
      box.value = text;
      box.setAttribute("readonly", "");
      box.style.cssText = "position:fixed;top:0;opacity:0";
      document.body.appendChild(box);
      box.select();
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      box.remove();
      if (ok) resolve(); else reject(new Error("copy"));
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest ? event.target.closest("[data-share]") : null;
    if (!button) return;
    var url = button.getAttribute("data-share");
    copyText(url).then(
      function () { MM.ui.toast("لینک محصول کپی شد", { level: "success" }); },
      function () { MM.ui.alert({ title: "کپی نشد؛ لینک را دستی کپی کنید", message: url }); }
    );
  });

  MM.init("shell", function (root) {
    MM.each(root, "#search-suggest", syncSuggestPanel);
  });
})(window.MM);
