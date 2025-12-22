#!/usr/bin/env python
"""
Minimal Stripe usage reporter.

Batch-aggregates usage per tenant and posts to Stripe subscription items.
Assumes you already map tenant_id -> subscription_item_id in your DB.
Replace the stub `get_batch()` with your store/queue fetch.
"""

from __future__ import annotations

import os
import time
from typing import Iterable, Tuple

import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


def get_batch() -> Iterable[Tuple[str, int]]:
    """
    Return an iterable of (subscription_item_id, quantity) to report.
    Replace with DB/queue fetch that sums tokens/requests per tenant for the interval.
    """
    # Example stub: no-op
    return []


def report_usage(subscription_item_id: str, quantity: int) -> None:
    stripe.UsageRecord.create(
        subscription_item=subscription_item_id,
        quantity=quantity,
        timestamp=int(time.time()),
        action="increment",
    )


def main() -> None:
    if not stripe.api_key:
        raise SystemExit("Set STRIPE_SECRET_KEY")
    for sub_item_id, qty in get_batch():
        if qty <= 0:
            continue
        report_usage(sub_item_id, qty)


if __name__ == "__main__":
    main()

