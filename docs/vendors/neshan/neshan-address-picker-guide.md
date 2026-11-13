# راهنمای کامل استفاده از نقشه و سرویس‌های نشان برای دریافت آدرس کاربر در فروشگاه اینترنتی

> این راهنما بر اساس مستندات رسمی پلتفرم نشان (`platform.neshan.org/docs`) نوشته شده است. هدف: کاربر در صفحه‌ی تکمیل خرید، موقعیت خود را روی نقشه انتخاب کند، آدرس متنی به‌صورت خودکار پر شود، کاربر جزئیات (پلاک، واحد، کدپستی و…) را کامل کند و سرور شما آدرس را معتبر ذخیره کند.

---

## فهرست مطالب

1. [معماری پیشنهادی](#1-معماری-پیشنهادی)
2. [پیش‌نیازها: کلیدهای دسترسی](#2-پیش‌نیازها-کلیدهای-دسترسی)
3. [انتخاب کیت توسعه وب](#3-انتخاب-کیت-توسعه-وب)
4. [گام اول: نمایش نقشه و انتخاب نقطه](#4-گام-اول-نمایش-نقشه-و-انتخاب-نقطه)
5. [گام دوم: تبدیل مختصات به آدرس (Reverse Geocoding)](#5-گام-دوم-تبدیل-مختصات-به-آدرس-reverse-geocoding)
6. [گام سوم: بک‌اند واسط (Proxy) برای مخفی ماندن کلید](#6-گام-سوم-بک‌اند-واسط-proxy-برای-مخفی-ماندن-کلید)
7. [گام چهارم: فرم کامل آدرس (کد نمونه کامل)](#7-گام-چهارم-فرم-کامل-آدرس-کد-نمونه-کامل)
8. [جستجوی آدرس و مکان (Search)](#8-جستجوی-آدرس-و-مکان-search)
9. [تبدیل آدرس متنی به مختصات (Geocoding)](#9-تبدیل-آدرس-متنی-به-مختصات-geocoding)
10. [اعتبارسنجی و ذخیره آدرس در سرور](#10-اعتبارسنجی-و-ذخیره-آدرس-در-سرور)
11. [قابلیت‌های تکمیلی برای فروشگاه](#11-قابلیت‌های-تکمیلی-برای-فروشگاه)
12. [خطاها و عیب‌یابی](#12-خطاها-و-عیب‌یابی)
13. [نکات مهم و تله‌های رایج](#13-نکات-مهم-و-تله‌های-رایج)
14. [چک‌لیست نهایی](#14-چک‌لیست-نهایی)
15. [لینک‌های مرجع](#15-لینک‌های-مرجع)

---

## 1. معماری پیشنهادی

```
مرورگر کاربر                          سرور شما                         سرویس‌های نشان
─────────────                         ─────────                        ───────────────
نقشه (MapLibre SDK) ──(کلید نقشه وب)──────────────────────────────────► کاشی‌های نقشه
کلیک / جابه‌جایی مارکر
      │
      └─ GET /api/reverse?lat&lng ──► Proxy ──(Api-Key سرویس)──────────► /v5/reverse
      └─ GET /api/search?term…    ──► Proxy ──(Api-Key سرویس)──────────► /v3/search
      │
      └─ POST /api/addresses ───────► اعتبارسنجی + ذخیره در دیتابیس
```

**اصل مهم:** دو نوع کلید دارید و جدا از هم استفاده می‌شوند:

| نوع کلید | کجا استفاده می‌شود | چطور محافظت می‌شود |
|---|---|---|
| **کلید نقشه وب** (Web SDK) | داخل مرورگر، هنگام ساخت نقشه | محدود کردن به دامنه‌ی سایت در پنل |
| **کلید سرویس** (وب‌سرویس‌ها) | فقط روی سرور شما، در هدر `Api-Key` | هرگز داخل کد فرانت‌اند قرار نگیرد |

---

## 2. پیش‌نیازها: کلیدهای دسترسی

1. در [پنل توسعه‌دهندگان نشان](https://platform.neshan.org/panel/signup) ثبت‌نام (رایگان) کنید.
2. در بخش ساخت کلید دسترسی، دو کلید بسازید:
   - کلید با نوع **«نقشه وب»** برای نمایش نقشه در مرورگر.
   - کلید **سرویس‌ها** (جستجو و تبدیل مختصات به آدرس، و در صورت نیاز تبدیل آدرس به مختصات، ماتریس فاصله و…) برای استفاده در سرور.
3. برای امنیت بیشتر، در فیلد **«دامنه/IP های مجاز»** دامنه‌ی سایت (برای کلید نقشه) و IP سرور (برای کلید سرویس) را وارد کنید.
4. سرویس‌های زیر **به‌صورت پیش‌فرض فعال نیستند** و باید از طریق ارسال تیکت در پنل کاربری با پشتیبانی تماس بگیرید:
   - جستجوی مکان‌مبنا (Search v3)
   - جستجوی مکان‌های نزدیک (Nearby)
   - اطلاعات مکان شاخص (POI Details)
   - لیست استان‌ها و شهرستان‌ها (Region)

> کلید هر سرویس باید با همان سرویس هم‌خوانی داشته باشد؛ در غیر این صورت خطای `483 ApiKeyTypeError` می‌گیرید.

[قوانین و شرایط استفاده](https://platform.neshan.org/tos/) را هم مطالعه کنید. لوگو و کپی‌رایت نشان روی نقشه نمایش داده می‌شود و فقط می‌توانید **موقعیت** آن‌ها را تغییر دهید، نه اینکه حذفشان کنید.

---

## 3. انتخاب کیت توسعه وب

| کیت | وضعیت | توصیه |
|---|---|---|
| **MapLibre SDK نشان** | فعال و به‌روز | ✅ **انتخاب پیشنهادی** برای پروژه‌ی جدید |
| Leaflet SDK | فعال | مناسب اگر پروژه از قبل Leaflet دارد. لایه‌ی ترافیک و مکان‌ها (POI) در آن به‌روز نمی‌شوند |
| OpenLayers SDK (+ کامپوننت React/Vue) | فعال | مناسب اگر پروژه از قبل OpenLayers دارد. لایه‌ی ترافیک و POI در آن به‌روز نمی‌شوند |
| Mapbox GL SDK | ⚠️ منقضی‌شده | استفاده نکنید |
| افزونه وردپرس | ⚠️ منسوخ‌شده | اگر فروشگاه شما وردپرسی است، از کیت وب (MapLibre) داخل اسنیپت کد استفاده کنید |

در ادامه‌ی این راهنما از **MapLibre SDK نشان** استفاده می‌شود. نمایش صحیح متن فارسی (RTL) در آن به‌صورت پیش‌فرض فعال است.

---

## 4. گام اول: نمایش نقشه و انتخاب نقطه

### 4.1 نصب

**روش CDN (بدون bundler):**

```html
<link rel="stylesheet" href="https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.css" />
<script src="https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js"></script>
```

**روش npm (Vite، webpack، Next.js و…):**

```bash
# (اختیاری) استفاده از رجیستری نشان: در فایل .npmrc پروژه
# @neshan-maps-platform:registry=https://npm.neshan.org

npm install @neshan-maps-platform/maplibre-sdk
```

```js
import maplibregl from "@neshan-maps-platform/maplibre-sdk";
import "@neshan-maps-platform/maplibre-sdk/style.css";   // فراموش نکنید!
```

> کتابخانه‌ی `maplibre-gl` داخل پکیج نشان bundle شده و نیازی به نصب جداگانه نیست.

### 4.2 ساخت نقشه

```js
// در حالت CDN باید از window.maplibregl.default استفاده کنید
const maplibregl = window.maplibregl.default;

const map = new maplibregl.Map({
  container: "map",                                   // id المان div
  style: "https://static.neshan.org/sdk/maplibre/styles/light.json",
  center: [51.389, 35.6892],                          // ⚠️ [طول, عرض] = [lng, lat]
  zoom: 13,
  minZoom: 5,
  apiKey: "YOUR_WEB_MAP_KEY",                         // الزامی
});

map.addControl(new maplibregl.NavigationControl());
```

```html
<div id="map" style="height: 400px; width: 100%;"></div>
```

> اگر `apiKey` ندهید، خطای `Api key is not defined!` می‌گیرید و نقشه ساخته نمی‌شود.

**استایل‌های آماده:**

| استایل | آدرس |
|---|---|
| Light | `https://static.neshan.org/sdk/maplibre/styles/light.json` |
| Dark | `https://static.neshan.org/sdk/maplibre/styles/dark.json` |
| Monochrome Light | `https://static.neshan.org/sdk/maplibre/styles/monochrome_light.json` |
| Monochrome Dark | `https://static.neshan.org/sdk/maplibre/styles/monochrome_dark.json` |
| Pastel | `https://static.neshan.org/sdk/maplibre/styles/pastel.json` |

برای هماهنگی رنگ نقشه با برند فروشگاه، از [ویرایشگر استایل نشان](https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-style-editor/) فایل `style.json` سفارشی بگیرید و آدرس آن را در `style` بدهید.

### 4.3 انتخاب نقطه با کلیک و جابه‌جایی مارکر

الگوی استاندارد: یک مارکر قابل‌کشیدن؛ با کلیک روی نقشه یا کشیدن مارکر، مختصات جدید گرفته می‌شود.

```js
let marker = null;

function setPoint(lng, lat) {
  if (!marker) {
    marker = new maplibregl.Marker({ draggable: true })
      .setLngLat([lng, lat])
      .addTo(map);
    marker.on("dragend", () => {
      const p = marker.getLngLat();
      onPointChanged(p.lng, p.lat);
    });
  } else {
    marker.setLngLat([lng, lat]);
  }
  onPointChanged(lng, lat);
}

map.on("click", (e) => setPoint(e.lngLat.lng, e.lngLat.lat));
```

### 4.4 دکمه‌ی «موقعیت فعلی من»

```js
document.getElementById("btn-locate").addEventListener("click", () => {
  if (!navigator.geolocation) return alert("مرورگر شما از موقعیت‌یابی پشتیبانی نمی‌کند.");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      map.flyTo({ center: [longitude, latitude], zoom: 17 });
      setPoint(longitude, latitude);
    },
    () => alert("دسترسی به موقعیت داده نشد. لطفاً نقطه را روی نقشه انتخاب کنید."),
    { enableHighAccuracy: true, timeout: 10000 }
  );
});
```

> Geolocation مرورگر فقط روی **HTTPS** (و localhost) کار می‌کند. همیشه یک راه جایگزین (انتخاب دستی روی نقشه) هم بگذارید.

### 4.5 محدود کردن نقشه به منطقه‌ی خدمات‌رسانی

اگر فقط در یک شهر ارسال دارید (مثلاً تهران)، با `maxBounds` جابه‌جایی را محدود کنید و `minZoom` را هم ببندید:

```js
const tehranBounds = [
  [51.20, 35.55],   // جنوب‌غربی [lng, lat]
  [51.60, 35.83],   // شمال‌شرقی [lng, lat]
];

const map = new maplibregl.Map({
  /* ... */
  minZoom: 10,
  maxZoom: 18,
  maxBounds: tehranBounds,
});
```

---

## 5. گام دوم: تبدیل مختصات به آدرس (Reverse Geocoding)

**سرویس:** تبدیل نقطه به آدرس — `GET https://api.neshan.org/v5/reverse`

| پارامتر | توضیح | اجباری |
|---|---|---|
| `lat` | عرض جغرافیایی | بله |
| `lng` | طول جغرافیایی | بله |

**هدر:** `Api-Key: <کلید سرویس>`

```bash
curl --location 'https://api.neshan.org/v5/reverse?lat=35.7009&lng=51.3908' \
  --header 'Api-Key: <YOUR_SERVICE_KEY>'
```

**نمونه پاسخ:**

```json
{
  "status": "OK",
  "formatted_address": "تهران، دکتر فاطمی، حجاب، سازمان آب، بین دائمی و عبداله زاده",
  "route_name": "سازمان آب",
  "route_type": "secondary",
  "neighbourhood": "فاطمي",
  "city": "تهران",
  "state": "استان تهران",
  "place": null,
  "municipality_zone": "6",
  "in_traffic_zone": true,
  "in_odd_even_zone": true,
  "village": null,
  "county": "شهرستان تهران",
  "district": "بخش مرکزی شهرستان تهران"
}
```

**نقشه‌ی فیلدها به فرم فروشگاه:**

| فیلد پاسخ | استفاده در فرم آدرس |
|---|---|
| `state` | استان |
| `city` | شهر |
| `neighbourhood` | محله |
| `formatted_address` | متن پیشنهادی آدرس (قابل‌ویرایش توسط کاربر) |
| `route_name` | نام آخرین معبر |
| `municipality_zone` | منطقه شهرداری (مثلاً برای زون‌بندی ارسال) |
| `village` / `county` / `district` | آدرس‌های روستایی یا خارج از شهر |
| `in_traffic_zone` / `in_odd_even_zone` | مهم برای پیک‌های موتوری/خودرو در تهران |

> بسیاری از فیلدها (`place`، `village`، `neighbourhood`…) ممکن است `null` باشند؛ کد شما باید این حالت را مدیریت کند.

> نسخه‌ی قدیمی‌تر (`/v2/reverse`) هم وجود دارد که فیلد `addresses` اضافه دارد ولی نسخه‌ی v5 آخرین نسخه است و پیشنهاد می‌شود از آن استفاده کنید.

---

## 6. گام سوم: بک‌اند واسط (Proxy) برای مخفی ماندن کلید

اگر `Api-Key` سرویس را مستقیم در JavaScript فرانت‌اند بگذارید، هر کسی از DevTools آن را می‌بیند و سهمیه‌ی شما را مصرف می‌کند. راه‌حل: یک endpoint ساده در سرور خودتان.

### نمونه با Node.js + Express (Node 18+)

```js
// server.js
import express from "express";

const app = express();
app.use(express.json());

const NESHAN = "https://api.neshan.org";
const KEY = process.env.NESHAN_SERVICE_KEY;   // در .env نگه دارید، نه در کد

// محدوده‌ی تقریبی ایران؛ برای رد کردن مختصات بی‌معنی
const inIran = (lat, lng) => lat >= 24 && lat <= 40.5 && lng >= 43 && lng <= 64;

async function neshanGet(path) {
  const r = await fetch(NESHAN + path, { headers: { "Api-Key": KEY } });
  const body = await r.json().catch(() => ({}));
  return { status: r.status, body };
}

// 1) تبدیل مختصات به آدرس
app.get("/api/reverse", async (req, res) => {
  const lat = Number(req.query.lat);
  const lng = Number(req.query.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || !inIran(lat, lng)) {
    return res.status(400).json({ error: "مختصات نامعتبر است" });
  }
  const { status, body } = await neshanGet(`/v5/reverse?lat=${lat}&lng=${lng}`);
  res.status(status).json(body);
});

// 2) جستجو (نیازمند فعال‌سازی سرویس از طریق تیکت)
app.get("/api/search", async (req, res) => {
  const term = String(req.query.term || "").trim();
  const lat = Number(req.query.lat);
  const lng = Number(req.query.lng);
  if (term.length < 2 || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return res.status(400).json({ error: "پارامترها نامعتبر است" });
  }
  const q = encodeURIComponent(JSON.stringify({ term, center: { latitude: lat, longitude: lng } }));
  const { status, body } = await neshanGet(`/v3/search?q=${q}`);
  res.status(status).json(body);
});

app.listen(3000, () => console.log("http://localhost:3000"));
```

**پیشنهادهای تکمیلی در پروداکشن:**

- **Rate limit** روی endpointها (مثلاً با `express-rate-limit`) تا کاربر یا ربات سهمیه را نسوزاند.
- **کش کوتاه‌مدت** نتیجه‌ی reverse بر اساس مختصات گردشده (مثلاً تا ۵ رقم اعشار) برای کاهش تعداد درخواست.
- پاسخ‌های خطای `481` و `482` را لاگ کنید تا بفهمید به سقف سهمیه یا نرخ مجاز رسیده‌اید.

---

## 7. گام چهارم: فرم کامل آدرس (کد نمونه کامل)

این یک صفحه‌ی HTML کامل و قابل اجراست (با فرض وجود endpointهای بخش ۶). فقط `YOUR_WEB_MAP_KEY` را عوض کنید.

```html
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>انتخاب آدرس تحویل</title>

  <link rel="stylesheet" href="https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.css" />
  <script src="https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js"></script>

  <style>
    body { font-family: Tahoma, sans-serif; margin: 0; padding: 16px; max-width: 720px; margin-inline: auto; }
    #map { height: 360px; border-radius: 12px; }
    .row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
    .row > * { flex: 1 1 200px; padding: 10px; font: inherit; box-sizing: border-box; }
    textarea { width: 100%; padding: 10px; font: inherit; margin-top: 10px; box-sizing: border-box; }
    button { cursor: pointer; }
    #hint { color: #666; font-size: 13px; margin-top: 6px; }
    #status { color: #b00020; font-size: 13px; min-height: 18px; }
  </style>
</head>
<body>

  <h3>آدرس تحویل سفارش</h3>

  <div class="row">
    <button type="button" id="btn-locate">📍 موقعیت فعلی من</button>
  </div>

  <div id="map" style="margin-top:10px"></div>
  <div id="hint">روی نقشه کلیک کنید یا سنجاق را بکشید تا موقعیت دقیق خود را مشخص کنید.</div>
  <div id="status"></div>

  <form id="address-form">
    <input type="hidden" name="lat" id="lat" />
    <input type="hidden" name="lng" id="lng" />

    <div class="row">
      <input name="province" id="province" placeholder="استان" required />
      <input name="city" id="city" placeholder="شهر" required />
      <input name="neighbourhood" id="neighbourhood" placeholder="محله" />
    </div>

    <textarea name="address" id="address" rows="3" placeholder="آدرس کامل" required></textarea>

    <div class="row">
      <input name="plaque" placeholder="پلاک" required />
      <input name="unit" placeholder="واحد" />
      <input name="postal_code" placeholder="کدپستی (۱۰ رقم)" inputmode="numeric" maxlength="10" />
    </div>

    <div class="row">
      <input name="receiver_name" placeholder="نام تحویل‌گیرنده" required />
      <input name="receiver_phone" placeholder="شماره موبایل" inputmode="tel" required />
    </div>

    <div class="row">
      <button type="submit">ثبت آدرس</button>
    </div>
  </form>

<script>
  const maplibregl = window.maplibregl.default;
  const $ = (id) => document.getElementById(id);

  // ---------- نقشه ----------
  const map = new maplibregl.Map({
    container: "map",
    style: "https://static.neshan.org/sdk/maplibre/styles/light.json",
    center: [51.389, 35.6892],      // [lng, lat]
    zoom: 12,
    minZoom: 5,
    apiKey: "YOUR_WEB_MAP_KEY",
  });
  map.addControl(new maplibregl.NavigationControl());

  // ---------- مارکر ----------
  let marker = null;
  let reqSeq = 0;   // برای نادیده گرفتن پاسخ‌های قدیمی

  function setPoint(lng, lat) {
    if (!marker) {
      marker = new maplibregl.Marker({ draggable: true }).setLngLat([lng, lat]).addTo(map);
      marker.on("dragend", () => {
        const p = marker.getLngLat();
        onPointChanged(p.lng, p.lat);
      });
    } else {
      marker.setLngLat([lng, lat]);
    }
    onPointChanged(lng, lat);
  }

  map.on("click", (e) => setPoint(e.lngLat.lng, e.lngLat.lat));

  $("btn-locate").addEventListener("click", () => {
    if (!navigator.geolocation) return ($("status").textContent = "مرورگر از موقعیت‌یابی پشتیبانی نمی‌کند.");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        map.flyTo({ center: [longitude, latitude], zoom: 17 });
        setPoint(longitude, latitude);
      },
      () => ($("status").textContent = "دسترسی به موقعیت داده نشد؛ لطفاً نقطه را روی نقشه انتخاب کنید."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });

  // ---------- دریافت آدرس ----------
  async function onPointChanged(lng, lat) {
    $("lat").value = lat.toFixed(6);
    $("lng").value = lng.toFixed(6);
    $("status").textContent = "در حال دریافت آدرس…";

    const mySeq = ++reqSeq;
    try {
      const r = await fetch(`/api/reverse?lat=${lat}&lng=${lng}`);
      const data = await r.json();
      if (mySeq !== reqSeq) return;                      // پاسخ قدیمی است
      if (!r.ok || data.status !== "OK") throw new Error();

      $("province").value = (data.state || "").replace(/^استان\s*/, "");
      $("city").value = data.city || data.village || "";
      $("neighbourhood").value = data.neighbourhood || "";
      $("address").value = data.formatted_address || "";
      $("status").textContent = "";
    } catch {
      if (mySeq === reqSeq) $("status").textContent = "آدرس این نقطه دریافت نشد؛ لطفاً آدرس را دستی وارد کنید.";
    }
  }

  // ---------- ثبت ----------
  $("address-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!$("lat").value) return ($("status").textContent = "لطفاً ابتدا موقعیت خود را روی نقشه مشخص کنید.");

    const payload = Object.fromEntries(new FormData(e.target));
    const r = await fetch("/api/addresses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    $("status").style.color = r.ok ? "green" : "#b00020";
    $("status").textContent = r.ok ? "آدرس ثبت شد ✓" : "ثبت آدرس ناموفق بود.";
  });
</script>
</body>
</html>
```

**نکات UX مهم:**

- آدرس خودکار را **قابل‌ویرایش** بگذارید؛ کاربر باید بتواند پلاک، واحد، طبقه و توضیحات تکمیلی بدهد.
- اگر آدرس دریافت نشد، فرم نباید قفل شود؛ کاربر باید بتواند دستی تایپ کند.
- متغیر `reqSeq` از مشکل رایج «پاسخ قدیمی، آدرس جدید را بازنویسی می‌کند» جلوگیری می‌کند (وقتی کاربر سریع مارکر را جابه‌جا می‌کند).
- هنگام کشیدن مارکر درخواست نفرستید، فقط بعد از `dragend` (همان‌طور که در کد بالاست).

---

## 8. جستجوی آدرس و مکان (Search)

برای اینکه کاربر بتواند به‌جای کلیک روی نقشه، نام خیابان/محله/مکان را تایپ کند.

> ⚠️ این سرویس برای فعال‌سازی نیاز به **تیکت پشتیبانی** دارد.

**سرویس:** `GET https://api.neshan.org/v3/search` — پارامتر `q` یک JSON است که باید URL-encode شود:

```json
{ "term": "میدان تجریش", "center": { "latitude": 35.8069, "longitude": 51.4287 } }
```

- `term` و `center` هر دو **اجباری** هستند. `center` می‌تواند موقعیت فعلی کاربر یا مرکز نقشه‌ی در حال نمایش باشد.
- نتایج بر اساس فاصله از `center` مرتب می‌شوند و حداکثر **۳۰ نتیجه** برمی‌گردد.

**نمونه پاسخ (کوتاه‌شده):**

```json
{
  "count": 19,
  "items": [
    {
      "title": "میدان تجریش",
      "address": "میدان تجریش",
      "category": "place",
      "type": "town_square",
      "region": "تهران، استان تهران",
      "neighbourhood": "",
      "location": { "x": 51.4288, "y": 35.8069 },
      "poiHash": "..."
    }
  ]
}
```

> ⚠️ در `location` مقدار `x` همان **طول (lng)** و `y` همان **عرض (lat)** است.

**نکته‌ی `category`:** یکی از `place` (مکان)، `municipal` (معبر شهری)، `region` (شهر/روستا/استان). برای آدرس‌دهی تحویل کالا معمولاً `place` و `municipal` مفید هستند.

**کد فرانت‌اند (با debounce):**

```js
let t;
$("search-input").addEventListener("input", (e) => {
  clearTimeout(t);
  const term = e.target.value.trim();
  if (term.length < 2) return;
  t = setTimeout(async () => {
    const c = map.getCenter();
    const r = await fetch(`/api/search?term=${encodeURIComponent(term)}&lat=${c.lat}&lng=${c.lng}`);
    const data = await r.json();
    renderResults(data.items || []);
  }, 400);
});

function renderResults(items) {
  // هر آیتم را در یک لیست نمایش بده؛ با کلیک:
  // map.flyTo({ center: [it.location.x, it.location.y], zoom: 17 });
  // setPoint(it.location.x, it.location.y);
}
```

> بدون debounce، هر کلید تایپ‌شده یک درخواست می‌زند و خیلی سریع به خطای `482 RateExceeded` می‌رسید.

---

## 9. تبدیل آدرس متنی به مختصات (Geocoding)

مناسب برای زمانی که آدرس کاربر را از قبل دارید (مثلاً آدرس‌های قدیمی ثبت‌شده در سایت) و می‌خواهید روی نقشه نشانش دهید.

### سرویس «پلاس» (پیشنهادی)

`GET https://api.neshan.org/geocoding/v1/plus?json={...}` (پارامتر `json` باید URL-encode شود)

| پارامتر | توضیح | اجباری |
|---|---|---|
| `address` | آدرس متنی | بله |
| `province` | استان | خیر |
| `city` | شهر | خیر |
| `location` | مرکز جستجو `{latitude, longitude}` | خیر |
| `extent` | کادر جستجو `{southWest, northEast}` | خیر |

**نمونه درخواست:**

```bash
curl --location --globoff 'https://api.neshan.org/geocoding/v1/plus?json={
  "address": "تهران بلوار ستارخان خیابان داوود اسدی رحیمی",
  "city": "تهران",
  "province": "تهران"
}' --header 'Api-Key: YOUR_API_KEY'
```

**پاسخ:** آرایه‌ی `items` (تا ۵ پیشنهاد) که هر کدام `location` (شامل `latitude` و `longitude`)، `province`، `city`، `neighbourhood` و `unMatchedTerm` دارند.

**فیلد کلیدی `unMatchedTerm`:** بخشی از آدرس ورودی که روی نقشه پیدا **نشده** است. می‌توانید با آن به کاربر هشدار دهید («پلاک ۱۰ روی نقشه پیدا نشد؛ لطفاً سنجاق را دستی جابه‌جا کنید.») و نتیجه را به‌عنوان «حدس اولیه» نشان دهید، نه واقعیت قطعی.

**تفاوت سرویس عادی و پلاس:**

| قابلیت | عادی | پلاس |
|---|:---:|:---:|
| تبدیل آدرس تا آخرین معبر اصلی | ✓ | ✓ |
| فیلتر استان/شهر، کادر جستجو، مرکز جستجو | ✓ | ✓ |
| **آدرس‌یابی بر اساس پلاک** (تهران، مشهد، کرج، اصفهان، اهواز) | — | ✓ |
| در نظر گرفتن اطلاعات مکانی ثبت‌شده (POI) | — | ✓ |

**چطور دقت را بالا ببریم:**

- آدرس را با ترتیب بزرگ‌به‌کوچک بنویسید: `استان + شهر/روستا + میدان + خیابان + کوچه + پلاک`.
- اجزای آدرس را با فاصله جدا کنید (`شهید بابایی` نه `شهیدبابایی`).
- در آدرس‌های پستی، ۵ رقم اول کدپستی (گشت کدپستی) به دقت کمک می‌کند.
- استان و شهر را در فیلدهای جدا بفرستید.

> نسخه‌های قدیمی‌تر (`/v4/geocoding`, `/v6/geocoding`) فقط یک نقطه با `location.x/y` برمی‌گردانند و از نسخه‌ی پلاس ساده‌تر هستند.

---

## 10. اعتبارسنجی و ذخیره آدرس در سرور

**هرگز به داده‌ی ارسالی مرورگر اعتماد کامل نکنید.** کاربر می‌تواند فیلدهای hidden را دستکاری کند.

### 10.1 ساختار پیشنهادی جدول

```sql
CREATE TABLE addresses (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL,
  receiver_name    TEXT   NOT NULL,
  receiver_phone   TEXT   NOT NULL,
  province         TEXT   NOT NULL,
  city             TEXT   NOT NULL,
  neighbourhood    TEXT,
  address_text     TEXT   NOT NULL,       -- آدرس نهایی که کاربر تأیید کرده
  plaque           TEXT   NOT NULL,
  unit             TEXT,
  postal_code      CHAR(10),
  lat              DOUBLE PRECISION NOT NULL,
  lng              DOUBLE PRECISION NOT NULL,
  neshan_raw       JSONB,                 -- پاسخ خام reverse برای پشتیبانی/عیب‌یابی
  municipality_zone TEXT,
  created_at       TIMESTAMPTZ DEFAULT now()
);
```

### 10.2 نمونه‌ی endpoint ثبت آدرس

```js
app.post("/api/addresses", async (req, res) => {
  const b = req.body;
  const lat = Number(b.lat), lng = Number(b.lng);

  // 1) اعتبارسنجی پایه
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || !inIran(lat, lng))
    return res.status(400).json({ error: "موقعیت نامعتبر" });
  if (!/^09\d{9}$/.test(b.receiver_phone || ""))
    return res.status(400).json({ error: "شماره موبایل نامعتبر" });
  if (b.postal_code && !/^\d{10}$/.test(b.postal_code))
    return res.status(400).json({ error: "کدپستی نامعتبر" });

  // 2) تأیید موقعیت از سمت سرور (استان/شهر را از روی مختصات دوباره بگیر)
  const { status, body: geo } = await neshanGet(`/v5/reverse?lat=${lat}&lng=${lng}`);
  if (status !== 200 || geo.status !== "OK")
    return res.status(422).json({ error: "موقعیت قابل تشخیص نیست" });

  // 3) بررسی قابل‌ارسال بودن به این شهر
  const deliverableCities = ["تهران", "کرج"];            // نمونه
  if (!deliverableCities.includes(geo.city))
    return res.status(422).json({ error: "به این منطقه ارسال نداریم" });

  // 4) ذخیره (استان/شهر معتبر را از reverse بردار، متن آدرس را از کاربر)
  // await db.insert({ ...b, province: geo.state, city: geo.city, neshan_raw: geo, ... });
  res.json({ ok: true });
});
```

### 10.3 نکات

- مختصات را با دقت ۶ رقم اعشار ذخیره کنید (حدود ۱۰ سانتی‌متر دقت).
- هم **متن آدرس تأییدشده‌ی کاربر** و هم **مختصات** را نگه دارید؛ متن برای پیک و فاکتور، مختصات برای مسیریابی و محاسبه‌ی هزینه.
- بهتر است پاسخ خام reverse را هم ذخیره کنید تا در اختلاف‌ها (پیک آدرس را پیدا نکرد) قابل بررسی باشد.
- تمام اطلاعات آدرس و تلفن داده‌ی شخصی است؛ قوانین حریم خصوصی را رعایت کنید.

---

## 11. قابلیت‌های تکمیلی برای فروشگاه

### 11.1 محاسبه‌ی هزینه و زمان ارسال — Distance Matrix

فاصله و زمان بین انبار (مبدأ) و آدرس مشتری (مقصد):

```
GET https://api.neshan.org/v1/distance-matrix?type=car&origins=LAT,LNG&destinations=LAT,LNG
```

- `type`: `car` یا `motorcycle` (پیش‌فرض `car`)
- `origins` و `destinations`: لیستی از `lat,lng` جداشده با `|` (پایپ؛ در URL به‌صورت `%7C`)
- هدر `Api-Key` لازم است.

```js
const { body } = await neshanGet(
  `/v1/distance-matrix?type=motorcycle&origins=${wh.lat},${wh.lng}&destinations=${lat},${lng}`
);
const el = body.rows?.[0]?.elements?.[0];
if (el?.status === "Ok") {
  const km = el.distance.value / 1000;       // value بر حسب متر
  const minutes = el.duration.value / 60;    // value بر حسب ثانیه
  const shippingFee = baseFee + km * perKm;
}
```

**مقادیر `status` هر المان:** `Ok`، `NoRoute` (مسیری یافت نشد)، `UnknownError`.
این سرویس با داده‌ی ترافیک آنلاین کار می‌کند؛ برای تخمین‌های پایدارتر می‌توانید از مسیریابی «الگوی ترافیک» (typical) استفاده کنید.

### 11.2 محدوده‌ی تحویل بر اساس زمان — Isochrone

اگر می‌گویید «تحویل ظرف ۳۰ دقیقه»، محدوده‌ی قابل‌دسترس از انبار را بگیرید و بررسی کنید آدرس مشتری داخلش هست یا نه:

```
GET https://api.neshan.org/v2/isochrone?latitude=35.7&longitude=51.4&time=30&dataset=MOTORCYCLE&polygons=true
```

- `time` (دقیقه) **یا** `distance` (کیلومتر)؛ هر دو را همزمان نفرستید (خطای 400).
- `dataset`: `PRIMARY` (خودرو، ترافیک زنده)، `TYPICAL`، `NO_TRAFFIC`، `MOTORCYCLE`، `BICYCLE`، `PEDESTRIAN`.
- `polygons=true` خروجی را به‌صورت `Polygon` می‌دهد.
- ⚠️ مختصات در پاسخ GeoJSON به‌صورت `[longitude, latitude]` است.

برای بررسی «نقطه داخل چندضلعی» در سرور از کتابخانه‌هایی مثل [Turf.js](https://turfjs.org/) (`booleanPointInPolygon`) استفاده کنید. همین چندضلعی را می‌توانید روی نقشه هم رسم کنید تا کاربر محدوده‌ی خدمات‌رسانی را ببیند.

### 11.3 نمایش مسیر پیک روی نقشه (پیگیری سفارش)

خروجی سرویس مسیریابی (`/v4/direction`) را بگیرید، `polyline` هر گام را decode کنید و به‌صورت لایه‌ی `line` روی نقشه بکشید. نمونه‌ی کامل: [رسم مسیر روی نقشه (MapLibre)](https://platform.neshan.org/docs/sdk/web/maplibre/examples/neshan-maplibre-draw-route).

> ⚠️ خروجی `polyline.decode` به‌صورت `[lat, lng]` است ولی MapLibre و GeoJSON ترتیب `[lng, lat]` می‌خواهند؛ حتماً جابه‌جا کنید.

### 11.4 لیست استان‌ها و شهرستان‌ها (Region)

اگر علاوه بر نقشه، فرم دستی «انتخاب استان → شهر» هم می‌خواهید:

- `GET https://api.neshan.org/v2/region/provinces` ← لیست استان‌ها (`id`, `name`)
- `GET https://api.neshan.org/v2/region/provinces/{provinceId}/cities` ← لیست شهرستان‌ها
- با افزودن `/geometry` به انتهای هر دو، مرز جغرافیایی (WKT) هم برگردانده می‌شود (حجم بسیار بیشتر).

> این سرویس هم نیاز به **فعال‌سازی با تیکت** دارد. ترتیب مختصات در WKT: عدد اول طول، عدد دوم عرض.

### 11.5 نمایش نقشه‌ی ثابت در ایمیل و فاکتور — Static Map

برای ایمیل تأیید سفارش یا صفحه‌ی فاکتور، یک تصویر ثابت از موقعیت تحویل:

```
https://api.neshan.org/v5/static?key=<KEY>&style=light&width=600&height=300&zoom=16&latitude=35.7009&longitude=51.3908&marker=red
```

- `zoom` بین ۵ تا ۱۹؛ `width` و `height` بین ۲۰۰ تا ۲۰۴۸ پیکسل.
- `marker`: `red`، `green`، `blue`، `violet` یا توکن آیکون آپلودشده در پنل.
- ⚠️ در مستندات، توضیح پارامترهای `latitude` و `longitude` این سرویس جابه‌جا نوشته شده (طول/عرض)؛ در عمل `latitude` = عرض و `longitude` = طول است (مطابق مثال رسمی). با یک نقطه‌ی مشخص تست کنید.
- چون کلید در URL قرار می‌گیرد، این تصویر را **از سرور** تولید و ذخیره/سرو کنید، نه اینکه کلید در HTML ایمیل قرار بگیرد.

### 11.6 اپلیکیشن موبایل

اگر فروشگاه اپ هم دارد، همین منطق با SDKهای Android و iOS (هر دو بر پایه‌ی MapLibre Native) قابل پیاده‌سازی است:

- **Android:** وابستگی `org.neshan.maplibre:android-sdk-opengl:13.4.1` + متادیتای `org.maplibre.android.API_KEY` در Manifest.
- **iOS:** Swift Package محلی + کلید `MLNApiKey` در `Info.plist`.
- استایل‌های آماده همان آدرس‌های `.../styles/*.json` هستند.

---

## 12. خطاها و عیب‌یابی

### کدهای خطای مشترک تمام سرویس‌ها

| HTTP | Status | معنی | اقدام |
|---|---|---|---|
| 400 | `INVALID_ARGUMENT` | پارامتر ورودی نامعتبر | فرمت پارامترها را بررسی کنید |
| 470 | `CoordinateParseError` | مختصات نامعتبر | ترتیب و فرمت `lat,lng` |
| 480 | `KeyNotFound` | کلید نامعتبر/ارسال‌نشده | هدر `Api-Key` را بررسی کنید |
| 481 | `LimitExceeded` | سقف سهمیه تمام شد | پلن را ارتقا دهید / کش اضافه کنید |
| 482 | `RateExceeded` | سقف درخواست در دقیقه | debounce، rate-limit، retry با تأخیر |
| 483 | `ApiKeyTypeError` | کلید با سرویس هم‌خوانی ندارد | کلید مخصوص همان سرویس را بسازید |
| 484 | `ApiWhiteListError` | دامنه/IP مجاز نیست | لیست مجاز کلید را در پنل اصلاح کنید |
| 485 | `ApiServiceListError` | سرویس برای این کلید فعال نیست | سرویس را به کلید اضافه کنید |
| 500 | `GenericError` | خطای ناشناخته | بعداً دوباره تلاش کنید |

### مشکلات رایج نقشه

| علامت | علت | راه‌حل |
|---|---|---|
| کنترل‌ها/کانواس بدون استایل | CSS پکیج import نشده | CSS را اضافه کنید |
| `Map is not a constructor` / `window.maplibregl is undefined` | در حالت CDN | از `window.maplibregl.default` استفاده کنید |
| `Api key is not defined!` | `apiKey` در ساخت نقشه ندارید | کلید نقشه وب را بدهید |
| نقشه خاکستری/تایل لود نمی‌شود | کلید اشتباه یا دامنه مجاز نیست | کنسول و تب Network را بررسی کنید (کدهای 480/484…) |
| خطا در Next.js/SSR: `window is not defined` | نقشه در سمت سرور ساخته می‌شود | نقشه را فقط داخل `useEffect` بسازید یا کامپوننت را با `ssr: false` لود کنید |
| دو نقشه در یک صفحه با کلیدهای متفاوت | `apiKey` به‌ازای هر **صفحه** ذخیره می‌شود | در هر صفحه از یک کلید واحد استفاده کنید |
| نقشه روی مرورگر قدیمی کار نمی‌کند | نیاز به `DecompressionStream` | حداقل Chrome 80+، Firefox 113+، Safari 16.4+ |

### نمونه‌ی ساخت نقشه در React (تمیزکاری حتماً لازم است)

```jsx
import { useEffect, useRef } from "react";
import maplibregl from "@neshan-maps-platform/maplibre-sdk";
import "@neshan-maps-platform/maplibre-sdk/style.css";

export default function AddressMap({ apiKey, onPick }) {
  const ref = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: "https://static.neshan.org/sdk/maplibre/styles/light.json",
      center: [51.389, 35.6892],
      zoom: 12,
      apiKey,
    });
    map.on("click", (e) => onPick(e.lngLat.lng, e.lngLat.lat));
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, [apiKey]);

  return <div ref={ref} style={{ height: 360 }} />;
}
```

در Next.js این کامپوننت را با `"use client"` علامت‌گذاری کنید و با `dynamic(() => import(...), { ssr: false })` لود کنید.

---

## 13. نکات مهم و تله‌های رایج

### ⚠️ ترتیب مختصات (رایج‌ترین باگ)

| جا | ترتیب |
|---|---|
| پارامترهای ورودی اغلب وب‌سرویس‌ها (`origin`, `origins`, `waypoints`, `location`…) | `latitude,longitude` |
| `center` و `setLngLat` و `flyTo` در **MapLibre** | `[longitude, latitude]` |
| `location.x / location.y` در پاسخ **Search** و **Geocoding قدیمی** و **POI** | `x`=طول، `y`=عرض |
| `location` در پاسخ **Geocoding پلاس** | `{latitude, longitude}` (صریح) |
| `coordinates` در **GeoJSON** و **Isochrone** | `[lng, lat]` |
| `start_location` در گام‌های مسیریابی | `[lng, lat]` |
| `snappedPoints[].location` در Map Matching | `[lat, lng]` |
| خروجی `polyline.decode` | `[lat, lng]` |
| `location` در پاسخ **TSP** | `[lng, lat]` |

### نکات امنیتی و کارایی

- کلید سرویس فقط در سرور؛ کلید نقشه وب با دامنه‌ی مجاز محدود شود.
- همیشه ورودی کاربر را در سرور اعتبارسنجی کنید و موقعیت را دوباره reverse کنید.
- روی endpointهای proxy **rate limit** بگذارید.
- از debounce برای جستجو و از `dragend` به‌جای `drag` استفاده کنید.
- نتایج reverse را کوتاه‌مدت کش کنید.
- خطاهای `481`/`482` را مانیتور کنید.

### نکات تجربه‌ی کاربری

- آدرس خودکار فقط «پیش‌فرض» است، نه نهایی؛ فیلد پلاک و واحد را اجباری و جدا بگذارید.
- دقت آدرس در همه‌ی نقاط یکسان نیست (به‌خصوص روستاها و معابر فرعی). نقشه را برای تأیید دقیق موقعیت و تحویل، در کنار فیلد توضیحات (مثلاً «زنگ سوم، ورودی پشتی») نشان دهید.
- پلاک‌یابی در سرویس ژئوکدینگ فقط در چند شهر بزرگ (تهران، مشهد، کرج، اصفهان، اهواز) پشتیبانی می‌شود (در نسخه‌ی پلاس)؛ برای بقیه‌ی شهرها اتکا به انتخاب دستی روی نقشه مطمئن‌تر است.
- در موبایل، ارتفاع نقشه را کافی (حداقل ۳۰۰–۴۰۰ پیکسل) بگیرید و اسکرول صفحه را با نقشه تداخل ندهید.

### حقوقی و برند

- لوگو و کپی‌رایت نشان قابل حذف نیست (فقط با `logoPosition` و `copyRightPosition` جابه‌جا می‌شود).
- شرایط استفاده‌ی نشان و سقف رایگان را در [تعرفه‌ها](https://platform.neshan.org/pricing/) بررسی کنید؛ برای ترافیک بالای فروشگاه، پلن مناسب بگیرید.

---

## 14. چک‌لیست نهایی

- [ ] ثبت‌نام در پنل نشان و دریافت **کلید نقشه وب** و **کلید سرویس**
- [ ] ثبت تیکت برای فعال‌سازی سرویس‌های مورد نیاز (Search، در صورت نیاز Region/Nearby/POI)
- [ ] محدود کردن کلیدها به دامنه/IP
- [ ] نصب MapLibre SDK نشان (و import کردن CSS)
- [ ] ساخت نقشه با `apiKey` و `center` به‌صورت `[lng, lat]`
- [ ] مارکر قابل‌کشیدن + کلیک روی نقشه + دکمه‌ی «موقعیت من»
- [ ] ساخت endpointهای proxy (`/api/reverse`، `/api/search`) با اعتبارسنجی و rate-limit
- [ ] پر کردن خودکار فرم (استان، شهر، محله، آدرس) و امکان ویرایش دستی
- [ ] فیلدهای جدای پلاک، واحد، کدپستی، گیرنده و موبایل
- [ ] مدیریت پاسخ‌های قدیمی (`reqSeq`) و حالت خطا
- [ ] اعتبارسنجی سمت سرور و reverse مجدد هنگام ثبت آدرس
- [ ] بررسی محدوده‌ی تحویل (فهرست شهرها یا Isochrone)
- [ ] محاسبه‌ی هزینه/زمان ارسال با Distance Matrix (اختیاری)
- [ ] ذخیره‌ی هم متن آدرس و هم `lat/lng`
- [ ] تست روی موبایل، HTTPS و مرورگرهای مختلف
- [ ] مانیتورینگ خطاهای 481 و 482

---

## 15. لینک‌های مرجع

| موضوع | لینک |
|---|---|
| صفحه‌ی اصلی مستندات | https://platform.neshan.org/docs/ |
| ثبت‌نام و دریافت کلید | https://platform.neshan.org/panel |
| MapLibre SDK نشان (وب) | https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-gl-js/ |
| ویرایشگر استایل | https://platform.neshan.org/docs/sdk/web/maplibre/neshan-maplibre-style-editor/ |
| مثال: دریافت مختصات با کلیک | https://platform.neshan.org/docs/sdk/web/maplibre/examples/neshan-maplibre-get-coord |
| مثال: محدود کردن ناحیه نقشه | https://platform.neshan.org/docs/sdk/web/maplibre/examples/neshan-maplibre-limit-bounds |
| مثال: مارکر سفارشی | https://platform.neshan.org/docs/sdk/web/maplibre/examples/neshan-maplibre-custom-marker |
| مثال: خوشه‌بندی نقاط | https://platform.neshan.org/docs/sdk/web/maplibre/examples/neshan-maplibre-clustering |
| مثال: رسم مسیر | https://platform.neshan.org/docs/sdk/web/maplibre/examples/neshan-maplibre-draw-route |
| تبدیل نقطه به آدرس (Reverse) | https://platform.neshan.org/docs/api/search-category/reverse-geocoding/ |
| تبدیل آدرس به نقطه (Geocoding) | https://platform.neshan.org/docs/api/search-category/geocoding/ |
| جستجوی مکان‌مبنا (Search) | https://platform.neshan.org/docs/api/search-category/search/ |
| مکان‌های نزدیک (Nearby) | https://platform.neshan.org/docs/api/search-category/nearby/ |
| جزئیات مکان (POI) | https://platform.neshan.org/docs/api/search-category/poi-details/ |
| استان‌ها و شهرستان‌ها (Region) | https://platform.neshan.org/docs/api/search-category/region/ |
| ماتریس فاصله | https://platform.neshan.org/docs/api/routing-category/distance-matrix/ |
| محدوده‌ی دسترس (Isochrone) | https://platform.neshan.org/docs/api/routing-category/isochrone/ |
| مسیریابی | https://platform.neshan.org/docs/api/routing-category/routing/ |
| نقشه‌ی استاتیک | https://platform.neshan.org/docs/api/static-map-category/static-map/ |
| SDK اندروید | https://platform.neshan.org/docs/sdk/android/neshan-android-sdk-getting-started/ |
| SDK iOS | https://platform.neshan.org/docs/sdk/ios/neshan-ios-sdk-getting-started/ |
| MCP نشان (برای ایجنت‌های هوش مصنوعی) | https://platform.neshan.org/docs/mcp/ |
| تعرفه‌ها | https://platform.neshan.org/pricing/ |
| قوانین و شرایط | https://platform.neshan.org/tos/ |
| پشتیبانی (تیکت) | https://platform.neshan.org/panel/support/ticketing |

---

> **یادآوری:** مشخصات endpointها و پارامترها ممکن است در طول زمان تغییر کند. پیش از انتشار نهایی، صفحه‌ی هر سرویس را در مستندات رسمی نشان یک‌بار دیگر بررسی کنید.
