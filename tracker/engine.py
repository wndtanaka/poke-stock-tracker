import time
from datetime import datetime, timezone

from . import http
from .adapters import ADAPTERS


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(url):
    return url.rstrip("/").split("?")[0].split("/")[-1].lower()


def _matches(p, terms):
    """A term matches by product-URL slug if it looks like a URL, else by
    case-insensitive title substring."""
    tl = p.title.lower()
    for t in terms or []:
        t = str(t).strip().lower()
        if not t:
            continue
        if t.startswith("http"):
            if _slug(p.url.lower()) == _slug(t):
                return True
        elif t in tl:
            return True
    return False


def _apply_filters(products, scfg):
    """Per-store choice of what to track.

    watch_only: true  -> keep only products matching `watch` (URLs/substrings)
    include_any       -> otherwise, keep only titles matching any keyword
    exclude_any       -> always drop matching titles
    """
    watch_only = scfg.get("watch_only")
    watch = scfg.get("watch") or []
    include_any = scfg.get("include_any") or []
    exclude_any = scfg.get("exclude_any") or []
    out = []
    for p in products:
        if watch_only:
            if not _matches(p, watch):
                continue
        elif include_any and not _matches(p, include_any):
            continue
        if exclude_any and _matches(p, exclude_any):
            continue
        out.append(p)
    return out


def run_all(config, state, only_store=None):
    """Poll every enabled store, diff against state, mutate state in place.

    Returns (alerts, summaries). Alerts are dicts consumed by notify.send_alerts.
    """
    alerts, summaries = [], []
    acfg = config.get("alerts") or {}
    realert_s = float(acfg.get("realert_hours", 6)) * 3600
    alert_new = acfg.get("alert_new_products", True)
    failure_alert_after = int(acfg.get("failure_alert_after", 5))
    now = time.time()
    now_iso = _now_iso()

    for name, scfg in (config.get("stores") or {}).items():
        scfg = scfg or {}
        if only_store and name != only_store:
            continue
        if not scfg.get("enabled", True):
            continue
        mod = ADAPTERS.get(name)
        if mod is None:
            summaries.append(f"{name}: FAILED - no adapter with this name")
            continue

        meta = state.setdefault("meta", {}).setdefault(name, {})
        try:
            products = mod.fetch(scfg)
        except Exception as e:
            word = "BLOCKED" if isinstance(e, http.BlockedError) else "FAILED"
            fails = meta.get("consecutive_failures", 0) + 1
            meta["consecutive_failures"] = fails
            summaries.append(f"{name}: {word} - {e} (x{fails})")
            if fails == failure_alert_after:
                alerts.append({
                    "kind": "error",
                    "store": name,
                    "store_label": mod.LABEL,
                    "title": f"{mod.LABEL} monitor has failed {fails} runs in a row",
                    "detail": f"{word}: {e}",
                })
            continue
        meta["consecutive_failures"] = 0
        meta["last_success"] = now_iso
        products = _apply_filters(products, scfg)

        sstate = state.setdefault("stores", {}).setdefault(name, {})
        first_run = not sstate
        seen = set()
        n_restock = n_new = 0

        for p in products:
            seen.add(p.key)
            old = sstate.get(p.key)
            status = p.status or ("In stock" if p.available else "Out of stock")
            rec = {
                "title": p.title,
                "url": p.url,
                "price": p.price,
                "available": p.available,
                "status": status,
                "image": p.image,
                "first_seen": old.get("first_seen", now_iso) if old else now_iso,
                "last_alert": old.get("last_alert", 0) if old else 0,
            }

            kind = None
            if old is None:
                # brand-new listing (often a preorder going live)
                if not first_run and p.available and alert_new:
                    kind = "new"
            elif p.available and not old.get("available"):
                kind = "restock"

            if kind and now - (rec["last_alert"] or 0) >= realert_s:
                rec["last_alert"] = now
                alerts.append({
                    "kind": kind,
                    "store": name,
                    "store_label": mod.LABEL,
                    "title": p.title,
                    "url": p.url,
                    "price": p.price,
                    "status": status,
                    "image": p.image,
                })
                if kind == "restock":
                    n_restock += 1
                else:
                    n_new += 1
            sstate[p.key] = rec

        # Products that vanished from the store's feed: mark unavailable silently,
        # so their reappearance in stock later fires a restock alert.
        if getattr(mod, "FULL_LISTING", True):
            for key, rec in sstate.items():
                if key not in seen and rec.get("available"):
                    rec["available"] = False
                    rec["status"] = "Delisted/unavailable"

        summaries.append(
            f"{name}: {len(products)} products, {n_restock} restock, {n_new} new"
            + (" (first run - seeded, alerts suppressed)" if first_run else "")
        )

    return alerts, summaries
