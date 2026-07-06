import time

from . import http

COLORS = {"restock": 0x2ECC71, "new": 0x3498DB, "error": 0xE74C3C}
EMOJI = {"restock": "🟢", "new": "🆕", "error": "⚠️"}


def _embed(a):
    if a["kind"] == "error":
        return {
            "title": f"⚠️ {a['title']}"[:256],
            "description": a.get("detail", ""),
            "color": COLORS["error"],
        }
    price = f"${a['price']:.2f}" if a.get("price") else "price n/a"
    desc = f"**{a['store_label']}** · {price}"
    if a.get("status") and a["status"] != "In stock":
        desc += f" · {a['status']}"
    e = {
        "title": f"{EMOJI[a['kind']]} {a['title']}"[:256],
        "url": a.get("url"),
        "description": desc,
        "color": COLORS[a["kind"]],
        "footer": {"text": "poke-restock-tracker"},
    }
    if a.get("image"):
        e["thumbnail"] = {"url": a["image"]}
    return e


def send_alerts(alerts, webhook, dry_run=False):
    if not alerts:
        return
    if dry_run or not webhook:
        for a in alerts:
            price = f"${a['price']:.2f}" if a.get("price") else "?"
            print(f"[{a['kind'].upper()}] {a.get('store_label', '')} | {a['title']} | {price} | {a.get('url', '')}")
        return
    embeds = [_embed(a) for a in alerts]
    for i in range(0, len(embeds), 10):  # Discord: max 10 embeds per message
        _post(webhook, {"username": "Restock Radar", "embeds": embeds[i:i + 10]})
        if i + 10 < len(embeds):
            time.sleep(1)


def _post(webhook, payload):
    for attempt in range(4):
        r = http.post_json(webhook, payload)
        if r.status_code == 429:
            try:
                delay = float(r.json().get("retry_after", 2))
            except Exception:
                delay = 2.0
            time.sleep(min(delay, 10) + 0.5)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Discord webhook HTTP {r.status_code}: {r.text[:200]}")
        return
    raise RuntimeError("Discord webhook kept rate-limiting (429) after 4 attempts")
