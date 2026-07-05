"""
Amazon Price Tracker – CLI entry point.

Run:
    python main.py

First launch triggers a one-time setup wizard (currency + location).
Tracked items and settings are stored in  ./data/  as JSON files.
"""

import sys
import re
import uuid
import time
from datetime import datetime
from typing import Optional, List, Tuple

import schedule
from colorama import Fore, Style, init as _init

from models.amazon import TrackedItem, AlertCriteria, AlertType
import storage
import scrapers.amazon as scraper
import notifier

_init(autoreset=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Low-level UI helpers
# ══════════════════════════════════════════════════════════════════════════════

def _hr(title: str = ""):
    width = 66
    print(f"\n{Fore.CYAN}{'─' * width}")
    if title:
        print(f"{Fore.CYAN}  {title}")
        print(f"{Fore.CYAN}{'─' * width}{Style.RESET_ALL}")
    else:
        print(Style.RESET_ALL, end="")


def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    ans = input(f"{Fore.WHITE}{prompt}{hint}: {Style.RESET_ALL}").strip()
    return ans if ans else default


def _ask_int(prompt: str, lo: int = 1, hi: int = 9999,
             default: Optional[int] = None) -> int:
    while True:
        raw = _ask(prompt, str(default) if default is not None else "")
        if raw.lstrip("-").isdigit():
            v = int(raw)
            if lo <= v <= hi:
                return v
        print(f"{Fore.RED}  Enter a whole number between {lo} and {hi}.{Style.RESET_ALL}")


def _ask_float(prompt: str) -> float:
    while True:
        raw = _ask(prompt).replace(",", ".")
        try:
            v = float(raw)
            if v > 0:
                return v
        except ValueError:
            pass
        print(f"{Fore.RED}  Enter a valid positive number.{Style.RESET_ALL}")


def _menu(options: List[str], prompt: str = "Choose") -> int:
    """Print numbered list and return 0-based index of chosen option."""
    for i, opt in enumerate(options, 1):
        print(f"  {Fore.YELLOW}{i}{Style.RESET_ALL}. {opt}")
    while True:
        raw = _ask(prompt)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"{Fore.RED}  Pick a number 1–{len(options)}.{Style.RESET_ALL}")


# ══════════════════════════════════════════════════════════════════════════════
#  Formatting helpers
# ══════════════════════════════════════════════════════════════════════════════

def _fmt(amount: Optional[float], currency: str) -> str:
    return notifier.fmt_price(amount, currency)


def _sym(currency: str) -> str:
    return notifier.get_symbol(currency)


def _describe_criteria(c: AlertCriteria, currency: str) -> str:
    s = _sym(currency)
    t = c.alert_type
    if t == AlertType.BELOW_PRICE:
        return f"Price drops below {s}{c.target_price:,.2f}"
    if t == AlertType.IN_RANGE:
        return f"Price enters {s}{c.min_price:,.2f} – {s}{c.max_price:,.2f}"
    if t == AlertType.ANY_DROP:
        return "Any price drop"
    if t == AlertType.DROP_BY_AMOUNT:
        return f"Price drops by ≥ {s}{c.drop_amount:,.2f}"
    if t == AlertType.DROP_BY_PERCENT:
        return f"Price drops by ≥ {c.drop_percent:.1f}%"
    return "Unknown"


# ══════════════════════════════════════════════════════════════════════════════
#  Alert logic
# ══════════════════════════════════════════════════════════════════════════════

def _effective_price(price: Optional[float],
                     prime: Optional[float]) -> Optional[float]:
    candidates = [p for p in (price, prime) if p is not None]
    return min(candidates) if candidates else None


