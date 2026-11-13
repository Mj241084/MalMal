# سند کامل تقویم شمسی (انتخاب‌گر تاریخ)

این سند خودکفاست و به هیچ پروژه‌ی دیگری ارجاع نمی‌دهد. دو بخش دارد:

- **سمت مرورگر:** یک فایل جاوااسکریپت بدون وابستگی (`jalali_picker.js`) که روی هر `<input>` با صفت `data-jalali-date` تقویم شمسی باز می‌کند.
- **سمت سرور (Django):** فیلد فرم، توابع تبدیل و نمایش، تگ‌های تمپلیت.

---

## ۱. چه کاری می‌کند

1. کاربر روی کادر کلیک می‌کند و یک پنجره‌ی شناور تقویم شمسی باز می‌شود.
2. تایپ دستی و paste ممنوع است. فقط انتخاب از تقویم مجاز است، پس فرمت همیشه درست است.
3. تاریخ انتخاب‌شده با ارقام فارسی و فرمت `۱۴۰۵/۰۷/۲۰` در کادر می‌نشیند.
4. رویدادهای `input` و `change` شلیک می‌شوند، پس htmx و هر اسکریپت دیگری متوجه تغییر می‌شود.
5. سرور رشته را با ارقام فارسی یا لاتین و جداکننده‌ی `/` یا `-` می‌خواند و به تاریخ میلادی (`datetime.date`) تبدیل می‌کند. در دیتابیس فقط میلادی ذخیره می‌شود.
6. دکمه‌های «امروز» و (اختیاری) «پاک‌کردن» دارد.
7. داخل `<dialog>` هم درست کار می‌کند.
8. اعتبارسنجی بازه‌ی «از ... تا ...» سمت کلاینت دارد.

**نکته‌ی اصلی طراحی:** هیچ فرمول کبیسه یا تبدیل تاریخ دستی در جاوااسکریپت نیست. همه‌ی تبدیل‌ها را `Intl.DateTimeFormat` مرورگر با تقویم داخلی `persian` انجام می‌دهد.

---

## ۲. نیازمندی‌ها

**مرورگر**
- مرورگر مدرن با `Intl` و ICU کامل (Chrome، Edge، Firefox، Safari جدید).
- ظاهر پیش‌فرض با Tailwind v4 و daisyUI v5 است. نسخه‌ی CSS مستقل در بخش ۶ هست.

**سرور**
- Django 4 یا بالاتر، با `USE_TZ = True` و `TIME_ZONE = 'Asia/Tehran'`.
- `pip install jdatetime`

---

## ۳. کد کامل `jalali_picker.js`

این فایل را در `static/js/jalali_picker.js` بگذارید و در انتهای `<body>` بارگذاری کنید. به `DOMContentLoaded` نیاز ندارد، چون همه‌ی شنونده‌ها روی `document` ثبت شده‌اند.

تنها تفاوت با نسخه‌ی عملیاتی: `ca-persian` صریحاً به locale اضافه شده تا اگر locale پیش‌فرض محیط میلادی بود، تقویم اشتباه نشود.

