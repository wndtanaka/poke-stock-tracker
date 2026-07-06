import argparse
import os
import sys

from .config import load_config, load_env
from .engine import run_all
from .notify import send_alerts
from .state import load_state, save_state


def main():
    ap = argparse.ArgumentParser("tracker", description="AU Pokemon TCG restock tracker")
    ap.add_argument("--dry-run", action="store_true", help="print alerts instead of posting to Discord")
    ap.add_argument("--store", help="only run one store (e.g. jbhifi)")
    ap.add_argument("--config", help="path to config.yaml")
    args = ap.parse_args()

    load_env()
    config = load_config(args.config)
    state = load_state()

    alerts, summaries = run_all(config, state, only_store=args.store)

    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if alerts and not webhook and not args.dry_run:
        print("NOTE: DISCORD_WEBHOOK_URL not set — printing alerts instead of posting.")
    try:
        send_alerts(alerts, webhook, dry_run=args.dry_run)
    except Exception as e:
        # Don't save state: the stock transitions stay pending, so the alerts
        # fire again on the next run instead of being lost.
        print(f"ERROR: failed to deliver alerts, state not saved: {e}", file=sys.stderr)
        sys.exit(3)

    save_state(state)
    for line in summaries:
        print(line)

    succeeded = [s for s in summaries if "FAILED" not in s and "BLOCKED" not in s]
    sys.exit(0 if succeeded or not summaries else 2)


if __name__ == "__main__":
    main()
