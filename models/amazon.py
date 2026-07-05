"""Amazon domain data models — moved from the top-level models.py."""

from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum


class AlertType(str, Enum):
    BELOW_PRICE     = "below_price"
    IN_RANGE        = "in_range"
    ANY_DROP        = "any_drop"
    DROP_BY_AMOUNT  = "drop_by_amount"
    DROP_BY_PERCENT = "drop_by_percent"


@dataclass
class AlertCriteria:
    alert_type:    AlertType
    target_price:  Optional[float] = None
    min_price:     Optional[float] = None
    max_price:     Optional[float] = None
    drop_amount:   Optional[float] = None
    drop_percent:  Optional[float] = None


@dataclass
class TrackedItem:
    id:             str
    url:            str
    title:          str
    asin:           str
    currency:       str
    location:       str
    alert_criteria: AlertCriteria

    selected_variants:     Dict[str, str]  = field(default_factory=dict)
    last_price:            Optional[float] = None
    last_original_price:   Optional[float] = None
    last_prime_price:      Optional[float] = None
    last_discount_percent: Optional[float] = None
    baseline_price:        Optional[float] = None
    is_prime_eligible:     bool            = False
    in_stock:              bool            = True
    date_added:            str             = ""
    last_checked:          str             = ""
    alert_triggered:       bool            = False
