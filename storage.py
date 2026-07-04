"""JSON-based persistence layer for config and tracked items."""

import json
from pathlib import Path
from typing import List

from models import TrackedItem, AlertCriteria, AlertType

DATA_DIR   = Path(__file__).parent / "data"
ITEMS_FILE = DATA_DIR / "items.json"
CONFIG_FILE = DATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "currency": None,
    "location": None,
    "check_interval_minutes": 60,
}


# ── internal helpers ──────────────────────────────────────────────────────────

def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _criteria_to_dict(c: AlertCriteria) -> dict:
    return {
        "alert_type":    c.alert_type.value,
        "target_price":  c.target_price,
        "min_price":     c.min_price,
        "max_price":     c.max_price,
        "drop_amount":   c.drop_amount,
        "drop_percent":  c.drop_percent,
    }


def _criteria_from_dict(d: dict) -> AlertCriteria:
    return AlertCriteria(
        alert_type    = AlertType(d["alert_type"]),
        target_price  = d.get("target_price"),
        min_price     = d.get("min_price"),
        max_price     = d.get("max_price"),
        drop_amount   = d.get("drop_amount"),
        drop_percent  = d.get("drop_percent"),
    )


def _item_to_dict(item: TrackedItem) -> dict:
    return {
        "id":                   item.id,
        "url":                  item.url,
        "title":                item.title,
        "asin":                 item.asin,
        "currency":             item.currency,
        "location":             item.location,
        "selected_variants":    item.selected_variants,
        "last_price":           item.last_price,
        "last_original_price":  item.last_original_price,
        "last_prime_price":     item.last_prime_price,
        "last_discount_percent": item.last_discount_percent,
        "baseline_price":       item.baseline_price,
        "is_prime_eligible":    item.is_prime_eligible,
        "in_stock":             item.in_stock,
        "date_added":           item.date_added,
        "last_checked":         item.last_checked,
        "alert_triggered":      item.alert_triggered,
        "alert_criteria":       _criteria_to_dict(item.alert_criteria),
    }


def _item_from_dict(d: dict) -> TrackedItem:
    return TrackedItem(
        id                   = d["id"],
        url                  = d["url"],
        title                = d["title"],
        asin                 = d["asin"],
        currency             = d["currency"],
        location             = d["location"],
        alert_criteria       = _criteria_from_dict(d["alert_criteria"]),
        selected_variants    = d.get("selected_variants", {}),
        last_price           = d.get("last_price"),
        last_original_price  = d.get("last_original_price"),
        last_prime_price     = d.get("last_prime_price"),
        last_discount_percent = d.get("last_discount_percent"),
        baseline_price       = d.get("baseline_price"),
        is_prime_eligible    = d.get("is_prime_eligible", False),
        in_stock             = d.get("in_stock", True),
        date_added           = d.get("date_added", ""),
        last_checked         = d.get("last_checked", ""),
        alert_triggered      = d.get("alert_triggered", False),
    )


# ── public API ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    _ensure()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    _ensure()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_items() -> List[TrackedItem]:
    _ensure()
    if not ITEMS_FILE.exists():
        return []
    with open(ITEMS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [_item_from_dict(d) for d in raw]


def save_items(items: List[TrackedItem]):
    _ensure()
    with open(ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump([_item_to_dict(i) for i in items], f, indent=2, ensure_ascii=False)


def add_item(item: TrackedItem):
    items = load_items()
    items.append(item)
    save_items(items)


def remove_item(item_id: str) -> bool:
    items = load_items()
    filtered = [i for i in items if i.id != item_id]
    if len(filtered) == len(items):
        return False
    save_items(filtered)
    return True


def update_item(updated: TrackedItem):
    items = load_items()
    for idx, item in enumerate(items):
        if item.id == updated.id:
            items[idx] = updated
            break
    save_items(items)
