import re
import time

from .. import http
from .base import Product

BASE = "https://www.amazon.com.au"
LABEL = "Amazon AU"
FULL_LISTING = True

# Markers of Amazon's bot wall. When we hit it we raise BlockedError so the run
# is treated as "no data" rather than "everything went out of stock".
BLOCK_MARKERS = (
    "api-services-support@amazon.com",
    "/errors/validateCaptcha",
    "Robot Check",
)


def fetch(cfg):
    out = []
    asins = cfg.get("asins") or {}
    for i, (asin, label) in enumerate(asins.items()):
        if i:
            time.sleep(2.5)  # be gentle; a handful of ASINs per run is the intended scale
        r = http.get(f"{BASE}/dp/{asin}")
        h = r.text
        if r.status_code == 503 or any(m in h for m in BLOCK_MARKERS):
            raise http.BlockedError(f"bot wall at asin {asin} (HTTP {r.status_code})")
        if r.status_code == 404:
            continue
        if r.status_code != 200:
            raise http.FetchError(f"dp/{asin} -> HTTP {r.status_code}")

        t = re.search(r'id="productTitle"[^>]*>\s*([^<]+)', h)
        title = t.group(1).strip() if t else str(label or asin)

        a = re.search(r'id="availability".{0,400}?<span[^>]*>\s*([^<]+)', h, re.S)
        avail_text = a.group(1).strip().lower() if a else ""
        has_buy_button = 'id="add-to-cart-button"' in h or 'id="buy-now-button"' in h
        explicitly_out = any(x in avail_text for x in ("unavailable", "out of stock"))
        available = has_buy_button and not explicitly_out

        p = re.search(r'"priceAmount"\s*:\s*([0-9]+(?:\.[0-9]+)?)', h) or re.search(
            r'class="a-offscreen">\s*\$([0-9,]+(?:\.[0-9]+)?)', h
        )
        price = float(p.group(1).replace(",", "")) if p else None

        status = "Pre-order" if available and re.search(r"Pre-?order now", h, re.I) else ""

        out.append(
            Product(
                key=asin,
                title=title,
                url=f"{BASE}/dp/{asin}",
                available=available,
                price=price,
                status=status,
            )
        )
    return out
