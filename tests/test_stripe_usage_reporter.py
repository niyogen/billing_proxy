import os
import sys
from unittest.mock import MagicMock, patch

import pytest
# Ensure we can import scripts
sys.path.append(".")
from scripts import stripe_usage_reporter

def test_report_usage_success():
    """Test report_usage calls Stripe API."""
    with patch("scripts.stripe_usage_reporter.stripe") as mock_stripe:
        uuid = "sub_item_123"
        qty = 10
        stripe_usage_reporter.report_usage(uuid, qty)
        
        mock_stripe.UsageRecord.create.assert_called_once()
        args = mock_stripe.UsageRecord.create.call_args[1]
        assert args["subscription_item"] == uuid
        assert args["quantity"] == qty

def test_main_no_key():
    """Test main exits if STRIPE_SECRET_KEY is not set."""
    with patch("scripts.stripe_usage_reporter.stripe") as mock_stripe:
        mock_stripe.api_key = None
        
        with pytest.raises(SystemExit) as excinfo:
            stripe_usage_reporter.main()
        
        assert "Set STRIPE_SECRET_KEY" in str(excinfo.value)

def test_main_success():
    """Test main loop reports usage from batched items."""
    with patch("scripts.stripe_usage_reporter.stripe") as mock_stripe, \
         patch("scripts.stripe_usage_reporter.get_batch") as mock_get_batch, \
         patch("scripts.stripe_usage_reporter.report_usage") as mock_report:
        
        mock_stripe.api_key = "sk_test_123"
        
        mock_get_batch.return_value = [
            ("item_1", 5),
            ("item_2", 0),
            ("item_3", 10)
        ]
        
        stripe_usage_reporter.main()
        
        assert mock_report.call_count == 2
        mock_report.assert_any_call("item_1", 5)
        mock_report.assert_any_call("item_3", 10)

def test_get_batch():
    """Test default get_batch returns empty list."""
    assert stripe_usage_reporter.get_batch() == []