```javascript
(function () {
  var FA = '۰۱۲۳۴۵۶۷۸۹', DAY = 86400000;
  var MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
  var WEEK = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];   // شنبه = ستون اول

  // قلب سیستم: تبدیل میلادی ← شمسی با Intl (ارقام لاتین، منطقه‌ی زمانی UTC)
  var fmt = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric', month: 'numeric', day: 'numeric', timeZone: 'UTC'
  });

  var pop = null;                 // خود پنجره‌ی تقویم (یک نمونه برای کل صفحه)
  var current = null;             // input ای که الان تقویمش باز است
  var view = { y: 0, m: 0 };      // سال و ماهی که در تقویم دیده می‌شود

  // ---------- ابزارهای کوچک ----------
  function fa(n) { return String(n).replace(/\d/g, function (d) { return FA[d]; }); }
  function en(s) {
    return String(s || '')
      .replace(/[۰-۹]/g, function (d) { return FA.indexOf(d); })
      .replace(/[٠-٩]/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(d); });
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function pad(n) { return n < 10 ? '0' + n : String(n); }

  // ---------- محاسبات تاریخ ----------
  // ms (میلادی، UTC) ← {y, m, d} شمسی
  function toJ(ms) {
    var o = {};
    fmt.formatToParts(new Date(ms)).forEach(function (p) { o[p.type] = parseInt(p.value, 10); });
    return { y: o.year, m: o.month, d: o.day };
  }
  // مقایسه‌ی تاریخ شمسی a با (y, m, d): منفی = a زودتر، صفر = برابر، مثبت = a دیرتر
  function cmp(a, y, m, d) { return a.y !== y ? a.y - y : a.m !== m ? a.m - m : a.d - d; }

  // ms روز اول ماه شمسی (y, m) ساعت ۱۲ UTC
  function firstOfMonth(y, m) {
    // تخمین: نوروز ≈ ۲۱ مارس سال y+621؛ ۶ ماه اول ۳۱ روزه، ۵ ماه بعد ۳۰ روزه
    var off = m <= 7 ? 31 * (m - 1) : 186 + 30 * (m - 7);
    var ms = Date.UTC(y + 621, 2, 21, 12) + off * DAY;
    // اصلاح: اگر تخمین یک روز جلو یا عقب بود، روز به روز جابه‌جا می‌شود تا دقیقاً به (y, m, 1) برسد
    for (var i = 0; i < 12; i++) {
      var c = cmp(toJ(ms), y, m, 1);
      if (c === 0) return ms;
      ms += c > 0 ? -DAY : DAY;
    }
    return ms;
  }
  // اطلاعات یک ماه: ms شروع، تعداد روز، تعداد خانه‌ی خالی قبل از روز اول
  function monthInfo(y, m) {
    var start = firstOfMonth(y, m), n = 0;
    while (n < 31 && toJ(start + n * DAY).m === m) n++;     // طول ماه را از خود Intl می‌شمارد
    // getUTCDay: یکشنبه=۰ ... شنبه=۶ ← می‌خواهیم شنبه=۰
    return { start: start, days: n, lead: (new Date(start).getUTCDay() + 1) % 7 };
  }
  // «امروز» شمسی طبق ساعت دستگاه کاربر (نه ساعت تهران)
  function todayJ() {
    var n = new Date();
    return toJ(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate(), 12));
  }
  // «۱۴۰۵/۰۷/۲۰» یا «1405-7-20» یا هر جداکننده‌ی غیررقم ← {y, m, d} یا null
  function parse(v) {
    var m = en(v).match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/);
    return m ? { y: +m[1], m: +m[2], d: +m[3] } : null;
  }

  // ---------- انتخاب و بستن ----------
  function pick(y, m, d) {
    current.value = fa(y) + '/' + fa(pad(m)) + '/' + fa(pad(d));
    current.dispatchEvent(new Event('input', { bubbles: true }));
    current.dispatchEvent(new Event('change', { bubbles: true }));
    close();
  }
  function close() { if (pop) pop.classList.add('hidden'); current = null; }

  // ---------- رسم تقویم ----------
  function render() {
    var info = monthInfo(view.y, view.m), sel = parse(current.value), today = todayJ();
    pop.textContent = '';

    // سربرگ: قبل | ماه | سال | بعد
    var head = el('div', 'flex items-center gap-1 mb-2');
    var prev = el('button', 'btn btn-ghost btn-xs', 'قبل ›'); prev.type = 'button';
    var next = el('button', 'btn btn-ghost btn-xs', '‹ بعد'); next.type = 'button';
    var ms = el('select', 'select select-xs flex-1 min-w-0');
    var ys = el('select', 'select select-xs w-20');
    MONTHS.forEach(function (n, i) {
      var o = el('option', null, n); o.value = i + 1;
      if (i + 1 === view.m) o.selected = true;
      ms.appendChild(o);
    });
    for (var y = view.y - 10; y <= view.y + 10; y++) {
      var o = el('option', null, fa(y)); o.value = y;
      if (y === view.y) o.selected = true;
      ys.appendChild(o);
    }
    function go(dm) {
      view.m += dm;
      if (view.m > 12) { view.m = 1; view.y++; }
      if (view.m < 1) { view.m = 12; view.y--; }
      render();
    }
    prev.addEventListener('click', function () { go(-1); });
    next.addEventListener('click', function () { go(1); });
    ms.addEventListener('change', function () { view.m = +ms.value; render(); });
    ys.addEventListener('change', function () { view.y = +ys.value; render(); });
    [prev, ms, ys, next].forEach(function (n) { head.appendChild(n); });
    pop.appendChild(head);

    // شبکه‌ی روزها
    var grid = el('div', 'grid grid-cols-7 gap-1 text-center');
    WEEK.forEach(function (w) { grid.appendChild(el('span', 'text-xs fb-muted py-1', w)); });
    for (var i = 0; i < info.lead; i++) grid.appendChild(el('span'));
    for (var d = 1; d <= info.days; d++) {
      var isSel = sel && sel.y === view.y && sel.m === view.m && sel.d === d;
      var isToday = today.y === view.y && today.m === view.m && today.d === d;
      var b = el('button',
        'btn btn-xs font-technical ' + (isSel ? 'btn-primary' : 'btn-ghost') +
        (isToday && !isSel ? ' border border-primary' : ''), fa(d));
      b.type = 'button';
      (function (day) { b.addEventListener('click', function () { pick(view.y, view.m, day); }); })(d);
      grid.appendChild(b);
    }
    pop.appendChild(grid);

    // پایین: امروز و (اختیاری) پاک‌کردن
    var foot = el('div', 'flex justify-between mt-2');
    var t = el('button', 'btn btn-ghost btn-xs', 'امروز'); t.type = 'button';
    t.addEventListener('click', function () { pick(today.y, today.m, today.d); });
    foot.appendChild(t);
    if (current.hasAttribute('data-clearable')) {
      var c = el('button', 'btn btn-ghost btn-xs', 'پاک‌کردن'); c.type = 'button';
      c.addEventListener('click', function () {
        current.value = '';
        current.dispatchEvent(new Event('change', { bubbles: true }));
        close();
      });
      foot.appendChild(c);
    }
    pop.appendChild(foot);
  }

  // ---------- باز کردن ----------
  function open(input) {
    if (input.disabled || current === input) return;
    if (!pop) {
      pop = el('div', 'jalali-popup absolute z-50 bg-base-100 border border-base-300 rounded-box shadow-lg p-3 w-72 hidden');
      pop.dir = 'rtl';
      // عمداً mousedown.preventDefault() گذاشته نشده؛ روی select سال و ماه
      // مرورگر لیست کشویی را باز نمی‌کند (باگ شناخته‌شده).
      pop.addEventListener('click', function (e) { e.stopPropagation(); });   // رسم دوباره‌ی دکمه‌ها را از DOM برمی‌دارد؛ نباید «کلیک بیرون» حساب شود
      document.body.appendChild(pop);
    }
    current = input;
    var s = parse(input.value) || todayJ();
    view = { y: s.y, m: s.m };
    render();

    // داخل dialog پنجره باید داخل همان dialog باشد، وگرنه در top-layer زیر مودال می‌ماند
    var host = input.closest('dialog') || document.body, inDialog = host !== document.body;
    if (pop.parentNode !== host) host.appendChild(pop);

    var r = input.getBoundingClientRect(), w = document.documentElement.clientWidth;
    var left = Math.min(Math.max(8, r.right - 288), w - 296);   // لبه‌ی راست پنجره = لبه‌ی راست input
    pop.style.left = (left + (inDialog ? 0 : window.scrollX)) + 'px';
    pop.style.top = (r.bottom + (inDialog ? 0 : window.scrollY) + 4) + 'px';
    pop.classList.remove('hidden');
    if (inDialog && r.bottom + 4 + pop.offsetHeight > window.innerHeight && r.top - 4 - pop.offsetHeight > 0) {
      pop.style.top = (r.top - 4 - pop.offsetHeight) + 'px';    // جا نبود ← بالای کادر
    }
  }

  // ---------- شنونده‌های سراسری (تفویضی) ----------
  document.addEventListener('focusin', function (e) {
    if (e.target.matches && e.target.matches('[data-jalali-date]')) open(e.target);
  });
  document.addEventListener('click', function (e) {
    if (e.target.matches && e.target.matches('[data-jalali-date]')) open(e.target); else close();
  });
  document.addEventListener('keydown', function (e) {
    if (!e.target.matches || !e.target.matches('[data-jalali-date]')) return;
    if (e.key === 'Tab' || e.key === 'Escape') { close(); return; }
    // تایپ دستی ممنوع: هر کلید تک‌نویسه، Backspace و Delete
    if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Delete') e.preventDefault();
  });
  document.addEventListener('paste', function (e) {
    if (e.target.matches && e.target.matches('[data-jalali-date]')) e.preventDefault();
  });

  // بسته‌شدن dialog (Esc، بک‌دراپ یا تعویض htmx) پنجره‌ی باز را هم می‌بندد.
  // رویداد close حباب نمی‌کند، پس در فاز capture گوش می‌دهیم.
  document.addEventListener('close', function (e) {
    if (e.target && e.target.tagName === 'DIALOG') close();
  }, true);

  // اعتبارسنجی بازه: تاریخ شروع نباید بعد از پایان باشد.
  // در فاز capture ثبت شده تا قبل از شنونده‌ی htmx روی فرم اجرا شود و ارسال را متوقف کند.
  document.addEventListener('submit', function (e) {
    var form = e.target, wrongAny = false;
    if (!form || !form.querySelectorAll) return;
    form.querySelectorAll('[data-date-range]').forEach(function (box) {
      var inputs = box.querySelectorAll('[data-jalali-date]');
      if (inputs.length !== 2) return;
      var a = en(inputs[0].value).replace(/\D/g, ''), b = en(inputs[1].value).replace(/\D/g, '');
      var wrong = !!(a && b && a > b);          // مقایسه‌ی رشته‌ی YYYYMMDD
      var msg = box.querySelector('[data-date-range-error]');
      if (msg) msg.classList.toggle('hidden', !wrong);
      if (wrong) wrongAny = true;
    });
    if (wrongAny) { e.preventDefault(); e.stopImmediatePropagation(); }
  }, true);
})();
```

