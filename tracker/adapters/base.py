from dataclasses import dataclass


@dataclass
class Product:
    key: str            # stable id within the store (handle / product id / asin)
    title: str
    url: str
    available: bool
    price: float | None = None
    status: str = ""    # optional label, e.g. "Pre-order"
    image: str | None = None


def to_float(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except ValueError:
        return None