def _check_criteria(item: TrackedItem, current: float,
                    prev: Optional[float]) -> Tuple[bool, str]:
    """
    Evaluate alert criteria.  `prev` is the price from the PREVIOUS check
    (before updating item.last_price), used only for ANY_DROP comparisons.
    """
    s = _sym(item.currency)
    c = item.alert_criteria
    t = c.alert_type

    if t == AlertType.BELOW_PRICE:
        if current <= c.target_price:
            return True, (
                f"Price {s}{current:,.2f} reached target "
                f"≤ {s}{c.target_price:,.2f}"
            )

    elif t == AlertType.IN_RANGE:
        if c.min_price <= current <= c.max_price:
            return True, (
                f"Price {s}{current:,.2f} is within "
                f"{s}{c.min_price:,.2f} – {s}{c.max_price:,.2f}"
            )

    elif t == AlertType.ANY_DROP:
        compare_to = prev if prev is not None else item.baseline_price
        if compare_to is not None and current < compare_to:
            diff = compare_to - current
            return True, (
                f"Price dropped {s}{diff:,.2f} "
                f"(from {s}{compare_to:,.2f} → {s}{current:,.2f})"
            )

    elif t == AlertType.DROP_BY_AMOUNT:
        base = item.baseline_price
        if base is not None and (base - current) >= c.drop_amount:
            return True, (
                f"Dropped {s}{base - current:,.2f} from baseline "
                f"{s}{base:,.2f} → {s}{current:,.2f}"
            )

    elif t == AlertType.DROP_BY_PERCENT:
        base = item.baseline_price
        if base and base > 0:
            pct = (base - current) / base * 100
            if pct >= c.drop_percent:
                return True, (
                    f"Dropped {pct:.1f}% from baseline "
                    f"{s}{base:,.2f} → {s}{current:,.2f}"
                )

    return False, ""


def _auto_reset(item: TrackedItem, current: float) -> bool:
    """
    Return True (and mark the item) if the alert should auto-reset because
    the price has moved back outside the trigger zone.
    This allows re-alerting if the price dips below target again later.
    """
    if not item.alert_triggered:
        return False
    c = item.alert_criteria
    t = c.alert_type
    reset = False
    if t == AlertType.BELOW_PRICE and current > c.target_price:
        reset = True
    elif t == AlertType.IN_RANGE and not (c.min_price <= current <= c.max_price):
        reset = True
    if reset:
        item.alert_triggered = False
    return reset


# ══════════════════════════════════════════════════════════════════════════════
#  Setup wizard
# ══════════════════════════════════════════════════════════════════════════════

def _setup_wizard() -> dict:
    _hr("First-Time Setup")
    print("Welcome to Amazon Price Tracker!\n")

    print("Enter your currency code (ISO 4217, e.g. USD / EUR / GBP / JPY):")
    currency = _ask("Currency code").upper()
    while len(currency) < 2 or not currency.isalpha():
        print(f"{Fore.RED}  Use 2-4 capital letters, e.g. USD{Style.RESET_ALL}")
        currency = _ask("Currency code").upper()

    print("\nEnter your location (city + country/state, used for context):")
    print("  e.g.  Seattle, WA   |   London, UK   |   Toronto, ON")
    location = _ask("Location")
    while len(location) < 2:
        location = _ask("Location")

    interval = _ask_int(
        "Check prices every N minutes (minimum 5)", lo=5, hi=1440, default=60
    )

    cfg = {"currency": currency, "location": location,
           "check_interval_minutes": interval}
    storage.save_config(cfg)
    notifier.ok(f"Setup saved!  Currency={currency}  Location={location}  "
                f"Interval={interval} min")
    return cfg


# ══════════════════════════════════════════════════════════════════════════════
#  Add item flow
# ══════════════════════════════════════════════════════════════════════════════

def _pick_variants(variant_groups: list, currency: str) -> dict:
    """Walk the user through each variant group; return {group_name: option_dict}."""
    chosen = {}
    for grp in variant_groups:
        gname   = grp["group_name"]
        options = grp["options"]
        print(f"\n  {Fore.CYAN}Select {gname}:{Style.RESET_ALL}")
        labels = []
        for opt in options:
            avail_tag = "" if opt["available"] else f"  {Fore.RED}[unavailable]{Style.RESET_ALL}"
            # Show snapshot price inline for condition tiers so the user can compare
            price_tag = ""
            if opt.get("price") is not None:
                price_tag = f"  ({_fmt(opt['price'], currency)})"
            labels.append(f"{opt['name']}{price_tag}{avail_tag}")
        idx = _menu(labels, f"  Choose {gname}")
        chosen[gname] = options[idx]
    return chosen


