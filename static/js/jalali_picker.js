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
