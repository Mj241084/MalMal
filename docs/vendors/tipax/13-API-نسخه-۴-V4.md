## ۱۳. API نسخه ۴ (V4)

### ۱۳.۱ مشخصات کلی
- **جدیدترین نسخه** معرفی‌شده.
- **تعداد اندپوینت:** ۷۶ در ۱۷ گروه؛ ۱۴۵ Schema.
- **آدرس پروداکشن:** `omapi.tipax.ir`
- **آدرس تست:** `omtestapi.tipax.ir`
- **مستندات:** Document UI V4 در `omtestapi.tipax.ir/docs/v4/index.html` و Swagger در `omtestapi.tipax.ir/swagger/index.html?urls.primaryName=V4+Docs`
- **ویژگی‌ها:** ۶ روش ثبت سفارش، Device Register، Return Order، Pickup مرسوله، Locker با جست‌وجوی lat/lon/cityId، Webhook اختصاصی.
- **معماری:** مبتنی بر رویداد (Event-Driven) و صف‌گذاری (Queue) و غیرهمزمان (Async).

### ۱۳.۲ احراز هویت
1. ثبت‌نام در `https://etipaxco.com/register` و ورود به `https://etipaxco.com/login`
2. دریافت **apiKey** از پروفایل کسب‌وکار در پنل
3. ارسال POST به `https://igtgatewayapi.tipax.ir/Token` با بدنه JSON:
```json
{
  "username": "نام کاربری پنل ای‌تیپاکس",
  "password": "رمز عبور پنل ای‌تیپاکس",
  "grant_type": "password"
}
```
(مقدار grant_type بدون تغییر بماند.)
4. ارسال هدر `Authorization: Bearer YOUR_ACCESS_TOKEN` در تمام درخواست‌ها.
5. تمدید توکن: `POST /api/OM/v4/Account/RefreshToken` با بدنه `{ "token": "...", "refreshToken": "..." }`.

### ۱۳.۳ Webhook (الزامی برای ثبت سفارش)
ترتیب کار:
1. **ابتدا** آدرس وب‌هوک را ثبت کنید:
   `POST https://omapi.tipax.ir/api/OM/v3/CustomerWebhook`
```json
{
  "url": "https://yourdomain.com/api/tipax/webhook",
  "headers": [
    { "key": "Authorization", "value": "Bearer YOUR_TOKEN" }
  ],
  "id": 0
}
```
2. سپس همان آدرس را در پیلود ثبت سفارش V4 در دو فیلد قرار دهید:
```json
{
  "SuccessCallbackUrl": "https://yourdomain.com/api/tipax/webhook",
  "FailureCallbackUrl": "https://yourdomain.com/api/tipax/webhook"
}
```

**نکات مهم:**
- ثبت Webhook پیش از ثبت سفارش الزامی است.
- هر دو پارامتر SuccessCallbackUrl و FailureCallbackUrl باید مقداردهی شوند.
- نام پارامترها دقیقاً با همین حروف بزرگ و کوچک ارسال شود.
- آدرس باید عمومی و از سمت سرور تیپاکس قابل دسترسی باشد؛ `localhost` یا `local.host` معتبر نیست.
- نتیجه پردازش موفق یا ناموفق سفارش از طریق Callback به سامانه شما ارسال می‌شود.
- وب‌هوک امکان تلاش مجدد (Retry) و به‌روزرسانی آنی وضعیت را می‌دهد.

### ۱۳.۴ ثبت سفارش در V4 — نمونه کامل ساختار
`POST /api/OM/v4/OmOrder` (ثبت سفارش عمومی)