def _build_criteria(currency: str) -> AlertCriteria:
    s = _sym(currency)
    _hr("Set Alert Criteria")
    idx = _menu([
        f"Drop to a specific price  (e.g. below {s}50)",
        f"Enter a price range       (e.g. {s}20 – {s}30)",
        "Any price drop",
        f"Drop by a fixed amount    (e.g. {s}10 off baseline)",
        "Drop by a percentage      (e.g. 20% off baseline)",
    ], "Alert type")

    if idx == 0:
        tp = _ask_float(f"  Alert when price drops below ({s})")
        return AlertCriteria(AlertType.BELOW_PRICE, target_price=tp)
    if idx == 1:
        lo = _ask_float(f"  Minimum of range ({s})")
        hi = _ask_float(f"  Maximum of range ({s})")
        if lo > hi:
            lo, hi = hi, lo
        return AlertCriteria(AlertType.IN_RANGE, min_price=lo, max_price=hi)
    if idx == 2:
        return AlertCriteria(AlertType.ANY_DROP)
    if idx == 3:
        amt = _ask_float(f"  Drop by at least ({s})")
        return AlertCriteria(AlertType.DROP_BY_AMOUNT, drop_amount=amt)
    pct = _ask_float("  Drop by at least (%)")
    return AlertCriteria(AlertType.DROP_BY_PERCENT, drop_percent=pct)


def add_item_flow(cfg: dict):
    _hr("Add New Item to Track")

    url = _ask("Amazon product URL").strip()
    if not scraper.is_valid_amazon_url(url):
        notifier.error("That doesn't look like an Amazon URL.")
        return

    print(f"\n{Fore.CYAN}Fetching product details – please wait...{Style.RESET_ALL}")
    try:
        details = scraper.get_product_details(url)
    except Exception as exc:
        notifier.error(str(exc))
        return

    # ── show summary ──────────────────────────────────────────────────────────
    currency = cfg["currency"]
    print(f"\n  {Fore.GREEN}Found:{Style.RESET_ALL} {details['title']}")
    print(f"  Current price  : {Fore.YELLOW}{_fmt(details['price'], currency)}")
    if details["original_price"]:
        print(f"  Original price : {Style.RESET_ALL}{_fmt(details['original_price'], currency)}")
    if details["discount_percent"]:
        print(f"  Discount       : {Fore.GREEN}{details['discount_percent']:.0f}% off")
    if details["prime_price"]:
        print(f"  Prime price    : {Fore.CYAN}{_fmt(details['prime_price'], currency)}")
    if details["is_prime_eligible"]:
        print(f"  {Fore.CYAN}✓ Prime eligible")
    if not details["in_stock"]:
        print(f"  {Fore.RED}⚠ Currently out of stock")

    confirm = _ask("\nIs this the correct product? (y/n)", default="y").lower()
    if confirm != "y":
        print("Cancelled.")
        return

    # ── variant selection ─────────────────────────────────────────────────────
    tracking_url    = details["normalized_url"]
    selected_labels: dict = {}   # {group_name: display_name}

    if details["variants"]:
        print(f"\n{Fore.CYAN}This product has variants. "
              f"Select which one to track:{Style.RESET_ALL}")
        chosen = _pick_variants(details["variants"], currency)

        for gname, opt in chosen.items():
            selected_labels[gname] = opt["name"]
            # Prefer the variant-specific URL if available
            if opt.get("url") and opt["url"].startswith("http"):
                tracking_url = opt["url"]
            elif re.match(r"^[A-Z0-9]{10}$", opt.get("asin", "")):
                base = scraper._amazon_base(details["url"])
                tracking_url = f"{base}/dp/{opt['asin']}"

        if selected_labels:
            label_str = ", ".join(f"{k}: {v}" for k, v in selected_labels.items())
            print(f"\n  Tracking variant: {Fore.YELLOW}{label_str}{Style.RESET_ALL}")
        else:
            print(f"\n  {Fore.YELLOW}Note:{Style.RESET_ALL} selected variant has no "
                  "dedicated ASIN; tracking the base product URL.")
    else:
        print(f"\n{Fore.CYAN}No variants found – tracking the base product.{Style.RESET_ALL}")

    # ── alert criteria ────────────────────────────────────────────────────────
    criteria = _build_criteria(currency)
    effective = _effective_price(details["price"], details["prime_price"])

    item = TrackedItem(
        id                  = str(uuid.uuid4()),
        url                 = tracking_url,
        title               = details["title"],
        asin                = details["asin"],
        currency            = currency,
        location            = cfg["location"],
        alert_criteria      = criteria,
        selected_variants   = selected_labels,
        last_price          = effective,
        last_original_price = details["original_price"],
        last_prime_price    = details["prime_price"],
        last_discount_percent = details["discount_percent"],
        baseline_price      = effective,   # anchors relative drop checks
        is_prime_eligible   = details["is_prime_eligible"],
        in_stock            = details["in_stock"],
        date_added          = datetime.now().isoformat(),
        last_checked        = datetime.now().isoformat(),
    )
    storage.add_item(item)
    notifier.ok(f'"{item.title[:60]}" added.')
    print(f"  Alert: {_describe_criteria(criteria, currency)}")


