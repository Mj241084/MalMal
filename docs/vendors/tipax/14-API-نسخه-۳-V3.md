## ۱۴. API نسخه ۳ (V3)

### ۱۴.۱ مشخصات کلی
- **نسخه پایدار قبلی** با ۱۰۷ اندپوینت در ۲۳ گروه.
- شامل: باکس‌لاین (Box Line)، لاکر، Webhook، تیکتینگ، تراکنش‌های مالی، سرویس‌های اکوپک.
- **مستندات:** `omtestapi.tipax.ir/docs/v3/index.html` و Swagger V3.
- **معماری:** همزمان (Synchronous).

### ۱۴.۲ احراز هویت V3
1. ثبت‌نام در `etipaxco.com/register` و ورود به `etipaxco.com/login`.
2. دریافت apiKey از پروفایل کسب‌وکار.
3. ارسال POST به `https://omapi.tipax.ir/api/OM/v3/Account/token` با `username`، `password`، `apiKey`.
4. ارسال هدر `Authorization: Bearer YOUR_ACCESS_TOKEN`.

سه روش ورود در V3: `token`، `tokenwithphonenumber`، `RefreshToken`.

### ۱۴.۳ ثبت‌نام و فعال‌سازی SSO (بدون توکن)
**مرحله ۱ — ثبت‌نام:** `POST https://omapi.tipax.ir/api/OM/v3/Account/SSORegister`
```json
{
  "firstName": "string",
  "lastName": "string",
  "phoneNumber": "string",
  "nationalId": "string",
  "password": "string",
  "email": "string"
}
```
پاسخ: `{ "approveId": 0 }`

**مرحله ۲ — تأیید:** `POST https://omapi.tipax.ir/api/OM/v3/Account/SSOValidateUser`
```json
{
  "code": 0,
  "approveId": 0
}
```
- `code` همان عددی است که به شماره تماس ثبت‌شده ارسال شده است.
- `approveId` از پاسخ مرحله قبل است.

### ۱۴.۴ گروه‌های V3 (۲۳ گروه)

| گروه | تعداد | کاربرد |
|---|---|---|
| Account | ۵ | ورود، توکن، SSO |
| Customers | ۲۰ | مشتری، اعتبار، شعب، محصولات (Fulfillment) |
| ActualCustomers | ۱ | ویرایش مشتری حقیقی |
| Addresses | ۶ | آدرس، دفترچه آدرس، پلیگون نمایندگی |
| Orders | ۱۶ | روش‌های ثبت سفارش |
| Booking (باکس‌لاین) | ۵ | ثبت، جستجو، تاریخ‌های کاری، ابطال، ویرایش |
| Parcels | ۹ | مرسوله‌ها، ابطال، مبلغ، لیست آماده جمع‌آوری |
| ParcelBooks | ۲ | بسته‌های تعریف‌شده مشتری |
| ParcelStatus | ۲ | وضعیت و رویداد |
| ParcelType | ۲ | انواع مرسوله (نسخه‌های قدیم) |
| Pricing | ۷ | محاسبه هزینه برای همه سرویس‌ها |
| PaymentType | ۲ | انواع پرداخت |
| PackingPrices | ۱ | بسته‌بندی‌ها |
| PackContentRates | ۱ | محتوای بسته |
| Tracking | ۶ | پیگیری مرسوله |
| Locker | ۲ | کیوسک و بانچ |
| CustomerWebhook | ۴ | مدیریت کال‌بک |
| CustomerWebhookHistory | ۲ | تاریخچه Webhook |
| Financial | ۳ | تراکنش‌ها |
| Ticketing | ۶ | تیکت و پاسخ |
| TimeTable | ۱ | برنامه روزانه |
| Cities | ۳ | شهرها |
| States | ۱ | استان‌ها |

