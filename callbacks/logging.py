"""
Structured logging callback for LiteLLM proxy.

Emits a JSON log per request so Cloud Logging/Monitoring can
build dashboards and alerts around tokens, cost, latency, and errors.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usage_fields(response_data: Optional[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    usage = {}
    if isinstance(response_data, dict):
        usage = response_data.get("usage") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def _cost_usd(response_data: Optional[Dict[str, Any]]) -> Optional[float]:
    if not isinstance(response_data, dict):
        return None
    # LiteLLM often injects cost under "response_cost" or in metadata; grab either if present.
    cost = response_data.get("response_cost")
    if cost is not None:
        return cost
    metadata = response_data.get("metadata") or {}
    return metadata.get("response_cost")


async def log_event(
    request_data: Optional[Dict[str, Any]],
    response_data: Optional[Dict[str, Any]],
    start_time: float,
    end_time: float,
    **kwargs: Any,
) -> None:
    """
    Callback signature expected by LiteLLM.
    Prints structured JSON to stdout for Cloud Logging ingestion.
    """

    latency_ms = int((end_time - start_time) * 1000)
    usage = _usage_fields(response_data)
    log_record = {
        "message": "litellm_request",
        "severity": "INFO",
        "timestamp": _now_iso(),
        "latency_ms": latency_ms,
        "model": (request_data or {}).get("model"),
        "tenant_id": (request_data or {}).get("metadata", {}).get("tenant_id"),
        "status": (response_data or {}).get("status") or (response_data or {}).get(
            "status_code"
        ),
        "error": (response_data or {}).get("error"),
        "request_id": (response_data or {}).get("id")
        or (response_data or {}).get("request_id"),
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "cost_usd": _cost_usd(response_data),
    }

    # Optional: attach labels for easier Cloud Logging queries.
    log_record["labels"] = {
        "tenant_id": log_record["tenant_id"],
        "model": log_record["model"],
    }

    print(json.dumps(log_record), flush=True)