ساختار اصلی:
```json
{
  "packages": [
    {
      "origin": {
        "cityId": 1262,
        "fullAddress": "آدرس فرستنده پلاک ۲۳",
        "latitude": 51.8302611199163,
        "longitude": 35.4438412913701,
        "beneficiary": {
          "fullName": "امیر",
          "mobile": "09121234567",
          "floor": "2",
          "unit": "4",
          "postalCode": "1234567891",
          "description": "test"
        }
      },
      "destination": {
        "cityId": 1293,
        "fullAddress": "آدرس گیرنده پلاک ۴۴۴",
        "latitude": 51.78712623,
        "longitude": 35.42576206,
        "floor": "12",
        "unit": "32",
        "postalCode": "8529637410",
        "beneficiary": {
          "fullName": "امیرعلی",
          "mobile": "09331234567"
        }
      },
      "customParcelTitle": "TESTL",
      "weight": 1,
      "packageValue": 10000000,
      "length": 40,
      "width": 30,
      "height": 5,
      "packingId": 522,
      "packageContentId": 36,
      "packType": 70,
      "paymentType": 20,
      "pickupType": 20,
      "distributionType": 10,
      "serviceId": 7,
      "cod": 0,
      "cashAmount": 0
    }
  ],
  "traceCode": "MP11101492",
  "secondaryTraceCode": "MP85214798910",
  "discountCode": null,
  "successCallbackUrl": "",
  "failureCallbackUrl": ""
}
```

### ۱۳.۵ روش‌های ثبت سفارش در V4 (۶ روش)

| روش | مسیر | نکته |
|---|---|---|
| ثبت عمومی | `POST /api/OM/v4/OmOrder` | آدرس مبدأ و مقصد کامل |
| با آدرس از پیش ساخته‌شده | `POST /api/OM/v4/OmOrder/RegisterOrderWithAddress` | `originId` و `destinationId` از دفترچه آدرس؛ گیرنده با `receiver` |
| با مبدأ از پیش تعریف‌شده | `POST /api/OM/v4/OmOrder/WithPreDefinedOrigin` | `originId` مبدأ؛ مقصد کامل |
| با آدرس مشتری (Client) | `POST /api/OM/v4/OmOrder/WithClientAndAddress` | `senderClientId`، `receiverClientId`، `senderAddressId`، `receiverAddressId` |
| از دستگاه (Device) | `POST /api/OM/v4/OmOrder/DeviceRegisterOrder` | ثبت از دستگاه با `creatorBranchId` |
| مرجوعی (Return) | `POST /api/OM/v4/OmOrder/ReturnRegisterOrder` | `OmV4ReturnOrderRegister` |

### ۱۳.۶ فیلدهای مهم سفارش
- **packages[]:** هر بسته یک آیتم.
- **origin / destination:** cityId، fullAddress، latitude، longitude، beneficiary (fullName، mobile، floor، unit، postalCode، description)، postalCode.
- **weight:** وزن به کیلوگرم.
- **packageValue:** ارزش بسته به ریال (برای جبران خسارت).
- **length / width / height:** ابعاد به سانتی‌متر.
- **packingId:** شناسه بسته‌بندی (اختیاری؛ در غیاب آن، بسته بدون بسته‌بندی در نظر گرفته می‌شود).
- **packageContentId:** نوع محتوا (عمومی، شکستنی و...).
- **packType:** نوع بسته‌بندی. **۱۰:** پاکت، **۲۰:** بسته، **۵۰:** مینی‌پک (در نمونه‌ها **۷۰** نیز دیده می‌شود که در مستندات توضیح داده نشده است).
- **serviceId:** نوع سرویس (بخش ۱۳.۸).
- **paymentType:** نوع پرداخت (بخش ۱۳.۹).
- **pickupType:** نوع جمع‌آوری. **۱۰:** از پلاک مشتری، **۲۰:** از نمایندگی.
- **distributionType:** نوع تحویل. **۱۰:** تحویل در پلاک مقصد، **۲۰:** تحویل در نمایندگی.
- **cod:** مبلغ COD به ریال.
- **cashAmount:** مبلغ نقدی (در روش‌های خاص).
- **customParcelTitle:** این مقدار شناسه فاکتور را تعیین می‌کند و در گزارش اکسل در ستون شناسه فاکتور نمایش داده می‌شود.
- **traceCode / secondaryTraceCode:** کد رهگیری اختصاصی مشتری.
- **discountCode:** کد تخفیف (اختیاری).
- **enableLabelPrivacy:** اگر true باشد جزئیات فرستنده و گیرنده روی لیبل چاپ می‌شود.
- **isUnusual:** آیا بسته غیراستاندارد است.
- **parcelBookId:** شناسه بسته تعریف‌شده مشتری (در صورت استفاده، ابعاد را دیگر ارسال نکنید؛ در غیر این صورت ابعاد باید با مقادیر مجاز ارسال شود).
- **description:** توضیحات.