---

## ۴. شرح مو به مو

### ۴.۱ تبدیل تاریخ: `toJ`
`Intl.DateTimeFormat` با locale `fa-IR-u-ca-persian-nu-latn` ساخته می‌شود:
- `ca-persian`: تقویم شمسی.
- `nu-latn`: ارقام لاتین. می‌خواهیم با `parseInt` عدد بگیریم، نه رشته‌ی فارسی.
- `timeZone: 'UTC'`: تبدیل بدون اثر منطقه‌ی زمانی دستگاه.

`formatToParts` آرایه‌ای مثل `[{type:'year',value:'1405'}, {type:'literal',...}, {type:'month',...}, {type:'day',...}]` می‌دهد. `toJ` فقط سه بخش `year`، `month` و `day` را برمی‌دارد.

**چرا همیشه ساعت ۱۲ UTC؟** با نیمه‌شب، یک ساعت جابه‌جایی منطقه‌ی زمانی می‌تواند روز را عوض کند. ظهر UTC در همه‌ی مناطق زمانی همان روز است.

### ۴.۲ `firstOfMonth(y, m)`: پیدا کردن روز اول ماه
می‌خواهیم برای ماه شمسی `(y, m)` مقدار میلادی روز اولش را بدانیم، بدون قانون کبیسه.

1. **تخمین:** نوروز سال شمسی `y` تقریباً ۲۱ مارس سال میلادی `y+621` است. ماه‌های ۱ تا ۶ سی‌ویک‌روزه‌اند و ماه‌های ۷ تا ۱۱ سی‌روزه. پس فاصله‌ی ماه `m` از نوروز:
   - برای `m ≤ 7`: `31 × (m−1)` (ماه ۷ بعد از `6×31=186` روز شروع می‌شود)
   - برای `m > 7`: `186 + 30 × (m−7)`
2. **اصلاح:** تخمین ممکن است یک روز جلو یا عقب باشد (نوروز گاهی ۲۰ یا ۲۱ مارس است). حلقه تا ۱۲ بار `toJ(ms)` را با `(y, m, 1)` مقایسه می‌کند. اگر تاریخ دیرتر بود یک روز عقب می‌رود، اگر زودتر بود یک روز جلو، تا برابر شود.

### ۴.۳ `monthInfo(y, m)`: طول ماه و ستون شروع
- **طول ماه:** از روز اول جلو می‌رویم و می‌شماریم تا ماه عوض شود (حداکثر ۳۱). نیازی به دانستن «اسفند ۲۹ یا ۳۰ روزه است» نیست، خودِ `Intl` جواب می‌دهد.
- **`lead`:** تعداد خانه‌ی خالی قبل از روز اول. `getUTCDay()` یکشنبه را ۰ و شنبه را ۶ می‌دهد. با `(روز + 1) % 7` شنبه می‌شود ۰ (ستون اول تقویم ایرانی).

### ۴.۴ `todayJ()`
تاریخ محلی دستگاه (`getFullYear`، `getMonth`، `getDate`) را با ظهر UTC به `toJ` می‌دهد. «امروز» ساعت دستگاه کاربر است، نه ساعت تهران.

