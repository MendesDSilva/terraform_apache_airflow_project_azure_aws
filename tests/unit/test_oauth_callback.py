import pytest

from scripts.oauth_browser import validated_callback

AUTH = "https://workspace.example/oidc/auth?redirect_uri=http%3A%2F%2Flocalhost%3A8020%2Fcallback"


def test_local_callback_only():
    callback = "http://localhost:8020/callback?code=temporary&state=random"
    assert validated_callback(AUTH, callback) == callback
    for invalid in ["http://example.com/callback?code=x&state=y",
                    "http://localhost:9999/callback?code=x&state=y",
                    "http://localhost:8020/callback?error=access_denied"]:
        with pytest.raises(ValueError):
            validated_callback(AUTH, invalid)
