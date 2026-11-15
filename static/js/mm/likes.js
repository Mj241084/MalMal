/* MM.likes: heart for signed-in users, ONE batched state request per page or swap, and the guest flow
   (remember the heart, open the login modal, apply the like after login). docs/02 D12. */
(function (MM) {
  "use strict";
  var PENDING_KEY = "malmal.like.pending";
  var PENDING_TTL = 15 * 60 * 1000;
  var CHUNK = 60;

  function isAuth() { return document.body.getAttribute("data-auth") === "1"; }

  function writePending(id) {
    try { window.localStorage.setItem(PENDING_KEY, JSON.stringify({ id: id, at: Date.now() })); } catch (e) { /* storage blocked */ }
  }
  function takePending() {
    try {
      var raw = window.localStorage.getItem(PENDING_KEY);
      window.localStorage.removeItem(PENDING_KEY);
      var data = JSON.parse(raw || "null");
      return data && data.id > 0 && Date.now() - data.at < PENDING_TTL ? data.id : 0;
    } catch (e) { return 0; }
  }

  function request(verb, url, values) {
    var result = window.htmx.ajax(verb, url, { swap: "none", values: values || {} });
    return result && result.then ? result.catch(function () {}) : Promise.resolve();
  }

  function pageContext(id) {
    var social = document.getElementById("social-product");
    return social && social.getAttribute("data-product") === String(id) ? "page" : "";
  }

  /* Guests: capture phase, so htmx never sees the click. The heart is remembered and the login modal opens. */
  document.addEventListener("click", function (event) {
    var heart = event.target.closest && event.target.closest("[data-like]");
    if (!heart || isAuth()) return;
    event.preventDefault();
    event.stopPropagation();
    writePending(parseInt(heart.getAttribute("data-like"), 10));
    MM.auth.open(window.location.pathname + window.location.search);
  }, true);

  /* The server takes an absolute state, so a double click or a replay is harmless. */
  document.addEventListener("htmx:configRequest", function (event) {
    var heart = event.detail.elt;
    if (!heart || !heart.hasAttribute || !heart.hasAttribute("data-like")) return;
    event.detail.parameters.state = heart.getAttribute("aria-pressed") === "true" ? "0" : "1";
    if (pageContext(heart.getAttribute("data-like"))) event.detail.parameters.ctx = "page";
  });

  function loadState(root) {
    var ids = [];
    MM.each(root, "[data-like]", function (heart) {
      if (heart.getAttribute("data-like-seen") === "1") return;
      heart.setAttribute("data-like-seen", "1");
      var id = heart.getAttribute("data-like");
      if (ids.indexOf(id) === -1) ids.push(id);
    });
    for (var i = 0; i < ids.length; i += CHUNK) {
      request("GET", "/likes/state/?ids=" + ids.slice(i, i + CHUNK).join(","));
    }
  }

  function applyPending(id) {
    var values = { state: "1" };
    if (pageContext(id)) values.ctx = "page";
    return request("POST", "/likes/" + id + "/", values);
  }

  MM.likes = { loadState: loadState };
  MM.init("likes", function (root) {
    if (!isAuth()) return;
    var pending = takePending(); /* only the first call (initial load) finds one */
    (pending ? applyPending(pending) : Promise.resolve()).then(function () {
      loadState(root);
      if (pending && pageContext(pending)) {
        window.htmx.ajax("GET", "/social/product/" + pending + "/", { target: "#social-product", swap: "innerHTML" });
      }
    });
  });
})(window.MM);
