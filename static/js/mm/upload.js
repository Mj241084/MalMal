/* MM.upload: drag & drop for a [data-dropzone] form. Files go up in batches of at most 3, one request after
   the other, each as a normal HTMX submit of the zone's form (docs/08-ui-modules.md). */
(function (MM) {
  "use strict";
  var BATCH = 3;
  var queue = [];
  var total = 0;
  var active = null; /* id of the form being fed */

  function zone() { return active ? document.getElementById(active) : null; }

  function progressOf(form) { return form ? form.querySelector("[data-dropzone-progress]") : null; }

  function feed() {
    var form = zone();
    if (!form) { queue = []; active = null; return; }
    var progress = progressOf(form);
    if (progress) {
      progress.max = total;
      progress.value = total - queue.length;
      progress.classList.toggle("hidden", !queue.length);
    }
    if (!queue.length) { active = null; return; }
    var input = form.querySelector("input[type='file']");
    var transfer = new DataTransfer();
    queue.splice(0, BATCH).forEach(function (file) { transfer.items.add(file); });
    input.files = transfer.files;
    window.htmx.trigger(form, "submit");
  }

  function start(form, list) {
    var files = Array.prototype.filter.call(list, function (file) { return file.type.indexOf("image/") === 0; });
    if (files.length !== list.length) MM.ui.toast("فقط فایل تصویری پذیرفته می‌شود", { level: "warning" });
    if (!files.length) return;
    queue = files;
    total = files.length;
    active = form.id;
    feed();
  }

  document.addEventListener("change", function (event) {
    var input = event.target;
    var form = input.closest && input.closest("[data-dropzone]");
    if (form && input.type === "file" && !active) start(form, input.files);
  });

  document.addEventListener("dragover", function (event) {
    var form = event.target.closest && event.target.closest("[data-dropzone]");
    if (!form) return;
    event.preventDefault();
    form.classList.add("bg-base-300");
  });
  document.addEventListener("dragleave", function (event) {
    var form = event.target.closest && event.target.closest("[data-dropzone]");
    if (form) form.classList.remove("bg-base-300");
  });
  document.addEventListener("drop", function (event) {
    var form = event.target.closest && event.target.closest("[data-dropzone]");
    if (!form) return;
    event.preventDefault();
    form.classList.remove("bg-base-300");
    if (!active) start(form, event.dataTransfer.files);
  });

  /* The next batch goes when the gallery section has been swapped in. */
  document.addEventListener("htmx:afterSettle", function (event) {
    if (!active) return;
    var el = event.target;
    if (el && el.closest && el.closest("#sec-gallery")) feed();
  });
  function stop() { queue = []; active = null; }
  document.addEventListener("htmx:responseError", stop);
  document.addEventListener("htmx:sendError", stop);

  MM.upload = { pending: function () { return queue.length; } };
})(window.MM);
