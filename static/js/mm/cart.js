/* MM.cart: guest cart (localStorage) + add button <-> stepper on the product page (docs/02 §5).
   Prices never live here: only {v, q}. */
(function (MM) {
  "use strict";
  var KEY = "malmal.cart.v1";
  var MAX_LINES = 30;
  var syncing = false;
  var busy = false;
  var busyTimer = null;
  var serverQty = {}; /* signed-in viewer: variant id -> quantity in the server cart */
  var known = {}; /* variant ids whose serverQty is already loaded */
  var loading = false;

  function isAuth() { return document.body.getAttribute("data-auth") === "1"; }

  function read() {
    try {
      var data = JSON.parse(window.localStorage.getItem(KEY) || "{}");
      return Array.isArray(data.items) ? data.items.filter(function (i) { return i && i.v > 0 && i.q > 0; }) : [];
    } catch (e) { return []; }
  }
  function write(items) {
    try { window.localStorage.setItem(KEY, JSON.stringify({ items: items, updatedAt: Date.now() })); } catch (e) { /* storage blocked */ }
  }
  function clear() { try { window.localStorage.removeItem(KEY); } catch (e) { /* storage blocked */ } }

  function qtyOf(id) {
    var hit = read().filter(function (i) { return i.v === id; })[0];
    return hit ? hit.q : 0;
  }
  function setLocal(id, qty) {
    var items = read().filter(function (i) { return i.v !== id; });
    if (qty > 0) {
      if (items.length >= MAX_LINES) return false;
      items.push({ v: id, q: qty });
    }
    write(items);
    window.malmalSetCartCount(items.length);
    return true;
  }
  function post(url, values, target) {
    var ctx = { swap: target ? "innerHTML" : "none", values: values };
    if (target) ctx.target = target;
    window.htmx.ajax("POST", url, ctx);
  }

  /* ---------- product page: add button <-> stepper ---------- */
  function panel() { return document.getElementById("variant-panel"); }
  function variantId() {
    var p = panel();
    return p ? parseInt(p.getAttribute("data-variant-id") || "0", 10) || 0 : 0;
  }
  function lineQty(id) {
    if (!id) return 0;
    return isAuth() ? serverQty[id] || 0 : qtyOf(id);
  }

  function renderControls() {
    var p = panel();
    if (!p) return;
    var qty = lineQty(variantId());
    var orderable = p.getAttribute("data-orderable") === "1";
    var max = parseInt(p.getAttribute("data-max") || "0", 10);

    document.querySelectorAll("[data-cart-idle]").forEach(function (el) { el.hidden = qty > 0; });
    document.querySelectorAll("[data-cart-active]").forEach(function (el) { el.hidden = qty <= 0; });
    document.querySelectorAll("[data-cart-qty]").forEach(function (el) { el.textContent = MM.fmt.faDigits(qty); });
    document.querySelectorAll("[data-cart-minus]").forEach(function (el) { el.hidden = qty === 1; });
    document.querySelectorAll("[data-cart-trash]").forEach(function (el) { el.hidden = qty !== 1; });
    document.querySelectorAll("[data-cart-add]").forEach(function (b) { b.disabled = !orderable || busy; });
    document.querySelectorAll("[data-cart-step]").forEach(function (b) {
      var plus = b.getAttribute("data-cart-step") === "1";
      b.disabled = busy || (plus && (!orderable || qty >= max));
      if (!plus) b.setAttribute("aria-label", qty === 1 ? "حذف از سبد" : "کم کردن");
    });
    var price = p.getAttribute("data-price");
    if (price) document.querySelectorAll("[data-bar-price]").forEach(function (el) { el.textContent = price; });
  }

  /* One request at a time; a network error must never keep the buttons locked. */
  function setBusy(on) {
    busy = on;
    window.clearTimeout(busyTimer);
    if (on) busyTimer = window.setTimeout(function () { busy = false; renderControls(); }, 4000);
    renderControls();
  }

  function loadQty() {
    var p = panel();
    if (!p || !isAuth() || loading) return;
    var ids = (p.getAttribute("data-variants") || "").split(",").filter(function (v) { return v && !known[v]; });
    if (!ids.length) return;
    loading = true;
    window.fetch("/cart/state/?variants=" + ids.join(","), { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("state");
        return response.json();
      })
      .then(function (data) {
        ids.forEach(function (v) { known[v] = true; serverQty[v] = (data.qty && data.qty[v]) || 0; });
      })
      .catch(function () {})
      .then(function () { loading = false; renderControls(); });
  }

  function onAdd(btn) {
    var id = variantId();
    if (!id || btn.disabled) return;
    if (isAuth()) {
      setBusy(true);
      post("/cart/add/", { variant_id: id });
      return;
    }
    var max = parseInt(panel().getAttribute("data-max") || "0", 10);
    var next = qtyOf(id) + 1;
    if (max && next > max) {
      MM.ui.toast("حداکثر " + MM.fmt.faDigits(max) + " عدد در هر سفارش", { level: "warning" });
      return;
    }
    if (!setLocal(id, next)) {
      MM.ui.toast("سبد خرید حداکثر " + MM.fmt.faDigits(MAX_LINES) + " قلم کالا دارد", { level: "error" });
      return;
    }
    renderControls();
  }

  function onStep(btn) {
    var id = variantId();
    if (!id || btn.disabled) return;
    var next = Math.max(0, lineQty(id) + parseInt(btn.getAttribute("data-cart-step"), 10));
    if (isAuth()) {
      setBusy(true);
      post("/cart/line/", { variant_id: id, qty: next });
      return;
    }
    var max = parseInt(panel().getAttribute("data-max") || "0", 10);
    if (max && next > max) return;
    setLocal(id, next);
    renderControls();
  }

  /* ---------- cart page ---------- */
  function renderGuest() {
    post("/cart/render/", { items: JSON.stringify(read()) }, "#cart-content");
  }

  function onSet(btn) {
    var id = parseInt(btn.getAttribute("data-variant"), 10);
    var qty = parseInt(btn.getAttribute("data-qty"), 10);
    if (!(id > 0) || !(qty >= 0)) return;
    btn.disabled = true; /* the server takes an absolute quantity, so a double click is harmless anyway */
    window.setTimeout(function () { if (btn.isConnected) btn.disabled = false; }, 4000); /* a network error must not lock it */
    if (isAuth()) {
      post("/cart/set/", { variant_id: id, qty: qty }, "#cart-content");
    } else {
      setLocal(id, qty);
      renderGuest();
    }
  }

  document.addEventListener("click", function (event) {
    var target = event.target.closest ? event.target : null;
    if (!target) return;
    var add = target.closest("[data-cart-add]");
    if (add) { onAdd(add); return; }
    var step = target.closest("[data-cart-step]");
    if (step) { onStep(step); return; }
    var set = target.closest("[data-cart-set]");
    if (set) onSet(set);
  });

  /* Guest items travel with the request: the cart page render, and the OTP verify form (merge before checkout). */
  document.addEventListener("htmx:configRequest", function (event) {
    var el = event.detail.elt;
    if (!el || !el.hasAttribute) return;
    if (el.hasAttribute("data-cart-items")) event.detail.parameters.items = JSON.stringify(read());
    if (el.hasAttribute("data-guest-cart")) event.detail.parameters.guest_cart = JSON.stringify(read());
  });

  document.addEventListener("htmx:afterSwap", function () {
    renderControls();
    var state = document.getElementById("cart-state");
    if (state && state.getAttribute("data-guest") === "1") {
      try { write(JSON.parse(state.getAttribute("data-normalized") || "[]")); } catch (e) { /* ignore */ }
    }
  });

  document.addEventListener("cart:changed", function (event) {
    var detail = event.detail || {};
    if (typeof detail.count === "number") window.malmalSetCartCount(detail.count);
    if (syncing) { clear(); syncing = false; }
    if (typeof detail.variant === "number") {
      serverQty[detail.variant] = detail.qty || 0;
      known[detail.variant] = true;
    }
    if (detail.message) MM.ui.toast(detail.message, { level: detail.ok === false ? "error" : "warning" });
    setBusy(false);
  });

  document.addEventListener("auth:login", clear); /* the server merged it during verify */

  function syncGuestCart() {
    var items = read();
    if (!isAuth() || !items.length || syncing) return;
    syncing = true;
    post("/cart/sync/", { items: JSON.stringify(items) });
  }

  /* A failed request leaves the in-flight flags set; clear them or the cart controls stay locked. */
  function resetPending() {
    syncing = false;
    setBusy(false);
  }
  document.addEventListener("htmx:responseError", resetPending);
  document.addEventListener("htmx:sendError", resetPending);

  /* Back/forward cache restores a stale page: reload the viewer's quantities. */
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) return;
    serverQty = {};
    known = {};
    renderControls();
    loadQty();
  });

  MM.cart = { read: read, clear: clear };
  MM.init("cart", function () {
    renderControls();
    if (isAuth()) {
      loadQty();
      syncGuestCart();
    } else {
      window.malmalSetCartCount(read().length);
    }
  });
})(window.MM);