# ══════════════════════════════════════════════════════════════════════════════
#  Price checking
# ══════════════════════════════════════════════════════════════════════════════

def _check_one(item: TrackedItem, cfg: dict) -> TrackedItem:
    """Fetch current price, evaluate alert, update storage. Returns updated item."""
    print(f"  Checking: {item.title[:55]}...")
    sys.stdout.flush()

    condition = item.selected_variants.get("Condition")
    try:
        info = scraper.get_current_price(item.url, condition=condition)
    except Exception as exc:
        notifier.error(f"  Failed: {exc}")
        return item

    effective = _effective_price(info["price"], info["prime_price"])
    if effective is None:
        notifier.warn(f"  Could not read price for '{item.title[:40]}'")
        item.last_checked = datetime.now().isoformat()
        storage.update_item(item)
        return item

    prev_price   = item.last_price   # snapshot BEFORE we overwrite it
    currency     = item.currency
    s            = _sym(currency)

    # ── display price movement ────────────────────────────────────────────────
    if prev_price is not None and prev_price != effective:
        diff  = effective - prev_price
        arrow = f"{Fore.GREEN}▼" if diff < 0 else f"{Fore.RED}▲"
        print(f"  {Fore.YELLOW}{item.title[:45]}{Style.RESET_ALL}")
        print(f"    {_fmt(effective, currency)}  "
              f"{arrow} {s}{abs(diff):.2f}{Style.RESET_ALL}")
    else:
        print(f"  {Fore.YELLOW}{item.title[:45]}{Style.RESET_ALL}  →  "
              f"{_fmt(effective, currency)}")
    sys.stdout.flush()

    # ── update item fields ────────────────────────────────────────────────────
    item.last_price           = effective
    item.last_original_price  = info["original_price"]
    item.last_prime_price     = info["prime_price"]
    item.last_discount_percent = info["discount_percent"]
    item.is_prime_eligible    = info["is_prime_eligible"]
    item.in_stock             = info["in_stock"]
    item.last_checked         = datetime.now().isoformat()

    # Auto-reset for BELOW_PRICE / IN_RANGE if price moved back outside zone
    _auto_reset(item, effective)

    # ── evaluate alert ────────────────────────────────────────────────────────
    if not item.alert_triggered:
        fired, desc = _check_criteria(item, effective, prev_price)
        if fired:
            item.alert_triggered = True
            storage.update_item(item)
            notifier.send_alert(
                item_title     = item.title,
                currency       = currency,
                current_price  = effective,
                criteria_desc  = desc,
                url            = item.url,
                original_price = info["original_price"],
                prime_price    = info["prime_price"],
            )
            return item

    storage.update_item(item)
    return item


def check_all(cfg: dict):
    items = storage.load_items()
    if not items:
        print(f"  {Fore.YELLOW}No items tracked yet.{Style.RESET_ALL}")
        sys.stdout.flush()
        return
    _hr(f"Checking {len(items)} item(s)")
    for i, item in enumerate(items, 1):
        _check_one(item, cfg)
        if i < len(items):
            time.sleep(3)   # polite pause between requests
    print(f"\n{Fore.GREEN}Done.{Style.RESET_ALL}")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  View / manage items
# ══════════════════════════════════════════════════════════════════════════════

def _show_item_row(n: int, item: TrackedItem):
    currency   = item.currency
    price_str  = _fmt(item.last_price, currency) if item.last_price else "—"
    var_str    = ""
    if item.selected_variants:
        var_str = "  (" + ", ".join(f"{k}: {v}"
                                    for k, v in item.selected_variants.items()) + ")"
    stock_tag  = f"  {Fore.RED}[OUT OF STOCK]{Style.RESET_ALL}" if not item.in_stock else ""
    alert_tag  = f"  {Fore.GREEN}[ALERT!]{Style.RESET_ALL}"    if item.alert_triggered else ""

    print(f"\n  {Fore.YELLOW}{n}.{Style.RESET_ALL} {item.title[:55]}{var_str}")
    print(f"     Price  : {Fore.YELLOW}{price_str}{Style.RESET_ALL}{stock_tag}{alert_tag}")
    print(f"     Alert  : {_describe_criteria(item.alert_criteria, currency)}")
    if item.last_checked:
        ts = item.last_checked[:16].replace("T", " ")
        print(f"     Checked: {ts}")


