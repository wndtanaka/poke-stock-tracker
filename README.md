# poke-restock-tracker

Polls Australian retailers for Pokemon TCG sealed-product stock and posts Discord
alerts when something comes (back) in stock or a new listing appears. Runs for free
on GitHub Actions; state lives in `state/stock.json`, committed back by the workflow,
so alerts only fire on out-of-stock → in-stock *transitions*.

## Stores

| Store | Method | Reliability |
|---|---|---|
| JB Hi-Fi | Shopify `suggest.json` + per-product `.js` (clean JSON) | 🟢 solid |
| Toymate | Fast Simon search API (the site's own backend, clean JSON) | 🟢 solid |
| Amazon AU | Product-page scrape per ASIN | 🟡 works from residential IPs; GitHub's datacentre IPs may get bot-walled — the tracker detects this and reports it rather than false-alerting |
| EB Games | — | 🔴 hard tier (Cloudflare managed challenge); not in v1. Same bucket as Kmart / Target / Big W |

## Setup

1. **Discord webhook**: Server Settings → Integrations → Webhooks → New Webhook →
   pick your alerts channel → Copy Webhook URL.
2. **GitHub**: push this repo, then add the webhook as a secret:
   Settings → Secrets and variables → Actions → New repository secret →
   name `DISCORD_WEBHOOK_URL`, value = the URL.
3. Actions run on the schedule in [.github/workflows/track.yml](.github/workflows/track.yml).
   Trigger one manually (Actions → track → Run workflow) to seed the state —
   the first run records everything without alerting.

**Cost note**: on a **public** repo, Actions minutes are unlimited (free). On a
**private** repo the free tier is 2,000 min/month — this schedule (~220 runs/day)
exceeds that, so either make the repo public or stretch the crons to `*/20` and `0,30`.

## Local runs

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # (bin/pip on mac/linux)
.venv/Scripts/python -m tracker --dry-run       # print alerts instead of posting
```

Put `DISCORD_WEBHOOK_URL=...` in `.env` (see `.env.example`) to post for real.
`--store jbhifi` runs a single store. Local and CI runs share state via git.

## Watching new products

- **New sets on Amazon**: add the ASIN (from the product URL `/dp/ASIN`) to
  `amazon_au.asins` in [config.yaml](config.yaml).
- **Specific JB products**: add the handle from `jbhifi.com.au/products/<handle>`
  to `jbhifi.watch_handles`. Keyword queries usually find everything anyway.
- Alert tuning (cooldown, new-listing alerts) is at the top of config.yaml.

## How alerting behaves

- First run per store seeds state silently (no alert blast).
- `restock` = product was unavailable (or delisted) and is now buyable; `new` =
  first time a matching product is seen listed and buyable.
- A product disappearing from a store's results is treated as going out of stock
  (silently), so its return fires a restock alert.
- Per-product cooldown (`realert_hours`) stops flapping stock from spamming.
- If a store fails/blocks 5 runs in a row you get one ⚠️ Discord warning.

## Roadmap / hard tier

EB Games, Kmart, Target and Big W all sit behind serious bot protection
(Cloudflare/Akamai). Realistic options, in order of effort: run this same tracker
on a home machine (residential IP) for just those stores; headless browser with
challenge solving; paid residential proxies. Revisit once v1 has proven useful.