### ۱۴.۵ روش‌های ثبت سفارش در V3 (۱۶ روش)
- `POST /api/OM/v3/Orders` — ثبت سفارش
- `POST /api/OM/v3/Orders/OrderForAnotherCustomer` — ثبت سفارش توسط مشتری برای مشتری دیگر
- `POST /api/OM/v3/Orders/GroupOrder` — ثبت سفارش گروهی (اکسل)
- `POST /api/OM/v3/Orders/WithPreDefinedAddresses` — با آدرس‌های از پیش تعریف‌شده
- `POST /api/OM/v3/Orders/WithPreDefinedOrigin` — با مبدأ از پیش تعریف‌شده
- `POST /api/OM/v3/Orders/PluginOrder` — از طریق پلاگین
- `POST /api/OM/v3/Orders/WithCoordinates` — با مختصات جغرافیایی
- `POST /api/OM/v3/Orders/WithDiscount` — با کد تخفیف
- `GET /api/OM/v3/Orders/GetOrderAmountByOrderId/{orderId}` — مبلغ سفارش
- `POST /api/OM/v3/Orders/GetSumTotalAmountByOrderIds` — جمع هزینه سفارش‌ها
- `POST /api/OM/v3/Orders/MyTipaxOrder` — ثبت سفارش مای‌تیپاکس
- `POST /api/OM/v3/Orders/CancelOrder/{orderId}` — ابطال سفارش
- `POST /api/OM/v3/Orders/PreOrder` — ثبت پیش‌سفارش (جدید)
- `POST /api/OM/v3/Orders/CancelOrderByCode/{secondaryTraceCode}` — ابطال با کد ثانویه
- `POST /api/OM/v3/Orders/QueueOrder` — ثبت سفارش در صف (جدید)
- `POST /api/OM/v3/Orders/BulkQueueOrder` — ثبت گروهی در صف

### ۱۴.۶ نمونه سفارش V3 با WithCoordinates
```json
{
  "latitude": "36.5461926",
  "longitude": "52.6783361",
  "no": "string",
  "packages": [
    {
      "destination": {
        "cityId": 1262,
        "fullAddress": "شهرک تست خیابان تست کوچه تست",
        "floor": "2",
        "unit": "45",
        "postalCode": "1234567891",
        "latitude": "35.71957113",
        "longitude": "51.37508023",
        "no": "3",
        "description": "توضیح تست",
        "beneficiary": {
          "phone": "093518880888",
          "fullName": "تست تستی",
          "mobile": "093518880888"
        }
      },
      "isUnsual": false,
      "weight": 4,
      "packageValue": 450000000,
      "length": 35,
      "width": 45,
      "height": 55,
      "packingId": 11,
      "packageContentId": 9,
      "packType": 20,
      "description": "Test",
      "serviceId": 4,
      "enableLabelPrivacy": true,
      "paymentType": 20,
      "pickupType": 20,
      "distributionType": 20,
      "cod": 0,
      "cashAmount": 0,
      "customParcelTitle": "TEST-SHENASE"
    }
  ],
  "traceCode": "TEST547698",
  "secondaryTraceCode": "TS3456678",
  "discountCode": ""
}
```

### ۱۴.۷ Fulfillment (انبار تیپاکس) در V3
**مرحله ۱ — دریافت محصولات مشتری:** `POST https://omapi.tipax.ir/api/OM/v3/Customers/GetTotalCustomerProducts` با بدنه `{}`. از پاسخ، `id` و `branchId` محصولات دریافت می‌شود.

**مرحله ۲ — ثبت سفارش Fulfillment:** `POST https://omapi.tipax.ir/api/OM/v3/Orders` با فیلد `products` در هر بسته:
```json
"products": [
  { "id": 401, "branchId": 432, "count": 1 }
]
```
| فیلد | توضیح |
|---|---|
| id | شناسه محصول (از GetTotalCustomerProducts) |
| branchId | شناسه شعبه مرتبط با محصول |
| count | تعداد محصول مورد نیاز |

مقادیر `id` و `branchId` در مثال نمونه هستند و در پیاده‌سازی واقعی باید از پاسخ سرویس دریافت شوند.

### ۱۴.۸ باکس‌لاین در V3 (LTL)
- `POST /api/OM/v3/Booking/Register` — ثبت سفارش باکس‌لاین
- `POST /api/OM/v3/Booking/Search` — جستجوی سفارش‌ها با فیلتر اختیاری
- `POST /api/OM/v3/Booking/GetWorkingDates` — تاریخ‌های کاری (ساعات مجاز جمع‌آوری یا تحویل) بر اساس آدرس، تاریخ شروع و مهلت
- `POST /api/OM/v3/Booking/Cancel` — ابطال توسط مشتری
- `POST /api/OM/v3/Booking/UpdateByCustomer/{bookingId}` — ویرایش توسط مشتری

