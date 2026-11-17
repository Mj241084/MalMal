/* Neshan MapLibre address picker (docs/vendors/neshan/neshan-address-picker-guide.md). */
(function (MM) {
  "use strict";
  var STYLE_LIGHT = "https://static.neshan.org/sdk/maplibre/styles/light.json";
  var STYLE_DARK = "https://static.neshan.org/sdk/maplibre/styles/dark.json";
  var DEFAULT_CENTER = [51.389, 35.6892]; // [lng, lat]

  function initPicker(root) {
    if (!root || root.dataset.mapInit === "1") return;
    if (!window.maplibregl || !window.maplibregl.default) return;

    var form = root.closest("form");
    var canvas = root.querySelector("[data-neshan-canvas]");
    var locateBtn = root.querySelector("[data-neshan-locate]");
    var statusEl = root.querySelector("[data-neshan-status]");
    var latInput = form && form.querySelector("input[name='lat']");
    var lngInput = form && form.querySelector("input[name='lng']");
    var provinceSelect = form && form.querySelector("select[name='province']");
    var citySelect = form && form.querySelector("select[name='city']");
    var addressInput = form && form.querySelector("textarea[name='address_text']");

    var apiKey = root.getAttribute("data-neshan-key") || "";
    var reverseUrl = root.getAttribute("data-reverse-url") || "";
    if (!canvas || !apiKey || !latInput || !lngInput) return;

    root.dataset.mapInit = "1";
    var maplibregl = window.maplibregl.default;
    var hasInitial = Boolean(latInput.value && lngInput.value);
    var initialLng = hasInitial ? Number(lngInput.value) : DEFAULT_CENTER[0];
    var initialLat = hasInitial ? Number(latInput.value) : DEFAULT_CENTER[1];
    var isDark = document.documentElement.getAttribute("data-theme") === "malmal-dark";

    var map = new maplibregl.Map({
      container: canvas,
      style: isDark ? STYLE_DARK : STYLE_LIGHT,
      center: [initialLng, initialLat],
      zoom: hasInitial ? 16 : 12,
      minZoom: 5,
      apiKey: apiKey,
    });
    map.addControl(new maplibregl.NavigationControl());

    var marker = null;
    var reqSeq = 0;

    function syncCitySelect(provinceId, cityId) {
      if (!provinceSelect || !citySelect || !provinceId) return;
      provinceSelect.value = String(provinceId);
      if (window.htmx) {
        var qs = "?province=" + encodeURIComponent(provinceId);
        if (cityId) qs += "&selected=" + encodeURIComponent(cityId);
        window.htmx.ajax("GET", "/geo/cities/" + qs, { target: citySelect, swap: "innerHTML" });
      }
    }

    function onPointChanged(lng, lat) {
      latInput.value = Number(lat).toFixed(6);
      lngInput.value = Number(lng).toFixed(6);

      if (!reverseUrl) {
        if (statusEl) statusEl.textContent = "موقعیت روی نقشه ثبت شد";
        return;
      }

      var mySeq = ++reqSeq;
      if (statusEl) statusEl.textContent = "در حال دریافت آدرس…";
      fetch(reverseUrl + "?lat=" + encodeURIComponent(latInput.value) + "&lng=" + encodeURIComponent(lngInput.value), {
        credentials: "same-origin",
      })
        .then(function (resp) {
          return resp.json().then(function (data) {
            return { ok: resp.ok, data: data };
          });
        })
        .then(function (res) {
          if (mySeq !== reqSeq) return;
          if (!res.ok || !res.data || res.data.enabled === false) {
            if (statusEl) statusEl.textContent = "موقعیت ثبت شد؛ جزئیات آدرس را وارد کنید";
            return;
          }
          if (res.data.address_text && addressInput && !addressInput.value.trim()) {
            addressInput.value = res.data.address_text;
          }
          if (res.data.province_id) {
            syncCitySelect(res.data.province_id, res.data.city_id);
          }
          if (statusEl) statusEl.textContent = "آدرس از نقشه دریافت شد؛ در صورت نیاز ویرایش کنید";
        })
        .catch(function () {
          if (mySeq === reqSeq && statusEl) {
            statusEl.textContent = "آدرس این نقطه دریافت نشد؛ لطفاً دستی وارد کنید";
          }
        });
    }

    function setPoint(lng, lat) {
      if (!marker) {
        marker = new maplibregl.Marker({ draggable: true }).setLngLat([lng, lat]).addTo(map);
        marker.on("dragend", function () {
          var p = marker.getLngLat();
          onPointChanged(p.lng, p.lat);
        });
      } else {
        marker.setLngLat([lng, lat]);
      }
      onPointChanged(lng, lat);
    }

    if (hasInitial) {
      marker = new maplibregl.Marker({ draggable: true }).setLngLat([initialLng, initialLat]).addTo(map);
      marker.on("dragend", function () {
        var p = marker.getLngLat();
        onPointChanged(p.lng, p.lat);
      });
    }

    map.on("click", function (e) {
      setPoint(e.lngLat.lng, e.lngLat.lat);
    });

    if (locateBtn) {
      locateBtn.addEventListener("click", function () {
        if (!navigator.geolocation) {
          if (statusEl) statusEl.textContent = "مرورگر از موقعیت‌یابی پشتیبانی نمی‌کند";
          return;
        }
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            map.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 17 });
            setPoint(pos.coords.longitude, pos.coords.latitude);
          },
          function () {
            if (statusEl) statusEl.textContent = "دسترسی به موقعیت داده نشد؛ نقطه را روی نقشه انتخاب کنید";
          },
          { enableHighAccuracy: true, timeout: 10000 }
        );
      });
    }
  }

  MM.init("neshan", function (root) { MM.each(root, "[data-neshan-picker]", initPicker); });
})(window.MM);