### ۱۳.۷ قواعد ویژه ارسال و بی‌درنگ بودن
- نسخه ۴ **صف‌محور** است؛ پس از ثبت، نتیجه از طریق callback برمی‌گردد و بارکد بلافاصله در پاسخ نیست.
- اگر successCallbackUrl و failureCallbackUrl در درخواست نباشد، بارکد در سیستم ثبت نمی‌شود (هرچند در تست دیده شود).
- ورودی `Locker` و `Pickup` در بخش‌های بعدی آمده است.

### ۱۳.۸ serviceId (نوع سرویس)
| مقدار | سرویس |
|---|---|
| ۱ | ارسال زمینی همان‌روز |
| ۲ | ارسال زمینی یک‌روزه |
| ۳ | ارسال زمینی دو‌روزه |
| ۴ | ارسال زمینی سه‌روزه |
| ۵ | اکسپرس ویژه بین‌شهری |
| ۶ | بین‌الملل |
| ۷ | اکسپرس درون‌شهری |
| ۱۲ | (در نمونه همان‌روز ذکر شده؛ در مستندات توضیح داده نشده) |

**قرارداد اکسپرس:** مقادیر ۱، ۲، ۳، ۴، ۵ و ۷ نوع قرارداد نهایی را «اکسپرس» تعیین می‌کنند.

### ۱۳.۹ paymentType (نوع پرداخت)
| مقدار | معنی |
|---|---|
| ۱۰ | سمت فرستنده / اعتباری |
| ۲۰ | سمت گیرنده / پس‌کرایه |
| ۳۰ | سمت گیرنده / پرداخت در محل (COD) |
| ۴۰ | سمت فرستنده / پرداخت در محل |
| ۵۰ | سمت فرستنده / پرداخت از کیف پول |
| ۸۰ | سمت فرستنده / نقدی |
| ۱۰۰ | نقدی-پس‌کرایه |
| ۱۱۰ | اعتباری-پس‌کرایه |

**قواعد مبلغ:**
- **۱۰ و ۴۰:** هزینه خدمات از اعتبار فرستنده کسر می‌شود. در ۴۰ اگر COD ارسال نشود یا کمتر از ارزش باشد، ارزش مرسوله به‌جای COD جای‌گذاری می‌شود.
- **۲۰ و ۳۰:** هزینه از گیرنده دریافت می‌شود. در ۳۰ اگر COD ارسال نشود یا کمتر از ارزش باشد، ارزش مرسوله به‌جای COD قرار می‌گیرد.
- **۸۰:** نماینده هنگام جمع‌آوری هزینه را نقداً از فرستنده دریافت می‌کند؛ باید `cashAmount` ارسال شود.
- **۱۰۰ و ۱۱۰ (پس‌کرایه):** فقط **یکی** از دو پارامتر ارسال شود و مقدار آن بیشتر از صفر باشد:
  - `payInPlaceAmount`: مبلغی که گیرنده پرداخت می‌کند
  - `cashAmount`: مبلغی که فرستنده پرداخت می‌کند
  - ارسال هر دو همزمان خطای اعتبارسنجی دارد؛ عدم ارسال هر دو نیز خطا است. پارامتر انتخاب‌نشده باید کاملاً از پیلود حذف شود (نه با مقدار صفر).

نمونه‌ها:
```json
{ "paymentType": 110, "payInPlaceAmount": 1000000 }
```
```json
{ "paymentType": 110, "cashAmount": 1000000 }
```

