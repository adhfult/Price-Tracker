"""Data models for the Amazon Price Tracker."""

from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum


class AlertType(str, Enum):
    BELOW_PRICE    = "below_price"      # Alert when price drops below a target
    IN_RANGE       = "in_range"         # Alert when price enters a min–max range
    ANY_DROP       = "any_drop"         # Alert on any price decrease between checks
    DROP_BY_AMOUNT = "drop_by_amount"   # Alert when price drops by ≥ $X from baseline
    DROP_BY_PERCENT = "drop_by_percent" # Alert when price drops by ≥ X% from baseline


@dataclass
class AlertCriteria:
    alert_type: AlertType
    target_price:  Optional[float] = None   # BELOW_PRICE
    min_price:     Optional[float] = None   # IN_RANGE
    max_price:     Optional[float] = None   # IN_RANGE
    drop_amount:   Optional[float] = None   # DROP_BY_AMOUNT
    drop_percent:  Optional[float] = None   # DROP_BY_PERCENT


@dataclass
class TrackedItem:
    id:               str
    url:              str
    title:            str
    asin:             str
    currency:         str
    location:         str
    alert_criteria:   AlertCriteria

    # Variant selection made by the user, e.g. {"Color": "Midnight Black", "Size": "256 GB"}
    selected_variants: Dict[str, str] = field(default_factory=dict)

    # Latest scraped pricing data
    last_price:           Optional[float] = None
    last_original_price:  Optional[float] = None
    last_prime_price:     Optional[float] = None
    last_discount_percent: Optional[float] = None

    # Price at the time the item / criteria was (last) saved – used for relative checks
    baseline_price: Optional[float] = None

    is_prime_eligible: bool = False
    in_stock:          bool = True

    date_added:    str  = ""
    last_checked:  str  = ""
    alert_triggered: bool = False
