/* MM.otp: digit boxes, resend timer, Web OTP. The real <input data-otp> stays in the form (hidden) and holds the ASCII code. */
(function (MM) {
  "use strict";

  var webOtpAbort = null;

  function listenWebOtp(fill) {
    if (!("OTPCredential" in window) || !navigator.credentials) return;
    if (webOtpAbort) webOtpAbort.abort();
    webOtpAbort = new AbortController();
    navigator.credentials
      .get({ otp: { transport: ["sms"] }, signal: webOtpAbort.signal })
      .then(function (cred) { if (cred && cred.code) fill(cred.code); }) /* fills only, never submits (docs/05) */
      .catch(function () {});
  }

  document.addEventListener("htmx:beforeSwap", function (event) {
    var target = event.detail && event.detail.target;
    if (target && target.id === "login-flow" && webOtpAbort) {
      webOtpAbort.abort();
      webOtpAbort = null;
    }
  });

  function build(source) {
    if (source.dataset.otpReady === "1") return;
    source.dataset.otpReady = "1";

    var length = parseInt(source.getAttribute("data-otp-length") || "4", 10);
    var invalid = source.getAttribute("aria-invalid") === "true";
    var submitId = source.getAttribute("data-otp-submit");
    var boxes = [];
    var group = document.createElement("div");
    group.className = "flex items-center justify-center gap-2";
    group.dir = "ltr"; /* digits run left to right */
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "کد تایید");

    for (var i = 0; i < length; i++) {
      var box = document.createElement("input");
      box.type = "text";
      box.inputMode = "numeric";
      box.autocomplete = i === 0 ? "one-time-code" : "off";
      box.className = "input input-lg h-14 min-h-14 w-12 sm:w-14 px-0 text-center text-title num" + (invalid ? " input-error" : "");
      box.setAttribute("aria-label", "رقم " + MM.fmt.faDigits(i + 1) + " از " + MM.fmt.faDigits(length));
      boxes.push(box);
      group.appendChild(box);
    }

    source.value = "";
    source.type = "hidden";
    source.parentNode.insertBefore(group, source);

    function digitsOf(text) { return MM.fmt.enDigits(text).replace(/\D/g, ""); }

    function sync() {
      source.value = boxes.map(function (b) { return MM.fmt.enDigits(b.value); }).join("");
    }

    function fillFrom(index, digits) {
      var last = index;
      for (var k = 0; k < digits.length && index + k < length; k++) {
        boxes[index + k].value = MM.fmt.faDigits(digits.charAt(k));
        last = index + k;
      }
      sync();
      if (source.value.length === length) {
        var submit = submitId && document.getElementById(submitId);
        if (submit) submit.focus(); /* the user presses Enter; we never auto-submit */
      } else {
        boxes[Math.min(last + 1, length - 1)].focus();
      }
    }

    boxes.forEach(function (box, index) {
      box.addEventListener("focus", function () { box.select(); });

      box.addEventListener("input", function () {
        var digits = digitsOf(box.value);
        box.value = "";
        if (!digits) { sync(); return; }
        fillFrom(index, digits); /* several digits = paste or SMS autofill landing in one box */
      });

      box.addEventListener("keydown", function (event) {
        if (event.key === "Backspace" && !box.value && index > 0) {
          boxes[index - 1].value = "";
          boxes[index - 1].focus();
          sync();
          event.preventDefault();
        } else if (event.key === "ArrowLeft" && index > 0) {
          boxes[index - 1].focus();
          event.preventDefault();
        } else if (event.key === "ArrowRight" && index < length - 1) {
          boxes[index + 1].focus();
          event.preventDefault();
        }
      });

      box.addEventListener("paste", function (event) {
        var digits = digitsOf((event.clipboardData || window.clipboardData).getData("text"));
        if (!digits) return;
        event.preventDefault();
        fillFrom(digits.length > 1 ? 0 : index, digits);
      });
    });

    boxes[0].focus();
    listenWebOtp(function (code) { fillFrom(0, digitsOf(code)); });
  }

  function startTimer(el) {
    if (el.dataset.otpTimerStarted === "1") return;
    el.dataset.otpTimerStarted = "1";
    var remaining = parseInt(el.getAttribute("data-seconds") || "0", 10) || 0;
    var resend = document.getElementById(el.getAttribute("data-otp-resend") || "otp-resend");
    var timer = window.setInterval(tick, 1000);

    function tick() {
      if (!el.isConnected) { window.clearInterval(timer); return; }
      if (resend) resend.disabled = remaining > 0;
      if (remaining <= 0) {
        el.textContent = "کد را دریافت نکردید؟";
        window.clearInterval(timer);
        return;
      }
      var minutes = Math.floor(remaining / 60);
      var seconds = remaining % 60;
      el.textContent = "ارسال دوباره تا " + MM.fmt.faDigits(minutes + ":" + (seconds < 10 ? "0" : "") + seconds);
      remaining -= 1;
    }
    tick();
  }

  MM.otp = { build: build, startTimer: startTimer };
  MM.init("otp", function (root) {
    MM.each(root, "[data-otp]", build);
    MM.each(root, "[data-otp-timer]", startTimer);
  });
})(window.MM);
