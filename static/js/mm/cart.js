/* MM.cart: guest cart (localStorage) + add / quantity controls (docs/02 §5). Prices never live here: only {v, q}. */
(function (MM) {
  "use strict";
  var KEY = "malmal.cart.v1";
  var MAX_LINES = 30;
  var syncing = false;
  var lastAdd = null;

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

  function flash(btn) {
    var label = btn.querySelector("[data-cart-label]");
    if (!label || btn.dataset.flashing) return;
    var original = label.textContent;
    btn.dataset.flashing = "1";
    label.textContent = "در سبد شما";
    window.setTimeout(function () { label.textContent = original; delete btn.dataset.flashing; }, 1600);
  }

  function onAdd(btn) {
    var panel = document.getElementById("variant-panel");
    if (!panel || !panel.dataset.variantId || btn.disabled) return;
    var id = parseInt(panel.dataset.variantId, 10);
    if (isAuth()) {
      lastAdd = btn;
      post("/cart/add/", { variant_id: id });
      return;
    }
    var max = parseInt(panel.dataset.max || "0", 10);
    var next = qtyOf(id) + 1;
    if (max && next > max) {
      MM.ui.toast("حداکثر " + MM.fmt.faDigits(max) + " عدد در هر سفارش", { level: "warning" });
      return;
    }
    if (!setLocal(id, next)) {
      MM.ui.toast("سبد خرید حداکثر " + MM.fmt.faDigits(MAX_LINES) + " قلم کالا دارد", { level: "error" });
      return;
    }
    flash(btn);
  }

  function renderGuest() {
    post("/cart/render/", { items: JSON.stringify(read()) }, "#cart-content");
  }

  function onSet(btn) {
    var id = parseInt(btn.getAttribute("data-variant"), 10);
    var qty = parseInt(btn.getAttribute("data-qty"), 10);
    if (!(id > 0) || !(qty >= 0)) return;
    btn.disabled = true; /* the server takes an absolute quantity, so a double click is harmless anyway */
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

  function syncButtons() {
    var panel = document.getElementById("variant-panel");
    if (!panel) return;
    var orderable = panel.getAttribute("data-orderable") === "1";
    document.querySelectorAll("[data-cart-add]").forEach(function (b) { b.disabled = !orderable; });
    var price = panel.getAttribute("data-price");
    if (price) document.querySelectorAll("[data-bar-price]").forEach(function (el) { el.textContent = price; });
  }

  document.addEventListener("htmx:afterSwap", function () {
    syncButtons();
    var state = document.getElementById("cart-state");
    if (state && state.getAttribute("data-guest") === "1") {
      try { write(JSON.parse(state.getAttribute("data-normalized") || "[]")); } catch (e) { /* ignore */ }
    }
  });

  document.addEventListener("cart:changed", function (event) {
    var detail = event.detail || {};
    if (typeof detail.count === "number") window.malmalSetCartCount(detail.count);
    if (syncing) { clear(); syncing = false; }
    if (detail.message) MM.ui.toast(detail.message, { level: detail.ok === false ? "error" : "warning" });
    if (lastAdd && detail.ok !== false) flash(lastAdd);
    lastAdd = null;
  });

  document.addEventListener("auth:login", clear); /* the server merged it during verify */

  function syncGuestCart() {
    var items = read();
    if (!isAuth() || !items.length || syncing) return;
    syncing = true;
    post("/cart/sync/", { items: JSON.stringify(items) });
  }

  MM.cart = { read: read, clear: clear };
  MM.init("cart", function () {
    syncButtons();
    if (isAuth()) syncGuestCart();
    else window.malmalSetCartCount(read().length);
  });
})(window.MM);