نمونه ثبت:
```json
{
  "pickupDate": "1405/05/10",
  "deadlineDays": 2,
  "bookingParcels": [
    {
      "parcelValue": "500000000",
      "weight": "30",
      "description": "Refrigerator sample",
      "packagingTypeId": 509,
      "senderClientId": 5877661,
      "receiverClientId": 71012065,
      "senderAddressesId": 86035238,
      "receiverAddressesId": 85581549,
      "paymentTypeId": 10,
      "pickupTypeId": 10,
      "deliveryTypeId": 10,
      "packagingContentId": 11
    }
  ],
  "WorkingDates": [
    { "date": "1405/05/10", "start": "09:00", "end": "15:00", "Type": "Origin" },
    { "date": "1405/05/11", "start": "09:00", "end": "15:00", "Type": "Origin" },
    { "date": "1405/05/10", "start": "02:40", "end": "12:00", "Type": "Destination" },
    { "date": "1405/05/11", "start": "02:40", "end": "12:00", "Type": "Destination" }
  ]
}
```

### ۱۴.۹ گروه‌های اصلی V3 با اندپوینت‌ها

**Customers:**
- `GET /api/OM/v3/Customers` — مشتری جاری
- `GET /api/OM/v3/Customers/Credit` — اعتبار
- `GET /api/OM/v3/Customers/Wallet` — کیف پول
- `POST /api/OM/v3/Customers/RechargeWallet` — شارژ کیف پول
- `GET /api/OM/v3/Customers/Remain` — مانده حساب
- `GET /api/OM/v3/Customers/mycustomers/{id}` — مشتری من
- `GET /api/OM/v3/Customers/myproducts` — لیست محصولات من
- `GET /api/OM/v3/Customers/mycustomers` — مشتریان من
- `GET /api/OM/v3/Customers/mySubstations` — شعب من
- `POST /api/OM/v3/Customers/CreateMySubstation` — افزودن شعبه
- `POST /api/OM/v3/Customers/DisableMySubstation` — غیرفعال کردن شعبه
- `POST /api/OM/v3/Customers/EnableMySubstation` — فعال کردن شعبه
- `GET /api/OM/v3/Customers/{customerId}/GetCustomerCreatedByCustomer` — مشتریان ایجادشده توسط مشتری
- `GET /api/OM/v3/Customers/{substationId}/GetCustomersOfSubstation` — مشتریان شعبه
- `POST /api/OM/v3/Customers/RegisterForPanel` — ثبت‌نام برای پنل
- `GET /api/OM/v3/Customers/GetMyCustomers/{substationCode}` — مشتری‌های شعبه
- `POST /api/OM/v3/Customers/ApprovePhoneNumber` — تأیید موبایل
- `POST /api/OM/v3/Customers/ValidateUserForPanel` — اعتبارسنجی پنل
- `POST /api/OM/v3/Customers/ApprovePhoneNumberCode` — تأیید کد
- `POST /api/OM/v3/Customers/ResendSMSForApprovePhoneNumber` — ارسال مجدد
- `POST /api/OM/v3/Customers/GetTotalCustomerProducts` — محصولات مشتری (Fulfillment)

**Addresses:**
- `POST /api/OM/v3/Addresses` — افزودن آدرس کسب‌وکار
- `GET /api/OM/v3/Addresses` — لیست آدرس‌ها
- `POST /api/OM/v3/Addresses/Book` — افزودن به دفترچه
- `GET /api/OM/v3/Addresses/Book` — دفترچه آدرس
- `GET /api/OM/v3/Addresses/{id}` — آدرس با شناسه
- `GET /api/OM/v3/Addresses/GetBranchPolygonByPoint` — نزدیک‌ترین پلیگون نمایندگی بر اساس طول و عرض

**Parcels:**
- `GET /api/OM/v3/Parcels/GetByOrderId/{orderId}`
- `GET /api/OM/v3/Parcels/PaymentType/{trackingCode}`
- `PUT /api/OM/v3/Parcels/Cancel/{trackingCode}`
- `GET /api/OM/v3/Parcels/GetAmountByTrackingCode/{trackingCode}`
- `POST /api/OM/v3/Parcels/GetSumTotalAmountByTrackingCodes`
- `GET /api/OM/v3/Parcels/GetAmountByContractCode/{contractCode}`
- `GET /api/OM/v3/Parcels/GetPriceDetailByTrackingCode/{trackingCode}`
- `GET /api/OM/v3/Parcels/GetPriceDetailByContractCode/{contractCode}`
- `POST /api/OM/v3/Parcels/Search` — مرسوله‌های در دست جمع‌آوری

**Pricing:**
- `POST /api/OM/v3/Pricing` — دریافت قیمت
- `POST /api/OM/v3/Pricing/WithAddressId`
- `POST /api/OM/v3/Pricing/WithOriginAddressId`
- `POST /api/OM/v3/Pricing/GetForAllServices` — قیمت همه سرویس‌ها
- `POST /api/OM/v3/Pricing/WithAddressIdForAllServices`
- `POST /api/OM/v3/Pricing/WithOriginAddressIdForAllServices`
- `POST /api/OM/v3/Pricing/GetServicesBetweenCities`