### ۱۳.۱۰ تیپ‌بندی جمع‌آوری و تحویل
- **pickupType:** ۱۰ = جمع‌آوری در محل مشتری؛ ۲۰ = جمع‌آوری در نمایندگی.
- **distributionType:** ۱۰ = تحویل در محل گیرنده؛ ۲۰ = تحویل در نمایندگی.

### ۱۳.۱۱ جمع‌آوری (Pickup) در V4
- `POST /api/OM/v4/Parcels/GetReadyForPickupList` — لیست مرسوله‌های آماده جمع‌آوری
- `POST /api/OM/v4/Parcels/PickupParcelWithUpdateBarcode` — ثبت جمع‌آوری مرسوله و به‌روزرسانی بارکد
- در ثبت زمان جمع‌آوری (pickupStartTime، pickupEndTime) امکان ثبت عملاً فعلاً فعال نیست.

### ۱۳.۱۲ فهرست کامل اندپوینت‌های V4 (۷۶ اندپوینت)

**۱. احراز هویت (Account) — ۱ اندپوینت**
- `POST /api/OM/v4/Account/RefreshToken` — تمدید توکن

**۲. مدیریت مشتری (Customers) — ۱۸ اندپوینت**
- `POST /api/OM/v4/Customers/GetCustomers` — دریافت لیست مشتری‌ها (جدید)
- `GET /api/OM/v4/Customers` — دریافت مشتری جاری
- `GET /api/OM/v4/Customers/Credit` — دریافت اعتبار مشتری
- `GET /api/OM/v4/Customers/Wallet` — دریافت موجودی کیف پول
- `POST /api/OM/v4/Customers/RechargeWallet` — شارژ کیف پول (بدنه: amount و frontCallBackUrl)
- `GET /api/OM/v4/Customers/Remain` — دریافت مانده حساب
- `GET /api/OM/v4/Customers/mycustomers/{id}` — دریافت مشتری من
- `GET /api/OM/v4/Customers/mycustomers` — لیست مشتریان من
- `GET /api/OM/v4/Customers/mySubstations` — لیست شعب من
- `POST /api/OM/v4/Customers/CreateMySubstation` — افزودن به لیست شعب من
- `POST /api/OM/v4/Customers/DisableMySubstation` — غیرفعال کردن شعبه من
- `POST /api/OM/v4/Customers/EnableMySubstation` — فعال کردن شعبه من
- `POST /api/OM/v4/Customers/RegisterForPanel` — ثبت‌نام برای پنل
- `GET /api/OM/v4/Customers/GetMyCustomers/{substationCode}` — لیست مشتری‌های شعبه من
- `POST /api/OM/v4/Customers/ApprovePhoneNumber` — تأیید شماره موبایل
- `POST /api/OM/v4/Customers/ValidateUserForPanel` — اعتبارسنجی کاربر پنل
- `POST /api/OM/v4/Customers/ApprovePhoneNumberCode` — تأیید کد شماره موبایل
- `POST /api/OM/v4/Customers/ResendSMSForApprovePhoneNumber` — ارسال مجدد پیامک تأیید

**۳. مدیریت آدرس (Addresses) — ۵ اندپوینت**
- `POST /api/OM/v4/Addresses` — افزودن آدرس کسب‌وکار برای مشتری جاری
- `GET /api/OM/v4/Addresses` — لیست آدرس‌های کاربر
- `POST /api/OM/v4/Addresses/Book` — افزودن آدرس به دفترچه آدرس
- `GET /api/OM/v4/Addresses/Book` — دریافت دفترچه آدرس کاربر
- `GET /api/OM/v4/Addresses/{id}` — دریافت آدرس با شناسه آدرس

**۴. ثبت سفارش (OmOrder) — ۶ اندپوینت**
- `POST /api/OM/v4/OmOrder` — ثبت سفارش
- `POST /api/OM/v4/OmOrder/RegisterOrderWithAddress` — ثبت با آدرس از پیش ساخته‌شده
- `POST /api/OM/v4/OmOrder/WithPreDefinedOrigin` — ثبت با مبدأ از پیش تعریف‌شده
- `POST /api/OM/v4/OmOrder/WithClientAndAddress` — ثبت با آدرس مبدأ و مقصد (کلاینت)
- `POST /api/OM/v4/OmOrder/DeviceRegisterOrder` — ثبت از دستگاه
- `POST /api/OM/v4/OmOrder/ReturnRegisterOrder` — ثبت مرجوعی

