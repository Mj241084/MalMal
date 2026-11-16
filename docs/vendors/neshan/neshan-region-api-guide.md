# راهنمای استفاده از Region API نشان (لیست استان‌ها و شهرستان‌ها)

با این سرویس می‌توانید **لیست استان‌های ایران** را به همراه شناسه (ID) هر استان دریافت کنید و سپس با ارسال شناسه‌ی یک استان، **لیست شهرستان‌های** آن استان را بگیرید. هر دو اندپوینت نسخه‌ی «با جئومتری» هم دارند که علاوه بر شناسه و نام، **محدوده‌ی جغرافیایی (مرز)** را نیز برمی‌گرداند.

کاربردها:

- ساخت منوها و فیلترهای انتخاب استان و شهر
- اعتبارسنجی آدرس‌ها
- تحلیل‌های منطقه‌ای
- ترسیم مرز مناطق روی نقشه

> **نکته:** برای فعال‌سازی این سرویس، لطفاً از طریق ارسال تیکت در [پنل کاربری نشان](https://platform.neshan.org/panel/support/ticketing) با پشتیبانی تماس بگیرید.

---

## ۰. پیش‌نیاز: دریافت کلید API

1. در [پنل توسعه‌دهندگان نشان](https://platform.neshan.org/panel) ثبت‌نام کنید و کلید API دریافت کنید.
2. کلید را در هدر `Api-Key` هر درخواست ارسال کنید.

---

## ۱. لیست استان‌ها

### آدرس Endpoint

| نوع خروجی | متد | آدرس |
|---|---|---|
| بدون جئومتری | `GET` | `https://api.neshan.org/v2/region/provinces` |
| با جئومتری | `GET` | `https://api.neshan.org/v2/region/provinces/geometry` |

> اندپوینت با جئومتری حجیم‌تر است. اگر فقط به شناسه و نام استان‌ها نیاز دارید (مثلاً برای منوی انتخاب استان)، از اندپوینت بدون جئومتری استفاده کنید.

### هدرهای درخواست

| هدر | مقدار |
|---|---|
| `Api-Key` | کلید API شما |

### پارامترهای ورودی

این اندپوینت پارامتر ورودی ندارد.

### نمونه درخواست

**cURL**

```bash
curl --location 'https://api.neshan.org/v2/region/provinces' \
--header 'Api-Key: <YOUR_API_KEY>'
```

**JavaScript (Fetch)**

```javascript
const myHeaders = new Headers();
myHeaders.append("Api-Key", "<YOUR_API_KEY>");

const requestOptions = {
  method: "GET",
  headers: myHeaders,
  redirect: "follow"
};

fetch("https://api.neshan.org/v2/region/provinces", requestOptions)
  .then((response) => response.json())
  .then((result) => console.log(result))
  .catch((error) => console.error(error));
```

**Python**

```python
import requests

url = "https://api.neshan.org/v2/region/provinces"

headers = {"Api-Key": "<YOUR_API_KEY>"}

response = requests.get(url, headers=headers)

print(response.json())
```

**PHP**

```php
<?php

$curl = curl_init();

curl_setopt_array($curl, array(
  CURLOPT_URL => 'https://api.neshan.org/v2/region/provinces',
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_ENCODING => '',
  CURLOPT_MAXREDIRS => 10,
  CURLOPT_TIMEOUT => 0,
  CURLOPT_FOLLOWLOCATION => true,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => 'GET',
  CURLOPT_HTTPHEADER => array(
    'Api-Key: <YOUR_API_KEY>'
  ),
));

$response = curl_exec($curl);
curl_close($curl);

echo $response;

?>
```

### فرمت پاسخ

پاسخ یک آرایه از آبجکت‌های استان است:

```json
[
  { "id": 3581, "name": "استان یزد" },
  { "id": 3641, "name": "استان لرستان" },
  { "id": 3595, "name": "استان اصفهان" },
  { "id": 3682, "name": "استان خوزستان" }
]
```

در پاسخ اندپوینت `provinces/geometry`، هر آبجکت علاوه بر `id` و `name` فیلد `geometry` را نیز دارد.

### اجزای پاسخ

| فیلد | توضیح |
|---|---|
| `id` | شناسه‌ی عددی استان. این مقدار ورودی سرویس لیست شهرستان‌ها است. |
| `name` | نام استان. |
| `geometry` | محدوده‌ی جغرافیایی استان به صورت رشته‌ی WKT. فقط در اندپوینت `provinces/geometry` وجود دارد. |

---

## ۲. لیست شهرستان‌های هر استان

### آدرس Endpoint

شناسه‌ی استان (`provinceId`) را در مسیر درخواست قرار دهید:

| نوع خروجی | متد | آدرس |
|---|---|---|
| بدون جئومتری | `GET` | `https://api.neshan.org/v2/region/provinces/{provinceId}/cities` |
| با جئومتری | `GET` | `https://api.neshan.org/v2/region/provinces/{provinceId}/cities/geometry` |

### هدرهای درخواست

| هدر | مقدار |
|---|---|
| `Api-Key` | کلید API شما |

### پارامترهای ورودی

| پارامتر | نوع | توضیح | الزامی |
|---|---|---|---|
| `provinceId` | Integer | شناسه‌ی استان که در مسیر (Path) قرار می‌گیرد. از فیلد `id` در خروجی لیست استان‌ها به‌دست می‌آید. | **بله** |

### نمونه درخواست

**cURL** (استان لرستان با شناسه‌ی `3641`)

```bash
curl --location 'https://api.neshan.org/v2/region/provinces/3641/cities' \
--header 'Api-Key: <YOUR_API_KEY>'
```

**JavaScript (Fetch)**

```javascript
const myHeaders = new Headers();
myHeaders.append("Api-Key", "<YOUR_API_KEY>");

const provinceId = 3641;

const requestOptions = {
  method: "GET",
  headers: myHeaders,
  redirect: "follow"
};

fetch(`https://api.neshan.org/v2/region/provinces/${provinceId}/cities`, requestOptions)
  .then((response) => response.json())
  .then((result) => console.log(result))
  .catch((error) => console.error(error));
```

**Python**

```python
import requests

province_id = 3641
url = f"https://api.neshan.org/v2/region/provinces/{province_id}/cities"

headers = {"Api-Key": "<YOUR_API_KEY>"}

response = requests.get(url, headers=headers)

print(response.json())
```

**PHP**

```php
<?php

$provinceId = 3641;
$url = "https://api.neshan.org/v2/region/provinces/{$provinceId}/cities";

$curl = curl_init();

curl_setopt_array($curl, array(
  CURLOPT_URL => $url,
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_ENCODING => '',
  CURLOPT_MAXREDIRS => 10,
  CURLOPT_TIMEOUT => 0,
  CURLOPT_FOLLOWLOCATION => true,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => 'GET',
  CURLOPT_HTTPHEADER => array(
    'Api-Key: <YOUR_API_KEY>'
  ),
));

$response = curl_exec($curl);
curl_close($curl);

echo $response;

?>
```

### فرمت پاسخ

پاسخ یک آرایه از آبجکت‌های شهرستان است (نمونه برای استان لرستان):

```json
[
  { "id": 1084, "name": "بروجرد" },
  { "id": 1065, "name": "بیران شهر" },
  { "id": 1051, "name": "الشتر" },
  { "id": 1063, "name": "خرم آباد" }
]
```

در پاسخ اندپوینت `cities/geometry` هر شهرستان فیلد `geometry` نیز دارد:

```json
[
  {
    "id": 1084,
    "name": "بروجرد",
    "geometry": "POLYGON ((48.71005579999999 33.932573299599625, 48.7103566 33.930705999599574, ...))"
  }
]
```

### اجزای پاسخ

| فیلد | توضیح |
|---|---|
| `id` | شناسه‌ی عددی شهرستان. |
| `name` | نام شهرستان. |
| `geometry` | محدوده‌ی جغرافیایی شهرستان به صورت رشته‌ی WKT. فقط در اندپوینت `cities/geometry` وجود دارد. |

---

## ۳. ساختار فیلد `geometry`

فیلد `geometry` یک رشته‌ی متنی در قالب استاندارد **WKT (Well-Known Text)** است؛ برای مثال:

```
POLYGON ((x1 y1, x2 y2, ...))
```

- در هر جفت مختصات، **عدد اول طول جغرافیایی (Longitude)** و **عدد دوم عرض جغرافیایی (Latitude)** است. این ترتیب برعکس ترتیب رایج `lat,lng` است؛ پیش از رسم روی نقشه به آن دقت کنید.
- برای تبدیل این رشته به GeoJSON و نمایش روی نقشه می‌توانید از کتابخانه‌هایی مانند [wellknown](https://www.npmjs.com/package/wellknown) یا [wkx](https://www.npmjs.com/package/wkx) در جاوااسکریپت و [Shapely](https://shapely.readthedocs.io/) در پایتون استفاده کنید.

---

## ۴. کدهای خطای سرویس

| HTTP Code | Status | توضیح |
|---|---|---|
| 400 | INVALID_ARGUMENT | خطا در پارامترهای ورودی |
| 470 | CoordinateParseError | مختصات جغرافیایی ارسالی معتبر نیست. |
| 480 | KeyNotFound | کلید API نامعتبر است یا در هدر ارسال نشده است. |
| 481 | LimitExceeded | تعداد فراخوانی‌ها از سهمیه‌ی تعیین‌شده عبور کرده است. |
| 482 | RateExceeded | تعداد درخواست در دقیقه از حد مجاز عبور کرده است. |
| 483 | ApiKeyTypeError | کلید استفاده‌شده با این سرویس همخوانی ندارد. |
| 484 | ApiWhiteListError | با توجه به محدودیت تعریف‌شده برای کلید، استفاده مجاز نیست. |
| 485 | ApiServiceListError | سرویس فراخوانی‌شده با سرویس‌های مجاز کلید همخوانی ندارد. |
| 500 | GenericError | خطای ناشناخته |

---

## ۵. نمونه‌ی کاربردی: ساخت منوی وابسته استان ← شهرستان

```javascript
const API_KEY = "<YOUR_API_KEY>";
const headers = { "Api-Key": API_KEY };

async function loadProvinces() {
  const res = await fetch("https://api.neshan.org/v2/region/provinces", { headers });
  return res.json(); // [{ id, name }, ...]
}

async function loadCities(provinceId) {
  const res = await fetch(
    `https://api.neshan.org/v2/region/provinces/${provinceId}/cities`,
    { headers }
  );
  return res.json(); // [{ id, name }, ...]
}

// استفاده
(async () => {
  const provinces = await loadProvinces();
  const lorestan = provinces.find((p) => p.name === "استان لرستان");
  const cities = await loadCities(lorestan.id);
  console.log(cities.map((c) => c.name));
})();
```

---

## ۶. نکات مهم

- شناسه‌ی استان و شهرستان را ثابت فرض نکنید؛ همیشه از خروجی سرویس بخوانید یا در سمت خود کش کنید.
- لیست استان‌ها و شهرستان‌ها به ندرت تغییر می‌کند، بنابراین کش‌کردن نتایج در سمت سرور یا کلاینت توصیه می‌شود و فراخوانی مکرر لازم نیست.
- برای نسخه‌ی با جئومتری، از اندپوینت `/geometry` استفاده کنید و پاسخ را فقط زمانی دریافت کنید که واقعاً به مرز نیاز دارید.

---

## مراجع

- [مستندات سرویس لیست استان‌ها و شهرستان‌ها](https://platform.neshan.org/docs/api/search-category/region/)
- [پنل توسعه‌دهندگان نشان](https://platform.neshan.org/panel)
- [پشتیبانی نشان](https://platform.neshan.org/panel/support/ticketing)
