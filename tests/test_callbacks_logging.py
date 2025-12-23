from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from callbacks import logging as cb_logging

def test_usage_fields_empty():
    """Test _usage_fields with None or empty data."""
    assert cb_logging._usage_fields(None) == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }
    assert cb_logging._usage_fields({}) == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }

def test_usage_fields_valid():
    """Test _usage_fields extracts correct values."""
    response = {
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    expected = {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
    }
    assert cb_logging._usage_fields(response) == expected

def test_cost_usd_none():
    """Test _cost_usd returns None when missing."""
    assert cb_logging._cost_usd(None) is None
    assert cb_logging._cost_usd({}) is None
    assert cb_logging._cost_usd({"metadata": {}}) is None

def test_cost_usd_direct():
    """Test _cost_usd finds 'response_cost'."""
    assert cb_logging._cost_usd({"response_cost": 1.23}) == 1.23

def test_cost_usd_metadata():
    """Test _cost_usd finds cost in metadata."""
    data = {"metadata": {"response_cost": 4.56}}
    assert cb_logging._cost_usd(data) == 4.56

@pytest.mark.asyncio
async def test_log_event_output(capsys):
    """Test log_event prints correct JSON to stdout."""
    request_data = {
        "model": "gpt-3.5-turbo",
        "metadata": {"tenant_id": "cust-1"}
    }
    response_data = {
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 5,
            "total_tokens": 10
        },
        "status": "success",
        "id": "req-123",
        "response_cost": 0.0002
    }
    start_time = 1000.0
    end_time = 1000.1 # 100ms
    
    await cb_logging.log_event(request_data, response_data, start_time, end_time)
    
    captured = capsys.readouterr()
    output = captured.out.strip()
    
    # Parse JSON to verify structure
    log_entry = json.loads(output)
    
    assert log_entry["message"] == "litellm_request"
    assert log_entry["severity"] == "INFO"
    assert "timestamp" in log_entry
    assert log_entry["latency_ms"] == 100
    assert log_entry["model"] == "gpt-3.5-turbo"
    assert log_entry["tenant_id"] == "cust-1"
    assert log_entry["request_id"] == "req-123"
    assert log_entry["cost_usd"] == 0.0002
    assert log_entry["total_tokens"] == 10
    assert log_entry["labels"]["tenant_id"] == "cust-1"