**۵. مرسولات (Parcels) — ۱۰ اندپوینت**
- `POST /api/OM/v4/Parcels/GetReadyForPickupList` — لیست آماده جمع‌آوری
- `POST /api/OM/v4/Parcels/PickupParcelWithUpdateBarcode` — جمع‌آوری و به‌روزرسانی بارکد
- `GET /api/OM/v4/Parcels/GetByOrderId/{orderId}` — مرسوله‌ها بر اساس شماره سفارش
- `GET /api/OM/v4/Parcels/PaymentType/{trackingCode}` — نوع پرداخت
- `PUT /api/OM/v4/Parcels/Cancel/{trackingCode}` — ابطال مرسوله
- `GET /api/OM/v4/Parcels/GetAmountByTrackingCode/{trackingCode}` — مبلغ مرسوله با کد رهگیری
- `POST /api/OM/v4/Parcels/GetSumTotalAmountByTrackingCodes` — جمع هزینه مرسوله‌ها (تومان)
- `GET /api/OM/v4/Parcels/GetAmountByContractCode/{contractCode}` — مبلغ با کد قرارداد جت
- `GET /api/OM/v4/Parcels/GetPriceDetailByTrackingCode/{trackingCode}` — جزئیات مبلغ با کد رهگیری
- `GET /api/OM/v4/Parcels/GetPriceDetailByContractCode/{contractCode}` — جزئیات مبلغ با کد قرارداد

**۶. بسته‌های مشتری (ParcelBooks) — ۲ اندپوینت**
- `GET /api/OM/v4/ParcelBooks` — لیست بسته‌های تعریف‌شده مشتری
- `POST /api/OM/v4/ParcelBooks` — افزودن بسته جدید

**۷. وضعیت مرسولات (ParcelStatus) — ۲ اندپوینت**
- `GET /api/OM/v4/ParcelStatus` — لیست وضعیت‌ها
- `GET /api/OM/v4/ParcelStatus/GetEventWithStatus` — لیست رویدادها

**۸. محاسبه هزینه (Pricing) — ۵ اندپوینت**
- `POST /api/OM/v4/Pricing` — دریافت قیمت
- `POST /api/OM/v4/Pricing/WithAddressId` — دریافت قیمت با آیدی آدرس‌های تعریف‌شده
- `POST /api/OM/v4/Pricing/WithOriginAddressId` — دریافت قیمت با آیدی آدرس مبدأ
- `POST /api/OM/v4/Pricing/GetServicesBetweenCities` — لیست سرویس‌های بین دو شهر
- `POST /api/OM/v4/Pricing/GetServicesList` — لیست سرویس‌ها (جدید)

**۹. انواع پرداخت (PaymentType) — ۲ اندپوینت**
- `POST /api/OM/v4/PaymentType/Search` — لیست انواع پرداخت
- `GET /api/OM/v4/PaymentType/Get` — پرداخت با شناسه

**۱۰. بسته‌بندی (PackingType) — ۳ اندپوینت**
- `GET /api/OM/v4/PackingType/GetPackTypes` — نوع بسته
- `GET /api/OM/v4/PackingType/GetPackingTypes` — بسته‌بندی‌ها
- `GET /api/OM/v4/PackingType/GetPackagingContents` — لیست محتوا

**۱۱. رهگیری (Tracking) — ۶ اندپوینت**
- `GET /api/OM/v4/Tracking/BriefTracking/{trackingInput}` — پیگیری مرسوله
- `GET /api/OM/v4/Tracking/ByContractCode/{contractCode}` — پیگیری با کد قرارداد جت
- `GET /api/OM/v4/Tracking/{orderId}` — پیگیری با کد سفارش
- `POST /api/OM/v4/Tracking/ByTrackingCode` — پیگیری چند مرسوله با کد رهگیری
- `POST /api/OM/v4/Tracking/{traceCode}` — پیگیری با کد رهگیری مشتری
- `POST /api/OM/v4/Tracking/BySecondaryTraceCode/{secondaryTraceCode}` — پیگیری با کد رهگیری ثانویه

