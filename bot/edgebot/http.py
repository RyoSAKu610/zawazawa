"""共通HTTPクライアント。requests があれば使い、無ければ標準ライブラリで動く。

リトライは冪等なGETのみ。POST(発注)は二重発注防止のためリトライしない。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "edgebot/0.1"
DEFAULT_TIMEOUT = 10.0

try:  # requests があれば接続プール等で有利
    import requests  # type: ignore

    _SESSION: "requests.Session | None" = requests.Session()
except Exception:  # pragma: no cover
    _SESSION = None


class HttpError(RuntimeError):
    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} for {url}: {body[:300]}")
        self.status = status
        self.body = body
        self.url = url


def get_json(url: str, params: dict | None = None, headers: dict | None = None,
             timeout: float = DEFAULT_TIMEOUT, retries: int = 2):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _request("GET", url, None, headers, timeout)
        except HttpError as e:
            if e.status < 500 and e.status != 429:
                raise
            last = e
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            last = e
        time.sleep(0.5 * (2 ** attempt))
    raise RuntimeError(f"GET failed after retries: {url}") from last


def post_json(url: str, params: dict | None = None, headers: dict | None = None,
              body: dict | str | None = None, timeout: float = DEFAULT_TIMEOUT):
    """発注系。リトライしない。"""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return _request("POST", url, body, headers, timeout)


def delete_json(url: str, params: dict | None = None, headers: dict | None = None,
                timeout: float = DEFAULT_TIMEOUT):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return _request("DELETE", url, None, headers, timeout)


def _request(method: str, url: str, body, headers: dict | None, timeout: float):
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)

    data: bytes | None = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        else:
            data = str(body).encode()

    if _SESSION is not None:
        resp = _SESSION.request(method, url, data=data, headers=hdrs, timeout=timeout)
        if resp.status_code >= 400:
            raise HttpError(resp.status_code, resp.text, url)
        return resp.json()

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, e.read().decode(errors="replace"), url) from e