def _item_actions(item: TrackedItem, cfg: dict):
    while True:
        _hr(f"Managing: {item.title[:52]}")
        print(f"  Current price   : {_fmt(item.last_price, item.currency)}")
        if item.selected_variants:
            var_str = ", ".join(f"{k}: {v}" for k, v in item.selected_variants.items())
            print(f"  Variant         : {var_str}")
        print(f"  Alert criteria  : {_describe_criteria(item.alert_criteria, item.currency)}")
        print(f"  URL             : {item.url[:72]}")
        print()

        idx = _menu([
            "Check price now",
            "Edit alert criteria",
            "Reset alert (re-arm for next trigger)",
            "Remove this item",
            "Back",
        ], "Action")

        if idx == 0:
            _check_one(item, cfg)
            return   # return to list (which reloads from disk)

        elif idx == 1:
            item.alert_criteria = _build_criteria(item.currency)
            item.baseline_price = item.last_price   # new baseline
            item.alert_triggered = False
            storage.update_item(item)
            notifier.ok("Alert criteria updated.")

        elif idx == 2:
            item.alert_triggered = False
            storage.update_item(item)
            notifier.ok("Alert re-armed.")

        elif idx == 3:
            confirm = _ask(f'Remove "{item.title[:40]}"? (y/n)', default="n").lower()
            if confirm == "y":
                storage.remove_item(item.id)
                notifier.ok("Item removed.")
                return

        elif idx == 4:
            return


def view_items_menu(cfg: dict):
    while True:
        _hr("Tracked Items")
        items = storage.load_items()

        if not items:
            print(f"  {Fore.YELLOW}No items tracked yet."
                  f"  Add one from the main menu.{Style.RESET_ALL}")
            input("\n  Press Enter to return...")
            return

        for i, item in enumerate(items, 1):
            _show_item_row(i, item)

        print(f"\n  {Fore.YELLOW}0{Style.RESET_ALL}. Back")
        choice = _ask("\nItem number to manage (or 0 to go back)")

        if choice == "0":
            return
        if choice.isdigit() and 0 < int(choice) <= len(items):
            _item_actions(items[int(choice) - 1], cfg)
        else:
            print(f"{Fore.RED}  Invalid selection.{Style.RESET_ALL}")


# ══════════════════════════════════════════════════════════════════════════════
#  Monitoring loop
# ══════════════════════════════════════════════════════════════════════════════

def run_monitor(cfg: dict):
    global _monitoring_stop
    _monitoring_stop = False
    
    interval = cfg.get("check_interval_minutes", 60)
    _hr("Price Monitor")
    print(f"  Checking every {interval} minute(s).  Press Ctrl+C to stop.\n")
    sys.stdout.flush()

    try:
        check_all(cfg)   # immediate first run

        schedule.every(interval).minutes.do(check_all, cfg=cfg)
        while True:
            schedule.run_pending()
            time.sleep(0.5)  # More responsive to Ctrl+C
    except KeyboardInterrupt:
        pass
    finally:
        schedule.clear()
        print(f"\n{Fore.YELLOW}Monitoring stopped.{Style.RESET_ALL}")
        sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  Settings
# ══════════════════════════════════════════════════════════════════════════════

def settings_menu(cfg: dict) -> dict:
    _hr("Settings")
    print(f"  Currency      : {cfg.get('currency', 'Not set')}")
    print(f"  Location      : {cfg.get('location', 'Not set')}")
    print(f"  Check interval: {cfg.get('check_interval_minutes', 60)} minutes\n")

    idx = _menu([
        "Change currency",
        "Change location",
        "Change check interval",
        "Back",
    ], "Setting to change")

    if idx == 0:
        cfg["currency"] = _ask("New currency code").upper()
    elif idx == 1:
        cfg["location"] = _ask("New location")
    elif idx == 2:
        cfg["check_interval_minutes"] = _ask_int(
            "New interval (minutes)", lo=5, hi=1440, default=60
        )
    else:
        return cfg

    storage.save_config(cfg)
    notifier.ok("Settings saved.")
    return cfg