**۱۲. لاکر (Locker) — ۲ اندپوینت**
- `POST /api/v4/Locker/SearchKiosks` — جست‌وجوی کیوسک‌ها بر اساس مختصات یا کد شهر و فیلتر ابعاد
- `POST /api/v4/Locker/SearchBunches` — جست‌وجوی بانچ‌ها بر اساس مختصات یا کد شهر و فیلتر ابعاد

**۱۳. مالی (Financial) — ۳ اندپوینت**
- `GET /api/OM/v4/Financial/GetDocuments` — دریافت حداکثر ۱۰۰ تراکنش آخر
- `GET /api/OM/v4/Financial/GetDocumentsByYear` — تراکنش‌ها بر اساس سال مالی
- `GET /api/OM/v4/Financial/GetDocumentById` — جزئیات تراکنش

**۱۴. تیکتینگ (Ticketing) — ۶ اندپوینت**
- `GET /api/OM/v4/Ticketing` — لیست تیکت‌ها
- `POST /api/OM/v4/Ticketing` — ثبت تیکت
- `POST /api/OM/v4/Ticketing/Answer` — ثبت پاسخ تیکت
- `GET /api/OM/v4/Ticketing/{id}` — جزئیات تیکت
- `GET /api/OM/v4/Ticketing/GetByOrderId/{orderId}` — تیکت‌های یک سفارش
- `GET /api/OM/v4/Ticketing/GetDepartments` — لیست دپارتمان‌ها

**۱۵. شهرها (Cities) — ۳ اندپوینت**
- `GET /api/OM/v4/Cities` — لیست شهرها
- `GET /api/OM/v4/Cities/plusstate` — لیست شهرها با نام استان
- `GET /api/OM/v4/Cities/BranchCities` — لیست شهرهای دارای نمایندگی فعال

**۱۶. استان‌ها (States) — ۱ اندپوینت**
- `GET /api/OM/v4/States` — لیست استان‌های ایران

**۱۷. مشتری حقیقی (ActualCustomers) — ۱ اندپوینت**
- `PUT /api/OM/v4/customers/actual` — ویرایش مشتری حقیقی

### ۱۳.۱۳ Tracking و جزئیات دست‌رشته‌ها
- برای مشاهده همه دست‌رشته‌ها و جزئیات کامل وضعیت مرسوله:
  `POST https://omapi.tipax.ir/api/v2/Tracking/GetJetTrackingDetail?trackingInput=<شماره قرارداد>` با بدنه `{}`
- به‌جای شماره نمونه، شماره قرارداد واقعی را قرار دهید.

### ۱۳.۱۴ ویرایش اطلاعات مشتری (Client)
- `PUT https://omapi.tipax.ir/api/v2/client`
- بدنه (همه فیلدها string):
```json
{
  "fullName": "string",
  "mobile": "string",
  "nationalId": "string",
  "telephonNumber": "string",
  "id": "string"
}
```
- فیلد `id` برای شناسایی مشتری الزامی است.

### ۱۳.۱۵ قیمت‌گذاری و تخفیف در پاسخ Pricing
| پارامتر | توضیح |
|---|---|
| `Discount` | درصد تخفیف |
| `DiscountAmount` | مبلغ تخفیف |
| `originalFinalPrice` | مبلغ کل قبل از اعمال تخفیف |
| `finalPrice` | مبلغ نهایی قابل پرداخت |

### ۱۳.۱۶ محدودیت نرخ (Rate Limit)
- خطای `API calls quota exceeded! maximum admitted 10 per 1s` یعنی بیش از ۱۰ درخواست در ثانیه (برای هر کلاینت یا IP).
- پاسخ معمولاً `HTTP 429` است.
- **راه‌حل:** بین هر batch حدود ۱۰۰ تا ۱۵۰ میلی‌ثانیه وقفه بگذارید؛ یا در صورت امکان چند مرسوله را در یک درخواست گروهی ارسال کنید.

