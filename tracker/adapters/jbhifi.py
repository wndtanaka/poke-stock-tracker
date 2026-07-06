import time

from .. import http
from .base import Product, to_float

BASE = "https://www.jbhifi.com.au"
LABEL = "JB Hi-Fi"
FULL_LISTING = True


def fetch(cfg):
    found = {}

    # JB runs on Shopify: the search-suggest endpoint returns clean JSON with an
    # `available` flag. Max ~10 results per query, so we sweep several phrases.
    for q in cfg.get("queries") or []:
        r = http.get(
            f"{BASE}/search/suggest.json",
            params={"q": q, "resources[type]": "product", "resources[limit]": "10"},
        )
        if r.status_code != 200:
            raise http.FetchError(f"suggest {q!r} -> HTTP {r.status_code}")
        products = ((r.json().get("resources") or {}).get("results") or {}).get("products") or []
        for p in products:
            title = p.get("title") or ""
            handle = p.get("handle")
            if not handle or "pokemon" not in title.lower():
                continue
            url = (p.get("url") or f"/products/{handle}").split("?")[0]
            found[handle] = Product(
                key=handle,
                title=title,
                url=BASE + url,
                available=bool(p.get("available")),
                price=to_float(p.get("price")),
                image=(p.get("featured_image") or {}).get("url"),
            )
        time.sleep(0.4)

    # Watched products given as JB URLs are always fetched directly, so
    # watching them doesn't depend on the search queries finding them.
    for entry in cfg.get("watch") or []:
        e = str(entry)
        if "/products/" not in e:
            continue
        handle = e.split("/products/")[-1].split("?")[0].strip("/ ")
        if not handle or handle in found:
            continue
        r = http.get(f"{BASE}/products/{handle}.js")
        if r.status_code == 404:
            continue
        if r.status_code != 200:
            raise http.FetchError(f"products/{handle}.js -> HTTP {r.status_code}")
        p = r.json()
        variants = p.get("variants") or []
        images = p.get("images") or []
        found[handle] = Product(
            key=handle,
            title=p.get("title") or handle,
            url=f"{BASE}/products/{handle}",
            available=any(v.get("available") for v in variants),
            price=(p.get("price") or 0) / 100.0 or None,  # .js endpoint prices are in cents
            image=("https:" + images[0]) if images and str(images[0]).startswith("//") else (images[0] if images else None),
        )
        time.sleep(0.4)

    return list(found.values())
