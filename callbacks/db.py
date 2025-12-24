"""
Postgres logging callback for LiteLLM proxy.

Persists per-request usage to a Postgres table for auditing/analytics.
Set these environment variables:
  PGHOST, PGPORT (default 5432), PGUSER, PGPASSWORD, PGDATABASE
Optional:
  PGSSL=disable (to skip TLS; default is require)
"""

from __future__ import annotations

import asyncio
import os
import sys
import ssl
from datetime import datetime
from typing import Any, Dict, Optional

import asyncpg

_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


def _ssl_context() -> Optional[ssl.SSLContext]:
    if os.environ.get("PGSSL", "require").lower() == "disable":
        return None
    return ssl.create_default_context()


async def _get_pool() -> Optional[asyncpg.Pool]:
    global _pool
    if _pool:
        return _pool
    async with _pool_lock:
        if _pool:
            return _pool

        host = os.environ.get("PGHOST")
        user = os.environ.get("PGUSER")
        password = os.environ.get("PGPASSWORD")
        database = os.environ.get("PGDATABASE")
        port = int(os.environ.get("PGPORT", "5432"))

        if not all([host, user, password, database]):
            print("pg_callback: missing PG env vars; skipping persistence")
            return None

        try:
            _pool = await asyncpg.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                ssl=_ssl_context(),
                min_size=1,
                max_size=5,
            )
        except Exception as exc:  # pragma: no cover - defensive
            print(f"pg_callback: failed to create pool: {exc}")
            return None
    return _pool


async def _insert(pool: asyncpg.Pool, row: Dict[str, Any]) -> None:
    sql = """
    INSERT INTO litellm_usage (
        created_at,
        tenant_id,
        model,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        latency_ms,
        status,
        cost_usd,
        request_id
    ) VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9)
    """
    await pool.execute(
        sql,
        row.get("tenant_id"),
        row.get("model"),
        row.get("prompt_tokens"),
        row.get("completion_tokens"),
        row.get("total_tokens"),
        row.get("latency_ms"),
        row.get("status"),
        row.get("cost_usd"),
        row.get("request_id"),
    )


async def log_event(
    request_data: Optional[Dict[str, Any]],
    response_data: Optional[Dict[str, Any]],
    start_time: float,
    end_time: float,
    **_: Any,
) -> None:
    """
    LiteLLM callback: persists request usage to Postgres.
    """
    try:
        pool = await _get_pool()
        if not pool:
            print("pg_callback: pool is None", file=sys.stderr)
            return

        try:
            diff = end_time - start_time
            if hasattr(diff, "total_seconds"):
                latency_ms = int(diff.total_seconds() * 1000)
            else:
                latency_ms = int(diff * 1000)
        except Exception as e:
            print(f"pg_callback: latency calc failed: {e}", file=sys.stderr)
            latency_ms = 0

        usage = (response_data or {}).get("usage") or {}
        
        row = {
            "tenant_id": (request_data or {}).get("metadata", {}).get("tenant_id"),
            "model": (request_data or {}).get("model"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "latency_ms": latency_ms,
            "status": (response_data or {}).get("status")
            or (response_data or {}).get("status_code"),
            "cost_usd": (response_data or {}).get("response_cost")
            or (response_data or {}).get("metadata", {}).get("response_cost"),
            "request_id": (response_data or {}).get("id")
            or (response_data or {}).get("request_id"),
        }
        
        await _insert(pool, row)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"pg_callback: log_event failed: {exc}")