### ۱۳.۱۷ شماره پلاک
- فیلد «پلاک» در ثبت آدرس حداکثر ۵ رقم عددی دارد.

### ۱۳.۱۸ فیلدهای ابعاد و پارامتر parcelTypeId
- parcelTypeId مربوط به نسخه‌های ۱ و ۲ است و در نسخه ۳ و ۴ نیازی به ارسال آن نیست.
- senderAddressAndClient و receiverAddressAndClient در صورت پر بودن origin و destination خودکار پر می‌شوند و ارسال آنها لازم نیست.

### ۱۳.۱۹ نمونه سفارش Same Day در API
برای ثبت همان‌روز، سرویس‌ها و محدودیت‌ها در بخش ۲۰ آمده است. نمونه بدنه با `serviceId: 12` در مستندات نشان داده شده است.

### ۱۳.۲۰ سوالات متداول API V4 (خلاصه)
- **چگونه توکن بگیرم؟** بخش ۱۳.۲.
- **زمان جمع‌آوری را چگونه ثبت کنم؟** پارامتر وجود دارد اما فعلاً امکان ثبت آن میسر نیست.
- **peopleAddressTypeId چیست؟** آدرس فرستنده = ۱ و آدرس گیرنده = ۲.
- **EnableLabelPrivacy چیست؟** چاپ جزئیات فرستنده و گیرنده روی لیبل.
- **parcelBookId چیست؟** شناسه بسته تعریف‌شده مشتری از `POST/GET /api/OM/v4/ParcelBooks`.
- **بارکد در تست گرفته شده اما ثبت نشده؟** نسخه ۴ صف‌محور است؛ حتماً successCallbackUrl و failureCallbackUrl ارسال شود.
- **ساختار webhook در V3 و V4 چه تفاوتی دارد؟** V3 همزمان (Synchronous) است و نتیجه بلافاصله برمی‌گردد. V4 رویدادمحور و صف‌محور است و callback الزامی است.
- **چرا webhook در V4 ضروری است؟** برای پردازش آنی حجم بالای درخواست‌ها (مثلاً ۱۰۰۰ درخواست در لحظه) و کاهش بار سرورها.
- **packingId نباشد؟** بسته بدون بسته‌بندی در نظر گرفته می‌شود.
- **حداکثر رقم پلاک؟** ۵ رقم.
- **شناسه محصولات جدید؟** `https://integrationapi.tipax.ir/api/OM/v3/Customers/myproducts` (بخش ۲۶ را ببینید).
- **محدودیت ارزش سفارش؟** ثبت سفارش بیش از ۱۰۰ میلیون تومان نیاز به هماهنگی با اکانت مدیر (منیجر) دارد.
- **عوامل هزینه؟** فاصله، نوع سرویس، نوع بسته، ارزش بیمه، وزن و ابعاد، نحوه جمع‌آوری.
- **مبلغ قرارداد (finalPrice)؟** مجموع هزینه خدمات، بسته‌بندی، مالیات بر ارزش افزوده و جبران خسارت.
- **حداکثر وزن و ارزش برای هر بسته‌بندی:**

| نوع بسته‌بندی | محدودیت وزن | سقف ارزش مرسوله (ریال) |
|---|---|---|
| حجیم و سنگین | ۳۰ تا ۱۰۰ کیلوگرم | ۳٬۰۰۰٬۰۰۰٬۰۰۰ |
| بسته (کارتن) | حداکثر ۳۰ کیلوگرم | ۱٬۰۰۰٬۰۰۰٬۰۰۰ |
| پاکت | حداکثر ۲ کیلوگرم | ۲۰٬۰۰۰٬۰۰۰ |
| مینی‌پک (فلایر) | حداکثر ۲ کیلوگرم | ۱۰۰٬۰۰۰٬۰۰۰ |

- **سرویس همان‌روز با API:** در بخش ۲۰.