### ۴.۵ `parse(v)`
رشته را لاتین می‌کند و با `(\d{4})\D+(\d{1,2})\D+(\d{1,2})` سه عدد را می‌گیرد. جداکننده هر غیررقمی می‌تواند باشد. اگر کادر خالی یا نامعتبر باشد `null` برمی‌گرداند و تقویم روی «امروز» باز می‌شود.

### ۴.۶ `pick(y, m, d)`
مقدار را با ارقام فارسی و صفر پر (`۱۴۰۵/۰۷/۰۵`) می‌نویسد، `input` و `change` را شلیک می‌کند و می‌بندد. رویدادها `bubbles: true` هستند تا شنونده‌های تفویضی و htmx آن‌ها را ببینند.

### ۴.۷ `render()`: رسم تقویم
هر بار کل محتوای `pop` پاک و از نو ساخته می‌شود. چهار بخش دارد:
1. **سربرگ:** دکمه‌ی «قبل»، `select` ماه، `select` سال (±۱۰ سال اطراف سال نمایش‌داده‌شده) و دکمه‌ی «بعد». `go(dm)` ماه را جابه‌جا می‌کند و در مرز سال سال را عوض می‌کند.
2. **ردیف روزهای هفته:** ش ی د س چ پ ج.
3. **روزها:** `info.lead` خانه‌ی خالی و بعد دکمه‌ی هر روز. روز انتخاب‌شده `btn-primary` است و روز امروز حاشیه‌ی رنگی دارد. کلیک هر روز `pick` را صدا می‌زند. حلقه با IIFE ساخته شده تا مقدار `d` در closure ثابت بماند.
4. **پایین:** دکمه‌ی «امروز» و، فقط اگر `input` صفت `data-clearable` دارد، «پاک‌کردن». پاک‌کردن فقط `change` شلیک می‌کند، نه `input`.

### ۴.۸ `open(input)`
- اگر `input` غیرفعال است یا تقویمش همین الان باز است، برنمی‌گردد. چون هم `focusin` و هم `click` باز می‌کنند، این شرط از باز شدن دوباره جلوگیری می‌کند.
- پنجره‌ی `pop` فقط یک‌بار برای کل صفحه ساخته و به `body` اضافه می‌شود. `dir="rtl"` دارد.
- **`pop` یک شنونده‌ی `click` با `stopPropagation` دارد.** چون `render` دکمه‌ها را از DOM برمی‌دارد، بعد از کلیک `e.target` دیگر داخل `pop` نیست و شنونده‌ی سراسری آن را «کلیک بیرون» می‌دانست و می‌بست.
- **داخل `<dialog>`:** پنجره باید فرزند همان dialog باشد، وگرنه زیر مودال (top-layer) پنهان می‌ماند. پس `pop` به `host = input.closest('dialog') || document.body` منتقل می‌شود.
- **مختصات:**
  - لبه‌ی راست پنجره با لبه‌ی راست کادر هم‌تراز می‌شود (`r.right - 288`، چون عرض `w-72` برابر ۲۸۸ پیکسل است). از چپ حداقل ۸ و از راست حداکثر عرض صفحه منهای ۲۹۶ نگه داشته می‌شود.
  - خارج از dialog به `scrollX/scrollY` اضافه می‌شود (مختصات صفحه).
  - داخل dialog نسبت به خود dialog است.
- **پایین جا نبود:** فقط داخل dialog اگر پنجره از پایین پنجره‌ی مرورگر بیرون بزند و بالا جا باشد، بالای کادر باز می‌شود.

### ۴.۹ شنونده‌ها
| رویداد | کار |
|---|---|
| `focusin` | با Tab یا فوکوس، باز می‌شود |
| `click` | کلیک روی `input` باز می‌کند، هر کلیک دیگر بیرون پنجره می‌بندد |
| `keydown` | Tab و Escape می‌بندند. هر کلید تک‌نویسه‌ای (حرف، رقم و Ctrl+V) و Backspace و Delete متوقف می‌شوند. Enter دست‌نخورده است و فرم ارسال می‌شود |
| `paste` | ممنوع |
| `close` (capture) | بسته‌شدن هر dialog پنجره‌ی تقویم را می‌بندد |
| `submit` (capture) | اعتبارسنجی بازه |

**چرا `close` در فاز capture؟** رویداد `close` روی `<dialog>` حباب نمی‌کند و شنونده‌ی معمولی روی `document` آن را نمی‌بیند.

### ۴.۱۰ اعتبارسنجی بازه
ساختار HTML:
```html
<div data-date-range>
  <input data-jalali-date name="from" ...>
  <input data-jalali-date name="to" ...>
  <span class="hidden" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد.</span>
</div>
```
در `submit` هر `[data-date-range]` با دقیقاً دو `input` بررسی می‌شود. مقدارها به `YYYYMMDD` تبدیل و به‌صورت رشته مقایسه می‌شوند. چون سال ۴ رقمی و ماه و روز دو رقمی است، ترتیب رشته‌ها همان ترتیب تاریخ‌هاست. اگر شروع بعد از پایان باشد، خطا نشان داده می‌شود و `preventDefault` و `stopImmediatePropagation` ارسال را متوقف می‌کنند. ثبت در فاز capture روی `document` باعث می‌شود قبل از شنونده‌ی htmx (که روی خود فرم است) اجرا شود. اگر فرمی ندارید که این را بخواهد، کل این بلوک را حذف کنید.

---

## ۵. استفاده در HTML

بارگذاری اسکریپت (انتهای `<body>`):
```html
<script src="/static/js/jalali_picker.js"></script>
```

