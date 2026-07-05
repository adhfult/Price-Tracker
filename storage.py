"""
JSON-based persistence layer with optional SQLite backend.

Backend selection:
  STORAGE_BACKEND=json   (default) → stores data/items.json + data/config.json
  STORAGE_BACKEND=sqlite            → stores data/tracker.db (SQLite)

SQLite adds a price_history table for historical price tracking.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models.amazon import TrackedItem, AlertCriteria, AlertType

DATA_DIR    = Path(__file__).parent / "data"
ITEMS_FILE  = DATA_DIR / "items.json"
CONFIG_FILE = DATA_DIR / "config.json"
DB_FILE     = DATA_DIR / "tracker.db"

DEFAULT_CONFIG = {
    "currency": None,
    "location": None,
    "check_interval_minutes": 60,
}

_BACKEND = os.getenv("STORAGE_BACKEND", "json").lower()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _criteria_to_dict(c: AlertCriteria) -> dict:
    return {
        "alert_type":   c.alert_type.value,
        "target_price": c.target_price,
        "min_price":    c.min_price,
        "max_price":    c.max_price,
        "drop_amount":  c.drop_amount,
        "drop_percent": c.drop_percent,
    }


def _criteria_from_dict(d: dict) -> AlertCriteria:
    return AlertCriteria(
        alert_type   = AlertType(d["alert_type"]),
        target_price = d.get("target_price"),
        min_price    = d.get("min_price"),
        max_price    = d.get("max_price"),
        drop_amount  = d.get("drop_amount"),
        drop_percent = d.get("drop_percent"),
    )


def _item_to_dict(item: TrackedItem) -> dict:
    return {
        "id":                    item.id,
        "url":                   item.url,
        "title":                 item.title,
        "asin":                  item.asin,
        "currency":              item.currency,
        "location":              item.location,
        "selected_variants":     item.selected_variants,
        "last_price":            item.last_price,
        "last_original_price":   item.last_original_price,
        "last_prime_price":      item.last_prime_price,
        "last_discount_percent": item.last_discount_percent,
        "baseline_price":        item.baseline_price,
        "is_prime_eligible":     item.is_prime_eligible,
        "in_stock":              item.in_stock,
        "date_added":            item.date_added,
        "last_checked":          item.last_checked,
        "alert_triggered":       item.alert_triggered,
        "alert_criteria":        _criteria_to_dict(item.alert_criteria),
    }


def _item_from_dict(d: dict) -> TrackedItem:
    return TrackedItem(
        id                    = d["id"],
        url                   = d["url"],
        title                 = d["title"],
        asin                  = d["asin"],
        currency              = d["currency"],
        location              = d["location"],
        alert_criteria        = _criteria_from_dict(d["alert_criteria"]),
        selected_variants     = d.get("selected_variants", {}),
        last_price            = d.get("last_price"),
        last_original_price   = d.get("last_original_price"),
        last_prime_price      = d.get("last_prime_price"),
        last_discount_percent = d.get("last_discount_percent"),
        baseline_price        = d.get("baseline_price"),
        is_prime_eligible     = d.get("is_prime_eligible", False),
        in_stock              = d.get("in_stock", True),
        date_added            = d.get("date_added", ""),
        last_checked          = d.get("last_checked", ""),
        alert_triggered       = d.get("alert_triggered", False),
    )


# ── SQLite helpers ────────────────────────────────────────────────────────────

def _db_connect() -> sqlite3.Connection:
    _ensure()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _db_init():
    """Create tables if they do not exist."""
    with _db_connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id                    TEXT PRIMARY KEY,
                url                   TEXT NOT NULL,
                title                 TEXT,
                asin                  TEXT,
                currency              TEXT,
                location              TEXT,
                selected_variants     TEXT DEFAULT '{}',
                last_price            REAL,
                last_original_price   REAL,
                last_prime_price      REAL,
                last_discount_percent REAL,
                baseline_price        REAL,
                is_prime_eligible     INTEGER DEFAULT 0,
                in_stock              INTEGER DEFAULT 1,
                date_added            TEXT,
                last_checked          TEXT,
                alert_triggered       INTEGER DEFAULT 0,
                alert_criteria        TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id     TEXT NOT NULL,
                asin        TEXT,
                price       REAL,
                prime_price REAL,
                in_stock    INTEGER DEFAULT 1,
                checked_at  TEXT NOT NULL,
                FOREIGN KEY(item_id) REFERENCES items(id)
            );

            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)


# ── Public API — Config ───────────────────────────────────────────────────────

def load_config() -> dict:
    _ensure()
    if _BACKEND == "sqlite":
        _db_init()
        with _db_connect() as conn:
            rows = conn.execute("SELECT key, value FROM config").fetchall()
            cfg  = {r["key"]: r["value"] for r in rows}
        return {**DEFAULT_CONFIG, **cfg}
    # JSON backend
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    _ensure()
    if _BACKEND == "sqlite":
        _db_init()
        with _db_connect() as conn:
            for k, v in config.items():
                conn.execute(
                    "INSERT INTO config(key, value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (k, str(v) if v is not None else None),
                )
        return
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


# ── Public API — Items ────────────────────────────────────────────────────────

def load_items() -> List[TrackedItem]:
    _ensure()
    if _BACKEND == "sqlite":
        _db_init()
        with _db_connect() as conn:
            rows = conn.execute("SELECT * FROM items").fetchall()
        items = []
        for r in rows:
            d = dict(r)
            d["selected_variants"] = json.loads(d["selected_variants"] or "{}")
            d["alert_criteria"]    = json.loads(d["alert_criteria"])
            d["is_prime_eligible"] = bool(d["is_prime_eligible"])
            d["in_stock"]          = bool(d["in_stock"])
            d["alert_triggered"]   = bool(d["alert_triggered"])
            items.append(_item_from_dict(d))
        return items
    if not ITEMS_FILE.exists():
        return []
    with open(ITEMS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [_item_from_dict(d) for d in raw]


def _save_items_json(items: List[TrackedItem]):
    _ensure()
    with open(ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump([_item_to_dict(i) for i in items], f, indent=2, ensure_ascii=False)


def add_item(item: TrackedItem):
    if _BACKEND == "sqlite":
        _db_init()
        d = _item_to_dict(item)
        with _db_connect() as conn:
            conn.execute(
                """INSERT INTO items VALUES (
                    :id,:url,:title,:asin,:currency,:location,
                    :selected_variants,:last_price,:last_original_price,
                    :last_prime_price,:last_discount_percent,:baseline_price,
                    :is_prime_eligible,:in_stock,:date_added,:last_checked,
                    :alert_triggered,:alert_criteria
                )""",
                {**d,
                 "selected_variants": json.dumps(d["selected_variants"]),
                 "alert_criteria":    json.dumps(d["alert_criteria"]),
                 "is_prime_eligible": int(d["is_prime_eligible"]),
                 "in_stock":          int(d["in_stock"]),
                 "alert_triggered":   int(d["alert_triggered"])},
            )
        return
    items = load_items()
    items.append(item)
    _save_items_json(items)


def remove_item(item_id: str) -> bool:
    if _BACKEND == "sqlite":
        _db_init()
        with _db_connect() as conn:
            cur = conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        return cur.rowcount > 0
    items    = load_items()
    filtered = [i for i in items if i.id != item_id]
    if len(filtered) == len(items):
        return False
    _save_items_json(filtered)
    return True


def update_item(updated: TrackedItem):
    if _BACKEND == "sqlite":
        _db_init()
        d = _item_to_dict(updated)
        with _db_connect() as conn:
            conn.execute(
                """UPDATE items SET
                    url=:url, title=:title, asin=:asin, currency=:currency,
                    location=:location, selected_variants=:selected_variants,
                    last_price=:last_price, last_original_price=:last_original_price,
                    last_prime_price=:last_prime_price,
                    last_discount_percent=:last_discount_percent,
                    baseline_price=:baseline_price,
                    is_prime_eligible=:is_prime_eligible, in_stock=:in_stock,
                    date_added=:date_added, last_checked=:last_checked,
                    alert_triggered=:alert_triggered, alert_criteria=:alert_criteria
                WHERE id=:id""",
                {**d,
                 "selected_variants": json.dumps(d["selected_variants"]),
                 "alert_criteria":    json.dumps(d["alert_criteria"]),
                 "is_prime_eligible": int(d["is_prime_eligible"]),
                 "in_stock":          int(d["in_stock"]),
                 "alert_triggered":   int(d["alert_triggered"])},
            )
        return
    items = load_items()
    for idx, item in enumerate(items):
        if item.id == updated.id:
            items[idx] = updated
            break
    _save_items_json(items)


# ── Price history (SQLite only) ───────────────────────────────────────────────

def append_price_history(
    item_id:    str,
    asin:       str,
    price:      Optional[float],
    prime_price: Optional[float],
    in_stock:   bool,
):
    """
    Append a price snapshot to the history table.
    Only available when STORAGE_BACKEND=sqlite.
    Silently no-ops for the JSON backend.
    """
    if _BACKEND != "sqlite":
        return
    _db_init()
    with _db_connect() as conn:
        conn.execute(
            "INSERT INTO price_history(item_id,asin,price,prime_price,in_stock,checked_at) "
            "VALUES(?,?,?,?,?,?)",
            (item_id, asin, price, prime_price, int(in_stock), datetime.utcnow().isoformat()),
        )


def load_price_history(item_id: str, limit: int = 90) -> List[dict]:
    """
    Return the last `limit` price history records for an item.
    Returns [] for the JSON backend.
    """
    if _BACKEND != "sqlite":
        return []
    _db_init()
    with _db_connect() as conn:
        rows = conn.execute(
            "SELECT * FROM price_history WHERE item_id=? ORDER BY checked_at DESC LIMIT ?",
            (item_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
