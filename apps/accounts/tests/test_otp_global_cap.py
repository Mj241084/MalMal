from apps.accounts import otp, ratelimit


def test_global_cap_stops_sms_floods_across_different_mobiles(db, settings, monkeypatch):
    settings.SMS_BACKEND = "console"
    monkeypatch.setattr(ratelimit, "GLOBAL_HOURLY_LIMIT", 1)
    assert otp.request_code("09121230011").ok
    assert otp.request_code("09121230012").status == otp.STATUS_RATE_LIMITED
