# یادداشت تطبیق زرین‌پال برای P3

نتیجه‌ی بررسی `[VERIFY]`های بریف `phase-03-checkout-V2.md` پیش از پیاده‌سازی. منبع: `zarinpal-complete-guide.md` در همین پوشه و مستندات رسمی زرین‌پال
([راهنمای اتصال به درگاه](https://next.zarinpal.com/paymentGateway/guide/)، [Sandbox](https://next.zarinpal.com/paymentGateway/sandbox.html)).

## ۱. آدرس StartPay
- مستندات رسمی: `authority` را در انتهای «آدرس درگاه پرداخت» بگذارید و کاربر را به آن ریدایرکت کنید.
- سندباکس رسمی `https://sandbox.zarinpal.com/pg/StartPay/<authority>` را نام می‌برد؛ نسخه‌ی اصلی هم `https://www.zarinpal.com/pg/StartPay/<authority>` و هم `https://payment.zarinpal.com/pg/StartPay/<authority>` را پاسخ می‌دهد.
- **پیاده‌سازی:** همان میزبان API استفاده می‌شود: `https://payment.zarinpal.com/pg/StartPay/<authority>` در production و `https://sandbox.zarinpal.com/pg/StartPay/<authority>` در سندباکس (`ZARINPAL_SANDBOX=true`). این با آدرس‌های «تغییر `payment.zarinpal.com` به `sandbox.zarinpal.com`» در بخش ۶ سند هم‌خوان است.

## ۲. واحد پول
- هر دو `IRR` و `IRT` پذیرفته می‌شود. کد پروژه تومان ذخیره می‌کند و فقط در adapter درخواست/verify را با `amount * 10` و `currency="IRR"` می‌فرستد (D14). verify هم همان مبلغ ریالی را می‌فرستد.

## ۳. حداقل/حداکثر مبلغ
- حداکثر `100,000,000` تومان (کد `-41`) → `PaymentGateway.max_amount`.
- حداقل: مستندات بین ۱٬۰۰۰ و ۱۰٬۰۰۰ ریال اختلاف دارند (کد `-9` برای مبلغ نامعتبر). ردیف seed حداقل `1,000` **تومان** (۱۰٬۰۰۰ ریال) گرفته تا از هر دو عدد محافظه‌کارانه‌تر باشد؛ مقدار در ادمین قابل تغییر است.

## ۴. Sandbox و مرچنت‌کد
- در سندباکس هر UUID نسخه ۴ دلخواه پذیرفته می‌شود؛ `SANDBOX_MERCHANT_ID` ساختگی فقط وقتی `ZARINPAL_SANDBOX=true` و `ZARINPAL_MERCHANT_ID` خالی باشد استفاده می‌شود.
- `authority` سندباکس با حرف `S` شروع می‌شود؛ تست‌های خودکار همین را فرض می‌کنند.
- کد `101` در verify یعنی «قبلاً verify شده» و موفقیت است، نه خطا.

## ۵. موارد باز
- مرچنت‌کد واقعی هنوز نیامده (D26، غیرمسدودکننده). گذار فقط با `.env` است.
- تست انتها‌به‌انتها روی سندباکس واقعی (بخش ۶ بریف، مورد ۱۲) به شبکه و مرچنت‌کد نیاز دارد و با کاربر است.