### کادر ساده
```html
<input type="text" name="issue_date" dir="ltr" inputmode="none" autocomplete="off"
       data-jalali-date placeholder="۱۴۰۵/۰۷/۲۰" class="input w-full font-technical">
```
- `inputmode="none"`: کیبورد موبایل باز نمی‌شود.
- `dir="ltr"`: ترتیب رقم‌ها به‌هم نمی‌ریزد.
- `autocomplete="off"`: پیشنهاد مرورگر تقویم را نپوشاند.

### با دکمه‌ی پاک‌کردن
```html
<input type="text" name="due_date" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" class="input w-full font-technical">
```

### مقدار اولیه (ویرایش رکورد)
مقدار را از سرور با فرمت `۱۴۰۵/۰۷/۲۰` بدهید (بخش ۷). تقویم روی همان تاریخ باز می‌شود.

### بازه‌ی از-تا
```html
<form method="get">
  <div class="flex flex-col gap-2" data-date-range>
    <input type="text" name="from" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="از تاریخ" class="input input-sm font-technical">
    <input type="text" name="to" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="تا تاریخ" class="input input-sm font-technical">
    <span class="hidden text-error text-xs" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد.</span>
  </div>
  <button type="submit" class="btn btn-primary btn-sm">اعمال</button>
</form>
```

### داخل مودال
```html
<dialog id="m" class="modal">
  <div class="modal-box">
    <input type="text" data-jalali-date ...>
  </div>
</dialog>
```
در daisyUI، `.modal` تمام صفحه است (`position: fixed; inset: 0`) و مختصات داخل dialog درست درمی‌آید. با `<dialog>` بومی و بدون این استایل، به `pop.style.position = 'fixed'` نیاز است (بخش ۸).

### رویدادها
```javascript
document.querySelector('[name=issue_date]').addEventListener('change', function (e) {
  console.log(e.target.value);   // «۱۴۰۵/۰۷/۲۰» (ارقام فارسی)
});
```
با htmx: `hx-trigger="change"` روی خود `input` کار می‌کند.

---

## ۶. CSS

### ۶.۱ اگر Tailwind v4 و daisyUI v5 دارید
فایل JS باید در `input.css` ثبت شود تا Tailwind کلاس‌های داخل آن را بسازد (وگرنه کلاس‌های `grid-cols-7` و مانند آن تولید نمی‌شوند):
```css
@source "../js/jalali_picker.js";
```
دو کلاس شخصی که باید تعریف شوند:
```css
.fb-muted { color: color-mix(in oklab, var(--color-base-content) 60%, transparent); }
.font-technical { font-feature-settings: "tnum" 1; direction: ltr; unicode-bidi: isolate; }
```
`font-technical` را فقط روی عنصر درون‌خطی یا `input` بگذارید. روی بلوک (`div` و `td`) بلوک را به چپ می‌چسباند.

### ۶.۲ اگر daisyUI و Tailwind ندارید (CSS مستقل)
کد JS یک کلاس مارکر `jalali-popup` روی پنجره می‌گذارد. این CSS ظاهر کامل را می‌سازد:
```css
.jalali-popup {
  position: absolute; z-index: 9999; width: 18rem; padding: .75rem;
  background: #fff; color: #1b2430; border: 1px solid #e3e7ec; border-radius: .875rem;
  box-shadow: 0 8px 24px rgb(0 0 0 / .15); font-family: inherit; font-size: .8125rem;
}
.jalali-popup.hidden { display: none; }
.jalali-popup .flex { display: flex; }
.jalali-popup .items-center { align-items: center; }
.jalali-popup .justify-between { justify-content: space-between; }
.jalali-popup .gap-1 { gap: .25rem; }
.jalali-popup .mb-2 { margin-bottom: .5rem; }
.jalali-popup .mt-2 { margin-top: .5rem; }
.jalali-popup .flex-1 { flex: 1 1 0; min-width: 0; }
.jalali-popup .grid { display: grid; }
.jalali-popup .grid-cols-7 { grid-template-columns: repeat(7, 1fr); }
.jalali-popup .text-center { text-align: center; }
.jalali-popup .text-xs { font-size: .75rem; }
.jalali-popup .fb-muted { color: #6b7684; padding: .25rem 0; }
.jalali-popup .font-technical { font-feature-settings: "tnum" 1; }
.jalali-popup button {
  font: inherit; cursor: pointer; border: 0; border-radius: .5rem;
  background: transparent; color: inherit; padding: .3rem .1rem;
}
.jalali-popup button:hover { background: #f0f2f5; }
.jalali-popup .btn-primary { background: #1a4a8a; color: #fff; }
.jalali-popup .btn-primary:hover { background: #1a4a8a; }
.jalali-popup .border-primary { box-shadow: inset 0 0 0 1px #1a4a8a; }
.jalali-popup select {
  font: inherit; padding: .25rem; border: 1px solid #e3e7ec; border-radius: .5rem; background: #fff;
}
```
در این حالت `class` ها در JS بی‌اثرند و فقط CSS بالا تعیین‌کننده است.

---

## ۷. سمت سرور (Django): کد کامل

### ۷.۱ `jalali.py`: تبدیل و نمایش
```python
import jdatetime
from datetime import datetime, date
from django.utils import timezone

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa_digits(value):
    if value is None:
        return ""
    return str(value).translate(_FA)


def jalali_str(value, fmt=None, persian=True):
    """date یا datetime میلادی ← رشته‌ی شمسی. خالی ← ''.
    datetime آگاه از منطقه‌ی زمانی ابتدا به زمان محلی (تهران) برده می‌شود.
    fmt فقط با کدهای عددی (%Y %m %d %H %M %S) استفاده شود؛ نام ماه وابسته به locale است."""
    if not value:
        return ""
    if isinstance(value, datetime):  # datetime زیرکلاس date است؛ ترتیب شرط‌ها مهم است
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        out = jdatetime.datetime.fromgregorian(datetime=value).strftime(fmt or "%Y/%m/%d %H:%M")
    elif isinstance(value, date):
        out = jdatetime.date.fromgregorian(date=value).strftime(fmt or "%Y/%m/%d")
    else:
        return str(value)
    return to_fa_digits(out) if persian else out
```

