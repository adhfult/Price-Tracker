"""
Alert notifications – desktop toast (via plyer) + always-visible console banner.
Also provides shared formatting helpers used across the codebase.
"""

from typing import Optional
from colorama import Fore, Style, init as _init

_init(autoreset=True)

# ISO 4217 → symbol
CURRENCY_SYMBOLS: dict = {
    "USD": "$",   "EUR": "€",   "GBP": "£",   "JPY": "¥",   "CNY": "¥",
    "CAD": "CA$", "AUD": "A$",  "NZD": "NZ$", "CHF": "Fr",
    "INR": "₹",   "BRL": "R$",  "MXN": "$",   "KRW": "₩",
    "SEK": "kr",  "NOK": "kr",  "DKK": "kr",
    "SGD": "S$",  "HKD": "HK$", "ZAR": "R",   "RUB": "₽",
    "PLN": "zł",  "CZK": "Kč",  "HUF": "Ft",  "TRY": "₺",
}


def get_symbol(currency: str) -> str:
    return CURRENCY_SYMBOLS.get(currency.upper(), currency.upper() + " ")


def fmt_price(amount: Optional[float], currency: str) -> str:
    if amount is None:
        return "N/A"
    return f"{get_symbol(currency)}{amount:,.2f}"


# ── console helpers ───────────────────────────────────────────────────────────

def info(msg: str):
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")


def ok(msg: str):
    print(f"{Fore.GREEN}[ OK ]{Style.RESET_ALL} {msg}")


def warn(msg: str):
    print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")


def error(msg: str):
    print(f"{Fore.RED}[ERR ]{Style.RESET_ALL} {msg}")


# ── alert ─────────────────────────────────────────────────────────────────────

def send_alert(
    item_title:     str,
    currency:       str,
    current_price:  float,
    criteria_desc:  str,
    url:            str,
    original_price: Optional[float] = None,
    prime_price:    Optional[float] = None,
):
    """Fire a desktop notification (best-effort) and always print a console banner."""
    price_str = fmt_price(current_price, currency)

    # ── desktop notification (non-fatal if unavailable) ──
    try:
        from plyer import notification  # type: ignore
        body_lines = [f"Price: {price_str}", f"Alert: {criteria_desc}"]
        if original_price:
            body_lines.append(f"Was: {fmt_price(original_price, currency)}")
        # Windows balloon tip has a 64-char limit, account for "Price Alert: " (13 chars)
        notification.notify(
            title=f"Price Alert: {item_title[:50]}",
            message="\n".join(body_lines),
            app_name="Amazon Price Tracker",
            timeout=15,
        )
    except Exception:
        pass

    # ── console banner (always shown) ────────────────────
    bar = "=" * 66
    print(f"\n{Fore.GREEN}{bar}")
    print(f"{Fore.GREEN}   PRICE ALERT  {Style.RESET_ALL}{item_title[:52]}")
    print(f"{Fore.GREEN}{bar}")
    print(f"  Current Price  : {Fore.YELLOW}{price_str}")
    if original_price:
        print(f"  Original Price : {Style.RESET_ALL}{fmt_price(original_price, currency)}")
    if prime_price:
        print(f"  Prime Price    : {Fore.CYAN}{fmt_price(prime_price, currency)}")
    print(f"  Alert          : {Style.RESET_ALL}{criteria_desc}")
    print(f"  Link           : {url}")
    print(f"{Fore.GREEN}{bar}{Style.RESET_ALL}\n")