# ══════════════════════════════════════════════════════════════════════════════
#  Non-Amazon platform flows
# ══════════════════════════════════════════════════════════════════════════════

def _google_search_flow():
    """Interactive Google Search loop."""
    import scrapers.google_search as gs
    while True:
        _hr("Google Search")
        query = _ask("Search query (or blank to go back)").strip()
        if not query:
            return
        print(f"\n{Fore.CYAN}Searching...{Style.RESET_ALL}")
        sys.stdout.flush()
        try:
            result = gs.search(query)
        except Exception as exc:
            notifier.error(str(exc))
            continue

        organic = result["organic_results"]
        if not organic:
            notifier.warn("No results found.")
            continue

        _hr(f"Results for: {query}")
        for r in organic:
            print(f"  {Fore.YELLOW}{r['position']}.{Style.RESET_ALL} {r['title']}")
            print(f"     {Fore.CYAN}{r['url']}{Style.RESET_ALL}")
            if r.get("snippet"):
                print(f"     {r['snippet'][:120]}")
            print()

        if result["people_also_ask"]:
            print(f"  {Fore.GREEN}People Also Ask:{Style.RESET_ALL}")
            for q in result["people_also_ask"][:4]:
                print(f"    • {q}")
            print()

        input("  Press Enter to search again...")


def _google_shopping_flow():
    """Interactive Google Shopping loop."""
    import scrapers.google_shopping as gsh
    while True:
        _hr("Google Shopping")
        query = _ask("Product query (or blank to go back)").strip()
        if not query:
            return
        country = _ask("Country code", default="us").lower()
        print(f"\n{Fore.CYAN}Searching...{Style.RESET_ALL}")
        sys.stdout.flush()
        try:
            result = gsh.shopping_search(query, country=country)
        except Exception as exc:
            notifier.error(str(exc))
            continue

        items = result["results"]
        if not items:
            notifier.warn("No products found.")
            continue

        _hr(f"Shopping: {query}")
        for r in items:
            price_str = f"${r['price']:.2f}" if r["price"] else "N/A"
            rating_str = f"  ★ {r['rating']:.1f}" if r.get("rating") else ""
            print(f"  {Fore.YELLOW}{r['position']}.{Style.RESET_ALL} {r['title']}")
            print(f"     {Fore.GREEN}{price_str}{Style.RESET_ALL}  from {r['store']}{rating_str}")
            if r.get("product_url"):
                print(f"     {Fore.CYAN}{r['product_url'][:80]}{Style.RESET_ALL}")
            print()

        input("  Press Enter to search again...")


def _google_news_flow():
    """Interactive Google News loop."""
    import scrapers.google_news as gn
    while True:
        _hr("Google News")
        query = _ask("News query (or blank to go back)").strip()
        if not query:
            return
        print(f"\n{Fore.CYAN}Searching...{Style.RESET_ALL}")
        sys.stdout.flush()
        try:
            result = gn.news_search(query)
        except Exception as exc:
            notifier.error(str(exc))
            continue

        articles = result["articles"]
        if not articles:
            notifier.warn("No articles found.")
            continue

        _hr(f"News: {query}")
        for a in articles:
            pub = f"  {Fore.YELLOW}{a['published']}{Style.RESET_ALL}" if a.get("published") else ""
            print(f"  {Fore.YELLOW}{a['position']}.{Style.RESET_ALL} {a['title']}{pub}")
            print(f"     {Fore.CYAN}{a['source']}{Style.RESET_ALL}")
            if a.get("url"):
                print(f"     {a['url'][:80]}")
            print()

        input("  Press Enter to search again...")


def _ebay_flow():
    """Interactive eBay listing lookup loop."""
    import scrapers.ebay as eb
    while True:
        _hr("eBay Product Lookup")
        url = _ask("eBay listing URL (or blank to go back)").strip()
        if not url:
            return
        print(f"\n{Fore.CYAN}Fetching listing...{Style.RESET_ALL}")
        sys.stdout.flush()
        try:
            listing = eb.get_listing(url)
        except Exception as exc:
            notifier.error(str(exc))
            continue

        _hr("eBay Listing")
        print(f"  {Fore.YELLOW}{listing['title']}{Style.RESET_ALL}")
        price_str = f"${listing['price']:.2f}" if listing["price"] else "N/A"
        print(f"  Price     : {Fore.GREEN}{price_str}{Style.RESET_ALL}")
        print(f"  Condition : {listing['condition']}")
        print(f"  Seller    : {listing['seller']}", end="")
        if listing.get("seller_feedback"):
            print(f"  ({listing['seller_feedback']}% positive)", end="")
        print()
        print(f"  Shipping  : {listing['shipping']}")
        stock_tag = f"{Fore.GREEN}In Stock" if listing["in_stock"] else f"{Fore.RED}Out of Stock"
        print(f"  Stock     : {stock_tag}{Style.RESET_ALL}")
        if listing.get("bids") is not None:
            print(f"  Bids      : {listing['bids']}")
        print(f"  URL       : {listing['url'][:72]}")

        input("\n  Press Enter to look up another...")