### ۷.۲ `jalali_forms.py`: فیلدهای فرم
```python
from datetime import datetime, date

import jdatetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .jalali import jalali_str

_FA_AR_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_digits_and_separators(val_str):
    """ارقام فارسی و عربی ← لاتین، «-» ← «/»."""
    if not val_str:
        return ""
    return str(val_str).strip().translate(_FA_AR_TO_EN).replace("-", "/")


class JalaliDateField(forms.Field):
    default_error_messages = {
        "invalid": "تاریخ وارد شده نامعتبر است. نمونه صحیح: ۱۴۰۵/۰۶/۳۰",
    }

    def prepare_value(self, value):
        # برای نمایش مقدار اولیه‌ی فرم
        if isinstance(value, (datetime, date)):
            return jalali_str(value, fmt="%Y/%m/%d", persian=True)
        return value or ""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        parts = normalize_digits_and_separators(value).split("/")
        if len(parts) != 3:
            raise ValidationError(self.error_messages["invalid"], code="invalid")
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return jdatetime.date(year, month, day).togregorian()  # ماه ۱۳، روز ۳۱ مهر، ۳۰ اسفند غیرکبیسه ← ValueError
        except (ValueError, TypeError, OverflowError):
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        try:
            data_val = self.to_python(data)
        except ValidationError:
            return True
        return self.to_python(initial) != data_val


class JalaliDateTimeField(forms.Field):
    """تاریخ و ساعت متنی («۱۴۰۵/۰۶/۳۰ ۱۴:۳۰»). خروجی datetime آگاه از منطقه‌ی زمانی (تهران)."""

    default_error_messages = {
        "invalid": "تاریخ و ساعت وارد شده نامعتبر است. نمونه صحیح: ۱۴۰۵/۰۶/۳۰ ۱۴:۳۰",
    }

    def prepare_value(self, value):
        if isinstance(value, datetime):
            return jalali_str(value, fmt="%Y/%m/%d %H:%M", persian=True)
        if isinstance(value, date):
            return jalali_str(value, fmt="%Y/%m/%d", persian=True)
        return value or ""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime):
            return timezone.make_aware(value) if timezone.is_naive(value) else value

        tokens = normalize_digits_and_separators(value).split()
        if len(tokens) == 1:
            date_part, time_part = tokens[0], "00:00:00"
        elif len(tokens) == 2:
            date_part, time_part = tokens
        else:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        d, t = date_part.split("/"), time_part.split(":")
        if len(d) != 3 or len(t) not in (2, 3):
            raise ValidationError(self.error_messages["invalid"], code="invalid")
        try:
            jdt = jdatetime.datetime(
                int(d[0]), int(d[1]), int(d[2]), int(t[0]), int(t[1]), int(t[2]) if len(t) == 3 else 0
            )
            return timezone.make_aware(jdt.togregorian(), timezone=timezone.get_current_timezone())
        except (ValueError, TypeError, OverflowError):
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        try:
            data_val = self.to_python(data)
        except ValidationError:
            return True
        initial_val = self.to_python(initial)
        if initial_val is None and data_val is None:
            return False
        if initial_val is None or data_val is None:
            return True
        return abs((initial_val - data_val).total_seconds()) > 59
```

### ۷.۳ تگ‌ها و فیلترهای تمپلیت (`templatetags/jalali_tags.py`)
```python
from django import template
from .jalali import jalali_str, to_fa_digits  # مسیر import را با ساختار خودتان تنظیم کنید

register = template.Library()


@register.filter
def to_jalali(value, format_str=None):
    """{{ obj.created_at|to_jalali:"%Y/%m/%d %H:%M" }}"""
    return jalali_str(value, fmt=format_str, persian=True)


@register.filter
def fa_digits(value):
    """{{ 123|fa_digits }} ← ۱۲۳"""
    return to_fa_digits(value)
```

### ۷.۴ خواندن امن برای URL و فیلتر (بدون خطا)
وقتی ورودی از آدرس مرورگر می‌آید (مثل فیلتر جدول)، خطا نباید صفحه را بشکند:
```python
def parse_jalali_safe(raw):
    """رشته‌ی شمسی ← date میلادی؛ خالی، نامعتبر یا خارج از ۱۹۰۰ تا ۲۹۹۹ ← None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        day = JalaliDateField().to_python(raw)
    except ValidationError:
        return None
    return day if day and 1900 <= day.year <= 2999 else None
```

---

## ۸. استفاده در Django

### ۸.۱ فرم
```python
from django import forms
from .jalali_forms import JalaliDateField


class InvoiceForm(forms.Form):
    issue_date = JalaliDateField(label="تاریخ صدور", required=False)
```
تمپلیت:
```html
<input type="text" name="issue_date" value="{{ form.issue_date.value|default:'' }}"
       data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off"
       class="input w-full font-technical">
```
اگر فرم را با `initial={"issue_date": date(2026, 9, 21)}` بسازید، `prepare_value` مقدار را به `۱۴۰۵/۰۶/۳۰` تبدیل می‌کند.

### ۸.۲ ویوی ساده بدون فرم
```python
from django.core.exceptions import ValidationError
from .jalali_forms import JalaliDateField


def save(request):
    raw = (request.POST.get("issue_date") or "").strip()
    try:
        day = JalaliDateField().clean(raw) if raw else None
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
        return redirect("...")
    obj.issue_date = day  # DateField میلادی
    obj.save()
```

