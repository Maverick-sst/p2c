from twilio.request_validator import RequestValidator

from app.security import CallSecurity


def make_security():
    return CallSecurity("test-auth-token", "+919999999999", "123456", max_pin_attempts=2)


def test_caller_allowlist_is_exact():
    security = make_security()
    assert security.caller_allowed("+919999999999")
    assert not security.caller_allowed("+918888888888")
    assert not security.caller_allowed(None)


def test_pin_attempts_are_limited_and_success_resets_counter():
    security = make_security()
    caller = "+919999999999"
    assert not security.verify_pin("000000", caller)
    assert not security.verify_pin("111111", caller)
    assert not security.verify_pin("123456", caller)
    security.pin_attempts.pop(caller, None)
    assert security.verify_pin("123456", caller)


def test_session_authentication_and_close():
    security = make_security()
    security.create_session("CA-test")
    assert not security.is_authenticated("CA-test")
    security.authenticate_session("CA-test")
    assert security.is_authenticated("CA-test")
    security.close_session("CA-test")
    assert not security.is_authenticated("CA-test")


def test_twilio_signature_validation():
    security = make_security()
    validator = RequestValidator("test-auth-token")
    url = "https://example.ngrok.app/voice"
    params = {"CallSid": "CA123", "From": "+919999999999"}
    signature = validator.compute_signature(url, params)

    assert security.valid_twilio_signature(url, params, signature)
    assert not security.valid_twilio_signature(url, params, "not-a-valid-signature")
