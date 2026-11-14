/* MM.ui: toast, confirm, alert, dialog. Native alert/confirm/prompt are forbidden (D31). */
(function (MM) {
  "use strict";
  var ui = (MM.ui = MM.ui || {});

  /* ---------- toast ---------- */
  var LEVEL_CLASS = { error: "alert-error", success: "alert-success", warning: "alert-warning", info: "alert-info" };

  ui.toast = function (message, options) {
    var opts = typeof options === "string" ? { level: options } : options || {};
    var host = document.getElementById("toasts");
    if (!host) return;
    var box = document.createElement("div");
    box.setAttribute("role", opts.level === "error" ? "alert" : "status");
    box.className = "alert " + (LEVEL_CLASS[opts.level] || LEVEL_CLASS.info) + " surface-float text-small max-w-sm";
    var text = document.createElement("span");
    text.textContent = message;
    box.appendChild(text);
    host.appendChild(box);
    window.setTimeout(function () { box.remove(); }, opts.timeout || 5000);
  };

  /* Legacy global alias */
  window.malmalToast = function (message, level) { MM.ui.toast(message, { level: level }); };

  /* ---------- plain dialogs (<dialog id="..."> in base.html or a page) ---------- */
  ui.dialog = {
    open: function (id) {
      var el = document.getElementById(id);
      if (el && typeof el.showModal === "function" && !el.open) el.showModal();
      return el;
    },
    close: function (id) {
      var el = document.getElementById(id);
      if (el && el.open) el.close();
    },
  };

  document.addEventListener("click", function (event) {
    var closer = event.target.closest && event.target.closest("[data-dialog-close]");
    if (closer) {
      var dialog = closer.closest("dialog");
      if (dialog && dialog.open) dialog.close();
    }
  });

  /* ---------- shared confirm / alert dialog (#mm-dialog) ---------- */
  var finishCurrent = null;

  function ask(options, withCancel) {
    var dialog = document.getElementById("mm-dialog");
    if (!dialog || typeof dialog.showModal !== "function") return Promise.resolve(false);
    if (finishCurrent) finishCurrent(false);

    var title = dialog.querySelector("[data-mm-title]");
    var message = dialog.querySelector("[data-mm-message]");
    var ok = dialog.querySelector("[data-mm-ok]");
    var cancel = dialog.querySelector("[data-mm-cancel]");
    var danger = options.tone === "danger";

    title.textContent = options.title || "";
    title.hidden = !options.title;
    message.textContent = options.message || "";
    ok.textContent = options.confirmLabel || "تایید";
    ok.className = "btn flex-1 min-w-0 h-11 min-h-11 " + (danger ? "btn-error" : "btn-primary");
    cancel.textContent = options.cancelLabel || "انصراف";
    cancel.hidden = !withCancel;

    return new Promise(function (resolve) {
      function finish(result) {
        if (finishCurrent !== finish) return;
        finishCurrent = null;
        ok.removeEventListener("click", onOk);
        cancel.removeEventListener("click", onCancel);
        dialog.removeEventListener("close", onClose);
        if (dialog.open) dialog.close();
        resolve(result);
      }
      function onOk() { finish(true); }
      function onCancel() { finish(false); }
      function onClose() { finish(false); } /* Esc or backdrop */

      finishCurrent = finish;
      ok.addEventListener("click", onOk);
      cancel.addEventListener("click", onCancel);
      dialog.addEventListener("close", onClose);
      dialog.showModal();
      (danger && withCancel ? cancel : ok).focus();
    });
  }

  /* ui.confirm("text") or ui.confirm({ title, message, confirmLabel, cancelLabel, tone: "danger" }) -> Promise<boolean> */
  ui.confirm = function (options) {
    return ask(typeof options === "string" ? { message: options } : options || {}, true);
  };
  ui.alert = function (options) {
    return ask(typeof options === "string" ? { message: options } : options || {}, false).then(function () {});
  };

  function optionsFrom(el, message) {
    return {
      message: message,
      title: el.getAttribute("data-confirm-title") || "",
      confirmLabel: el.getAttribute("data-confirm-label") || "",
      cancelLabel: el.getAttribute("data-confirm-cancel") || "",
      tone: el.getAttribute("data-confirm-tone") || "",
    };
  }

  /* hx-confirm="..." keeps working in templates, but renders our dialog instead of the native browser confirm */
  document.addEventListener("htmx:confirm", function (event) {
    var question = event.detail && event.detail.question;
    if (!question) return;
    event.preventDefault();
    ui.confirm(optionsFrom(event.detail.elt, question)).then(function (ok) {
      if (ok) event.detail.issueRequest(true);
    });
  });

  /* Plain (non-HTMX) forms: <form data-confirm="..."> */
  document.addEventListener("submit", function (event) {
    var form = event.target;
    var question = form.getAttribute && form.getAttribute("data-confirm");
    if (!question || form.dataset.mmConfirmed === "1") return;
    event.preventDefault();
    var submitter = event.submitter;
    ui.confirm(optionsFrom(form, question)).then(function (ok) {
      if (!ok) return;
      form.dataset.mmConfirmed = "1";
      if (form.requestSubmit) form.requestSubmit(submitter);
      else form.submit();
    });
  }, true);

  /* ---------- HTMX transport errors ---------- */
  function transportError() { ui.toast("ارتباط برقرار نشد. دوباره تلاش کنید", { level: "error" }); }
  document.addEventListener("htmx:responseError", transportError);
  document.addEventListener("htmx:sendError", transportError);
})(window.MM);
