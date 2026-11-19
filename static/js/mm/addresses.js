/* MM.addresses: the inline address form (account page and checkout).
   On checkout, an address form that is open and filled in is saved before the order is placed, never dropped. */
(function (MM) {
  "use strict";
  var CHECKOUT_FORM = "checkout-form";
  var SAVE_PATH = "/checkout/address/new/";
  var REQUIRED = ["address_text", "plate", "postal_code", "city"]; /* a value in any of these = the customer meant to add it */
  var SAVE_TIMEOUT = 15000; /* a network error must never keep the pay buttons locked */
  var pending = null; /* {form, submitter} while the address is being saved on the way to payment */

  function sync() {
    var add = document.querySelector("[data-address-add]");
    var container = document.getElementById("address-form-container");
    if (add && container) add.classList.toggle("hidden", Boolean(container.querySelector("#address-form")));
  }

  function isFilled(form) {
    return REQUIRED.some(function (name) {
      var field = form.elements[name];
      return Boolean(field) && String(field.value || "").trim() !== "";
    });
  }

  function lockPay(on) {
    document.querySelectorAll("button[type='submit'][form='" + CHECKOUT_FORM + "']").forEach(function (button) {
      button.disabled = on;
    });
  }

  function release() {
    if (!pending) return; /* never touch buttons the server rendered disabled */
    pending = null;
    lockPay(false);
  }

  document.addEventListener("click", function (event) {
    if (!event.target.closest || !event.target.closest("[data-address-cancel]")) return;
    var container = document.getElementById("address-form-container");
    if (container) container.innerHTML = "";
    sync();
  });

  /* Capture phase: runs before the browser submits #checkout-form. */
  document.addEventListener("submit", function (event) {
    var checkout = event.target;
    if (!checkout || checkout.id !== CHECKOUT_FORM) return;
    if (pending) {
      event.preventDefault(); /* a second click while the address is being saved */
      return;
    }

    var address = document.getElementById("address-form");
    var hasSaved = Boolean(document.querySelector("input[name='address_id']"));

    if (!address) {
      var add = document.querySelector("[data-address-add]");
      if (!hasSaved && add) { /* nothing saved and no form open: show the form instead of a server error */
        event.preventDefault();
        add.click();
        MM.ui.toast("آدرس تحویل را وارد کنید", { level: "warning" });
      }
      return;
    }
    if (hasSaved && !isFilled(address)) return; /* an empty form left open is simply ignored */

    event.preventDefault();
    var job = { form: checkout, submitter: event.submitter || null };
    pending = job;
    lockPay(true);
    window.setTimeout(function () { if (pending === job) release(); }, SAVE_TIMEOUT);
    window.htmx.trigger(address, "submit");
  }, true);

  /* The address section was swapped: no form left = saved, so go on to payment; a form = errors, stay and fix. */
  document.addEventListener("htmx:afterSettle", function (event) {
    if (!pending) return;
    var path = (event.detail && event.detail.pathInfo && event.detail.pathInfo.requestPath) || "";
    if (path && path.indexOf(SAVE_PATH) === -1) return; /* some other request settled */
    var job = pending;
    release();
    if (document.getElementById("address-form")) return;
    if (job.form.requestSubmit) job.form.requestSubmit(job.submitter);
    else job.form.submit();
  });
  document.addEventListener("htmx:responseError", release);
  document.addEventListener("htmx:sendError", release);

  MM.init("addresses", function () {
    sync();
    var container = document.getElementById("address-form-container");
    if (container && container.firstElementChild) container.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
})(window.MM);