### ۸.۳ تاریخ + ساعت (تقویم و دو select)
تقویم فقط روز می‌دهد. برای ساعت دو `select` کنارش بگذارید (ساعت `۰۰` تا `۲۳`، دقیقه با فاصله‌ی ۵):
```python
from datetime import datetime
from django.utils import timezone


def build_due(date_raw, hour_raw, minute_raw):
    if not (date_raw or "").strip():
        return None
    try:
        day = JalaliDateField().clean(date_raw)
        hour, minute = int(hour_raw or 17), int(minute_raw or 0)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return timezone.make_aware(datetime(day.year, day.month, day.day, hour, minute))
    except Exception:
        raise ValueError("تاریخ یا ساعت سررسید نامعتبر است.")
```
برای نمایش دوباره‌ی مقدار ذخیره‌شده در فرم ویرایش، `timezone.localtime(due_at)` بگیرید و روز را با `jalali_str(local, fmt="%Y/%m/%d")` و ساعت را با `local.hour` و `local.minute` پر کنید.

### ۸.۴ نمایش
```html
{% load jalali_tags %}
{{ invoice.issue_date|to_jalali:"%Y/%m/%d" }}
{{ invoice.created_at|to_jalali }}
```
در پایتون: `jalali_str(value, fmt="%Y/%m/%d", persian=False)` برای خروجی لاتین (مثلاً CSV).

---

## ۹. تست

### ۹.۱ تست‌های پایتون
```python
from datetime import date, datetime, timezone as dt_timezone
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .jalali import jalali_str
from .jalali_forms import JalaliDateField, JalaliDateTimeField


class JalaliTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(jalali_str(date(2026, 3, 21)), "۱۴۰۵/۰۱/۰۱")
        aware = datetime(2026, 9, 20, 21, 0, tzinfo=dt_timezone.utc)  # ۰۰:۳۰ تهران، روز بعد
        self.assertEqual(jalali_str(aware), "۱۴۰۵/۰۶/۳۰ ۰۰:۳۰")
        self.assertEqual(jalali_str(None), "")
        self.assertEqual(jalali_str(date(2026, 3, 21), persian=False), "1405/01/01")

    def test_parse_digits_and_separators(self):
        f = JalaliDateField()
        self.assertEqual(f.to_python("۱۴۰۵/۰۶/۳۰"), date(2026, 9, 21))
        self.assertEqual(f.to_python("1405-06-30"), date(2026, 9, 21))
        self.assertEqual(f.to_python("١٤٠٥/٠٦/٣٠"), date(2026, 9, 21))  # ارقام عربی
        self.assertIsNone(f.to_python(""))

    def test_invalid(self):
        f = JalaliDateField()
        for bad in ("۱۴۰۵/۱۳/۰۱", "۱۴۰۵/۰۷/۳۱", "abc", "۱۴۰۵/۰۶", "۱۴۰۵/۰۶/۳۰/۱", "۱۴۰۴/۱۲/۳۰"):
            with self.assertRaises(ValidationError, msg=bad):
                f.to_python(bad)

    def test_leap_esfand(self):
        f = JalaliDateField()
        self.assertEqual(f.to_python("۱۴۰۳/۱۲/۳۰"), date(2025, 3, 20))  # ۱۴۰۳ کبیسه است

    def test_roundtrip_and_has_changed(self):
        f = JalaliDateField()
        self.assertEqual(f.prepare_value(date(2026, 9, 21)), "۱۴۰۵/۰۶/۳۰")
        self.assertFalse(f.has_changed(date(2026, 9, 21), "۱۴۰۵/۰۶/۳۰"))
        self.assertTrue(f.has_changed(date(2026, 9, 21), "۱۴۰۵/۰۶/۲۹"))

    def test_datetime_field(self):
        f = JalaliDateTimeField()
        got = f.to_python("۱۴۰۵/۰۶/۳۰ ۰۰:۳۰")
        self.assertEqual(got.astimezone(dt_timezone.utc), datetime(2026, 9, 20, 21, 0, tzinfo=dt_timezone.utc))
        with self.assertRaises(ValidationError):
            f.to_python("۱۴۰۵/۰۶/۳۰ ۲۵:۰۰")
```
فرض: `TIME_ZONE='Asia/Tehran'` و `USE_TZ=True` در تنظیمات تست.

### ۹.۲ بررسی هم‌خوانی کلاینت و سرور (یک‌بار بزنید)
کلاینت (`Intl`) و سرور (`jdatetime`) از دو منبع جدا کبیسه را حساب می‌کنند. اگر در سالی اختلاف داشته باشند، یکی ۳۰ اسفند را نشان می‌دهد و دیگری رد می‌کند.

کنسول مرورگر:
```javascript
var f = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {year:'numeric',month:'numeric',day:'numeric',timeZone:'UTC'});
function lastEsfand(y) {
  var max = 0;
  for (var ms = Date.UTC(y + 622, 1, 15, 12); ms < Date.UTC(y + 622, 3, 5, 12); ms += 86400000) {
    var o = {}; f.formatToParts(new Date(ms)).forEach(function (p) { o[p.type] = parseInt(p.value, 10); });
    if (o.year === y && o.month === 12 && o.day > max) max = o.day;
  }
  return max;
}
var out = []; for (var y = 1380; y <= 1450; y++) out.push(y + ':' + lastEsfand(y));
console.log(out.join(' '));
```
پایتون (`python manage.py shell`):
```python
import jdatetime

out = []
for y in range(1380, 1451):
    try:
        jdatetime.date(y, 12, 30)
        out.append(f"{y}:30")
    except ValueError:
        out.append(f"{y}:29")
print(" ".join(out))
```
دو خروجی باید یکی باشند. اگر سالی فرق داشت، سرور تصمیم‌گیرنده است. در آن سال کاربر ممکن است ۳۰ اسفند را انتخاب کند و با خطای «تاریخ نامعتبر» روبه‌رو شود. این مورد را گزارش بدهید و حدس نزنید.

