/* MM.addresses: hide the primary "add" button while the inline form is open. */
(function (MM) {
  "use strict";

  function sync() {
    var add = document.querySelector("[data-address-add]");
    var container = document.getElementById("address-form-container");
    if (add && container) add.classList.toggle("hidden", Boolean(container.querySelector("#address-form")));
  }

  document.addEventListener("click", function (event) {
    if (!event.target.closest || !event.target.closest("[data-address-cancel]")) return;
    var container = document.getElementById("address-form-container");
    if (container) container.innerHTML = "";
    sync();
  });

  MM.init("addresses", function () {
    sync();
    var container = document.getElementById("address-form-container");
    if (container && container.firstElementChild) container.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
})(window.MM);
