import os
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_env():
    """Load KEY=VALUE lines from .env (if present) without overriding real env vars."""
    envf = ROOT / ".env"
    if not envf.exists():
        return
    for line in envf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config(path=None):
    p = pathlib.Path(path) if path else ROOT / "config.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
