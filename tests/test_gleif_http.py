import json
import os
import types

import pytest

from patentpack.gleif.http import GLEIF_API, make_session, safe_get, smoke_test


class _Resp:
    def __init__(self, status=200, text="", json_obj=None):
        self.status_code = status
        self.text = text
        self._json = json_obj

    def json(self):
        if isinstance(self._json, Exception):
            raise self._json
        return self._json


def test_make_session_headers(monkeypatch):
    monkeypatch.setenv("PATENTPACK_USER_AGENT", "ua-test-123")
    s = make_session()
    # UA taken from env; Accept set as JSON:API
    assert s.headers.get("User-Agent") == "ua-test-123"
    assert s.headers.get("Accept") == "application/vnd.api+json"
    # Retry adapter mounted for https
    assert "https://" in s.adapters


def test_safe_get_ok_json(monkeypatch):
    # stub Session.get to return 200 + valid JSON
    def fake_get(self, url, params=None, timeout=30):
        assert url == GLEIF_API
        return _Resp(status=200, text='{"data":[1]}', json_obj={"data": [1]})

    # attach bound method to a real session
    sess = make_session()
    sess.get = types.MethodType(fake_get, sess)

    j, status, body = safe_get(sess, {"page[size]": "1"})
    assert status == 200
    assert j == {"data": [1]}
    assert "data" in body  # snippet echo


def test_safe_get_http_error(monkeypatch):
    def fake_get(self, url, params=None, timeout=30):
        return _Resp(
            status=503, text="Service Unavailable", json_obj={"err": 1}
        )

    sess = make_session()
    sess.get = types.MethodType(fake_get, sess)

    j, status, body = safe_get(sess, {"x": "y"})
    assert j is None
    assert status == 503
    assert "Service Unavailable" in body


def test_safe_get_json_decode_error(monkeypatch):
    def fake_get(self, url, params=None, timeout=30):
        return _Resp(status=200, text="not-json", json_obj=ValueError("boom"))

    sess = make_session()
    sess.get = types.MethodType(fake_get, sess)

    j, status, body = safe_get(sess, {})
    assert j is None
    assert status == 200
    assert "not-json" in body


def test_smoke_test_writes_to_stderr(monkeypatch, capsys):
    # make safe_get return an error so smoke_test prints both lines
    from patentpack.gleif import http as http_mod

    def fake_safe_get(session, params):
        return None, 418, "teapot"

    monkeypatch.setattr(http_mod, "safe_get", fake_safe_get)
    smoke_test(make_session())
    captured = capsys.readouterr()
    assert "[smoke] GET" in captured.err
    assert "418" in captured.err
    assert "teapot" in captured.err
