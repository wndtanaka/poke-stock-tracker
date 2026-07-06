import time

from .. import http
from .base import Product, to_float

BASE = "https://toymate.com.au"
LABEL = "Toymate"
FULL_LISTING = True

# Toymate (BigCommerce) renders its product grid via Fast Simon; the same API the
# site's own JS calls is public JSON. UUID comes from the site's page source.
API = "https://api.fastsimon.com/full_text_search"
DEFAULT_UUID = "ac0f15b5-8578-40fe-821c-ec742c109347"
PER_PAGE = 40
MAX_RESULTS = 400


def fetch(cfg):
    found = {}
    include = [k.lower() for k in cfg.get("include_any") or []]

    for q in cfg.get("queries") or ["pokemon tcg"]:
        page = 1
        while True:
            r = http.get(
                API,
                params={
                    "UUID": cfg.get("uuid") or DEFAULT_UUID,
                    "store_id": cfg.get("store_id", 1),
                    "q": q,
                    "page_num": page,
                    "products_per_page": PER_PAGE,
                    "api_type": "json",
                },
                headers={"Origin": BASE, "Referer": BASE + "/"},
            )
            if r.status_code != 200:
                raise http.FetchError(f"fastsimon {q!r} p{page} -> HTTP {r.status_code}")
            d = r.json()
            items = d.get("items") or []
            for it in items:
                title = it.get("l") or ""
                tl = title.lower()
                if "pokemon" not in tl and "pokémon" not in tl:
                    continue
                if include and not any(k in tl for k in include):
                    continue
                u = it.get("u") or ""
                found[str(it.get("id"))] = Product(
                    key=str(it.get("id")),
                    title=title,
                    url=u if u.startswith("http") else BASE + u,
                    available=bool(it.get("iso")),  # "in stock online"
                    price=to_float(it.get("p")),
                    image=it.get("t") or None,
                )
            total = int(d.get("total_results") or 0)
            if not items or page * PER_PAGE >= min(total, MAX_RESULTS):
                break
            page += 1
            time.sleep(0.4)
        time.sleep(0.4)

    return list(found.values())
