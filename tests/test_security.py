from app.auth import digest


def test_session_token_digest_is_stable_and_not_raw():
    token = "a-long-random-session-token"
    assert digest(token) == digest(token)
    assert digest(token) != token
    assert len(digest(token)) == 64