نمونه ورودی Pricing:
```json
{
  "packageInputs": [
    {
      "origin": { "cityId": 1262 },
      "destination": { "cityId": 1262 },
      "weight": 2,
      "packageValue": 2222222,
      "length": 2,
      "width": 2,
      "height": 2,
      "packingId": 7,
      "packageContentId": 520,
      "packType": 20,
      "paymentType": 20,
      "pickupType": 0,
      "distributionType": 10,
      "serviceId": 7
    }
  ]
}
```

**Tracking:**
- `GET /api/OM/v3/Tracking/BriefTracking/{trackingInput}`
- `GET /api/OM/v3/Tracking/ByContractCode/{contractCode}`
- `GET /api/OM/v3/Tracking/{orderId}`
- `POST /api/OM/v3/Tracking/ByTrackingCode`
- `POST /api/OM/v3/Tracking/{traceCode}`
- `POST /api/OM/v3/Tracking/BySecondaryTraceCode/{secondaryTraceCode}`

**CustomerWebhook:**
- `GET /api/OM/v3/CustomerWebhook` — همه وب‌هوک‌ها
- `POST /api/OM/v3/CustomerWebhook` — ایجاد
- `PUT /api/OM/v3/CustomerWebhook` — به‌روزرسانی با شناسه یکتا
- `PUT /api/OM/v3/CustomerWebhook/SoftDelete/{id}` — حذف نرم

**CustomerWebhookHistory:**
- `POST /api/OM/v3/CustomerWebhookHistory/GetAll`
- `GET /api/OM/v3/CustomerWebhookHistory/Recent/{customerId}`

**Financial:**
- `GET /api/OM/v3/Financial/GetDocuments` — ۱۰۰ تراکنش آخر
- `GET /api/OM/v3/Financial/GetDocumentsByYear`
- `GET /api/OM/v3/Financial/GetDocumentById`

**Ticketing:**
- `GET /api/OM/v3/Ticketing` — لیست
- `POST /api/OM/v3/Ticketing` — ثبت
- `POST /api/OM/v3/Ticketing/Answer` — پاسخ
- `GET /api/OM/v3/Ticketing/{id}`
- `GET /api/OM/v3/Ticketing/GetByOrderId/{orderId}`
- `GET /api/OM/v3/Ticketing/GetDepartments`

**Locker (V3):**
- `POST /api/v3/Locker/SearchKiosks`
- `POST /api/v3/Locker/SearchBunches`

**TimeTable:**
- `GET /api/v3/TimeTable/GetNextDayTimeTableSchedule` — برنامه روز بعد

**Cities / States:**
- `GET /api/OM/v3/Cities`
- `GET /api/OM/v3/Cities/plusstate`
- `GET /api/OM/v3/Cities/BranchCities`
- `GET /api/OM/v3/States`

**PaymentType / PackingPrices / PackContentRates / ParcelType / ParcelStatus / ParcelBooks:** مسیرهای مشابه V4 با پیشوند `/api/OM/v3/`.

**customers/actual:** `PUT /api/OM/v3/customers/actual`

### ۱۴.۱۰ تفاوت V3 و V4
| موضوع | V3 | V4 |
|---|---|---|
| معماری | همزمان | رویدادمحور و صف‌محور |
| نتیجه سفارش | بلافاصله در پاسخ | از طریق Callback |
| Callback | اختیاری | الزامی |
| Retry | ندارد | دارد |
| مناسب برای | حجم متوسط | حجم بالا و Webhook |

### ۱۴.۱۱ مرسوله‌ها و نوع‌های سرویس در V3
- serviceId: ۱ ارسال زمینی همان‌روز؛ ۲ زمینی یک‌روزه؛ ۳ زمینی دو‌روزه؛ ۵ اکسپرس ویژه بین‌شهری؛ ۶ بین‌الملل؛ ۷ اکسپرس درون‌شهری (و نسخه‌های دیگر طبق لیست سرویس‌ها).
- paymentType در V3 شامل ۱۰، ۲۰، ۳۰، ۴۰، ۵۰، ۶۰، ۸۰، ۹۰، ۱۰۰ و ۱۱۰ است (جدول ۱۳.۹ و جدول V3 که ۶۰ و ۹۰ را هم دارد).
- pickupType: ۱۰ محل مشتری، ۲۰ نمایندگی.
- distributionType: ۱۰ محل مشتری، ۲۰ نمایندگی.
