import time

from curl_cffi import requests as creq


class FetchError(Exception):
    pass


class BlockedError(Exception):
    """The site is refusing us (bot wall / captcha), not just erroring."""


BASE_HEADERS = {"Accept-Language": "en-AU,en;q=0.9"}
RETRYABLE = {429, 500, 502, 503, 520, 522, 524}


def get(url, params=None, headers=None, timeout=30, retries=2, impersonate="chrome"):
    err = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(2 * attempt)
        try:
            r = creq.get(
                url,
                params=params,
                headers={**BASE_HEADERS, **(headers or {})},
                timeout=timeout,
                impersonate=impersonate,
            )
        except Exception as e:
            err = e
            continue
        if r.status_code in RETRYABLE and attempt < retries:
            err = FetchError(f"HTTP {r.status_code}")
            continue
        return r
    raise FetchError(f"GET {url} failed after {retries + 1} attempts: {err}")


def post_json(url, payload, timeout=30):
    return creq.post(url, json=payload, timeout=timeout)