### ۹.۳ تست دستی در مرورگر
- کلیک روی کادر خالی: تقویم ماه جاری، روز امروز با حاشیه.
- انتخاب روز: مقدار فارسی با صفر پر، تقویم بسته.
- باز کردن دوباره: روی همان ماه، روز انتخاب‌شده آبی.
- ماه اسفند سال کبیسه (۳۰ روز) و غیرکبیسه (۲۹ روز)، ماه‌های ۷ (سی روزه) و ۶ (سی‌ویک روزه).
- جابه‌جایی ماه در مرز سال (فروردین ← اسفند سال قبل).
- تایپ، Backspace و Ctrl+V بی‌اثر. Tab و Esc می‌بندند.
- `data-clearable`: «پاک‌کردن» کادر را خالی می‌کند.
- داخل مودال: تقویم روی مودال است و جایی که جا نباشد بالای کادر باز می‌شود. بستن مودال با Esc تقویم را هم می‌بندد.
- بازه‌ی از-تا با تاریخ برعکس: خطا نشان داده می‌شود و ارسال انجام نمی‌شود.
- موبایل (کیبورد باز نشود)، حالت روشن و تاریک، و کادر `disabled` (باز نمی‌شود).

---

## ۱۰. تله‌ها و محدودیت‌ها

1. **«امروز» ساعت دستگاه کاربر است**، نه تهران. اگر دستگاه روی منطقه‌ی زمانی دیگری باشد، نزدیک نیمه‌شب «امروز» ممکن است یک روز فرق کند.
2. **وابسته به ICU مرورگر.** مرورگر خیلی قدیمی یا Node بدون ICU کامل ممکن است `ca-persian` را نشناسد.
3. **پنجره فقط هنگام باز شدن جایگزین می‌شود.** روی اسکرول یا تغییر اندازه‌ی صفحه جابه‌جا نمی‌شود. اگر صفحه با پنجره‌ی باز اسکرول شود، پنجره از کادر جدا می‌ماند تا کلیک بعدی بیرون آن را ببندد.
4. **`<dialog>` بدون تمام‌صفحه‌بودن:** کد داخل dialog فرض می‌کند dialog کل صفحه را می‌پوشاند (مثل `.modal` در daisyUI). اگر چنین نیست، بعد از `host.appendChild(pop)` این را اضافه کنید:
   ```javascript
   if (inDialog) pop.style.position = 'fixed';
   ```
5. **بدون جابه‌جایی با کیبورد داخل تقویم و بدون `aria`.** فقط ماوس و لمس. اگر دسترس‌پذیری لازم است، باید اضافه شود.
6. **تایپ دستی ممنوع است**، پس برای تاریخ‌های خیلی دور (مثلاً تاریخ تولد ۱۳۴۰) باید سال را با `select` عوض کرد. `select` سال فقط ±۱۰ سال اطراف سال نمایش‌داده‌شده را دارد.
7. **مقایسه‌ی بازه فقط سمت کلاینت است.** سرور باید خودش بازه‌ی برعکس را مدیریت کند، مثلاً در فیلتر جابه‌جا کند.
8. **هر `input` که `type="date"` است این‌جا کار نمی‌کند.** باید `type="text"` باشد، چون مقدار فارسی است.
9. **ارقام:** مقدار در کادر فارسی است. هر اسکریپت دیگری که مقدار را می‌خواند باید `en()` مشابه بزند، یا از سرور بخواهید ارقام را لاتین کند (`normalize_digits_and_separators` این کار را می‌کند).
10. **`has_changed` فیلد Django** تاریخ نامعتبر را «تغییر کرده» حساب می‌کند تا خطای اعتبارسنجی ظاهر شود.
11. **`jalali_str` با `fmt` حاوی `%B` یا `%A`** نام ماه و روز را به انگلیسی می‌دهد (وابسته به locale). فقط از کدهای عددی استفاده کنید.
12. **سال‌های تاریخی:** `jdatetime.date.togregorian` برای سال‌های خیلی دور مشکل ندارد، اما فیلدهای دیتابیس و ابزارهای دیگر ممکن است. `parse_jalali_safe` برای همین سقف ۱۹۰۰ تا ۲۹۹۹ را دارد.

---

## ۱۱. چک‌لیست انتقال به پروژه‌ی جدید

1. `pip install jdatetime`
2. `jalali.py` و `jalali_forms.py` را کپی کنید و `templatetags/jalali_tags.py` را بسازید.
3. `jalali_picker.js` را در static بگذارید و در پایین `base.html` بارگذاری کنید.
4. CSS را اضافه کنید: بخش ۶.۱ برای Tailwind و daisyUI، یا ۶.۲ برای CSS مستقل.
5. تنظیمات: `USE_TZ=True` و `TIME_ZONE='Asia/Tehran'`.
6. یک `input` آزمایشی با `data-jalali-date` بگذارید و تست دستی بخش ۹.۳ را انجام دهید.
7. تست‌های بخش ۹.۱ را اجرا کنید و بررسی هم‌خوانی ۹.۲ را یک‌بار بزنید.

### متن آماده برای دستیار کدنویس پروژه‌ی جدید
```
تقویم شمسی را از سند منتقل کن.
- jalali_picker.js، jalali.py، jalali_forms.py و jalali_tags.py را عیناً از سند بساز.
- منطق را «بهتر» نکن و هر جا کد با سند نخواند، توقف و گزارش.
- jdatetime را به requirements اضافه کن.
- اسکریپت را پایین base.html بارگذاری کن و CSS بخش ۶ را اضافه کن.
- یک صفحه‌ی آزمایشی با سه کادر بساز: ساده، data-clearable، و یک بازه‌ی data-date-range.
- تست‌های بخش ۹.۱ را در پروژه بنویس و اجرا کن.
- خروجی کنسول و پایتون بخش ۹.۲ را مقایسه و گزارش کن؛ اگر سالی فرق داشت فقط گزارش بده.
```