def _generic_web_flow():
    """Interactive generic web fetch loop."""
    import scrapers.generic as gw
    while True:
        _hr("Generic Web Fetch")
        url = _ask("URL to fetch (or blank to go back)").strip()
        if not url:
            return
        include_text = _ask("Include plain-text extraction? (y/n)", default="n").lower() == "y"
        print(f"\n{Fore.CYAN}Fetching...{Style.RESET_ALL}")
        sys.stdout.flush()
        try:
            result = gw.fetch_html(url, include_text=include_text)
        except Exception as exc:
            notifier.error(str(exc))
            continue

        _hr("Fetch Result")
        status_color = Fore.GREEN if result["status"] == "ok" else Fore.RED
        print(f"  Status    : {status_color}{result['status'].upper()}{Style.RESET_ALL}")
        print(f"  Final URL : {result['url']}")
        print(f"  HTML size : {len(result['html']):,} bytes")
        if result.get("text"):
            preview = result["text"][:400].replace("\n", " ")
            print(f"\n  Text preview:\n  {preview}...")

        input("\n  Press Enter to fetch another...")


def _amazon_main(cfg: dict):
    """Full Amazon price tracker main loop."""
    while True:
        items    = storage.load_items()
        n_items  = len(items)
        n_alerts = sum(1 for i in items if i.alert_triggered)

        status = f"  {n_items} item(s) tracked"
        if n_alerts:
            status += f"   {Fore.GREEN}|  {n_alerts} alert(s) triggered!{Style.RESET_ALL}"

        _hr(f"Amazon Tracker  ·  {cfg['currency']}  ·  {cfg['location']}")
        print(status + "\n")

        idx = _menu([
            "Add new item to track",
            f"View / manage items  ({n_items} tracked)",
            "Check all prices now",
            "Start auto-monitoring",
            "Settings",
            "Back to platform menu",
        ], "Choose")

        if   idx == 0:  add_item_flow(cfg)
        elif idx == 1:  view_items_menu(cfg)
        elif idx == 2:  check_all(cfg)
        elif idx == 3:  run_monitor(cfg)
        elif idx == 4:  cfg = settings_menu(cfg)
        elif idx == 5:  return cfg


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    _hr("Open Data API  —  CLI")
    print(f"  {Fore.CYAN}Multi-platform data extraction tool{Style.RESET_ALL}\n")

    cfg = storage.load_config()

    while True:
        _hr("Platform Select")
        idx = _menu([
            f"{Fore.YELLOW}Amazon{Style.RESET_ALL}         — Price tracking, alerts, monitoring",
            f"{Fore.CYAN}Google Search{Style.RESET_ALL}   — Web search results (SERP)",
            f"{Fore.CYAN}Google Shopping{Style.RESET_ALL} — Product search & price comparison",
            f"{Fore.CYAN}Google News{Style.RESET_ALL}     — Real-time news articles",
            f"{Fore.GREEN}eBay{Style.RESET_ALL}            — Product listing lookup",
            f"{Fore.GREEN}Generic Web{Style.RESET_ALL}     — Fetch rendered HTML for any URL",
            "Exit",
        ], "Select platform")

        if idx == 0:
            # Amazon needs currency/location config
            if not cfg.get("currency") or not cfg.get("location"):
                cfg = _setup_wizard()
            cfg = _amazon_main(cfg)

        elif idx == 1:  _google_search_flow()
        elif idx == 2:  _google_shopping_flow()
        elif idx == 3:  _google_news_flow()
        elif idx == 4:  _ebay_flow()
        elif idx == 5:  _generic_web_flow()
        elif idx == 6:
            print(f"\n{Fore.CYAN}Goodbye!{Style.RESET_ALL}\n")
            sys.exit(0)


if __name__ == "__main__":
    main()
