/* MM.auth: login modal. The OTP step itself lives in otp.js; resuming is decided by the server (session). */
(function (MM) {
  "use strict";
  var DIALOG = "auth-modal";
  var BODY = "auth-modal-body";

  function open() {
    document.querySelectorAll("header details.dropdown[open]").forEach(function (d) { d.removeAttribute("open"); });
    var body = document.getElementById(BODY);
    if (body && !body.firstElementChild) {
      body.innerHTML =
        '<div class="min-h-64 flex items-center justify-center"><span class="loading loading-spinner loading-md text-ink-3"></span></div>';
    }
    MM.ui.dialog.open(DIALOG);
  }

  document.addEventListener("click", function (event) {
    var opener = event.target.closest && event.target.closest("[data-auth-open]");
    if (opener) {
      event.preventDefault();
      open();
    }
  });

  /* The server answers 204 when the visitor is already signed in */
  document.addEventListener("htmx:beforeSwap", function (event) {
    var target = event.detail && event.detail.target;
    var xhr = event.detail && event.detail.xhr;
    if (target && xhr && target.id === BODY && xhr.status === 204) {
      event.detail.shouldSwap = false;
      MM.ui.dialog.close(DIALOG);
      window.location.reload();
    }
  });

  MM.init("auth", function (root) {
    MM.each(root, "#" + DIALOG, function (dialog) {
      if (dialog.dataset.authReady === "1") return;
      dialog.dataset.authReady = "1";
      dialog.addEventListener("close", function () {
        var body = document.getElementById(BODY);
        if (body) body.innerHTML = "";
      });
    });
  });
})(window.MM);
