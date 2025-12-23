from __future__ import annotations

import asyncio
import os
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from callbacks import db

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {
        "PGHOST": "localhost",
        "PGUSER": "test_user",
        "PGPASSWORD": "test_password",
        "PGDATABASE": "test_db",
        "PGPORT": "5432"
    }, clear=True):
        yield

@pytest.fixture
def cleanup_pool():
    # Reset the global pool before and after tests
    db._pool = None
    yield
    db._pool = None

def test_ssl_context_default():
    """Test that SSL context is created by default (require)."""
    with patch.dict(os.environ, {}, clear=True):
        ctx = db._ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

def test_ssl_context_disable():
    """Test that SSL context is None when PGSSL is disable."""
    with patch.dict(os.environ, {"PGSSL": "disable"}, clear=True):
        ctx = db._ssl_context()
        assert ctx is None

@pytest.mark.asyncio
async def test_get_pool_missing_env():
    """Test that _get_pool returns None if env vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        pool = await db._get_pool()
        assert pool is None

@pytest.mark.asyncio
async def test_get_pool_success(mock_env, cleanup_pool):
    """Test successful pool creation."""
    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create:
        mock_pool = AsyncMock()
        mock_create.return_value = mock_pool
        
        pool = await db._get_pool()
        
        assert pool is mock_pool
        mock_create.assert_called_once()
        # Verify arguments
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["host"] == "localhost"
        assert call_kwargs["user"] == "test_user"
        assert call_kwargs["database"] == "test_db"

@pytest.mark.asyncio
async def test_get_pool_cached(mock_env, cleanup_pool):
    """Test that _get_pool returns the cached pool."""
    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create:
        mock_pool = AsyncMock()
        mock_create.return_value = mock_pool
        
        pool1 = await db._get_pool()
        pool2 = await db._get_pool()
        
        assert pool1 is pool2
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_get_pool_failure(mock_env, cleanup_pool):
    """Test _get_pool handles exceptions during pool creation."""
    with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
        pool = await db._get_pool()
        assert pool is None

@pytest.mark.asyncio
async def test_insert_success():
    """Test _insert executes the correct SQL."""
    mock_pool = AsyncMock()
    row = {
        "tenant_id": "tenant-123",
        "model": "gpt-4",
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "latency_ms": 500,
        "status": "success",
        "cost_usd": 0.002,
        "request_id": "req-1",
    }
    
    await db._insert(mock_pool, row)
    
    mock_pool.execute.assert_called_once()
    args = mock_pool.execute.call_args[0]
    assert "INSERT INTO litellm_usage" in args[0]
    assert args[1] == "tenant-123"
    assert args[2] == "gpt-4"
    assert args[9] == "req-1"

@pytest.mark.asyncio
async def test_log_event_no_pool(mock_env, cleanup_pool):
    """Test log_event does nothing if pool cannot be created."""
    with patch("callbacks.db._get_pool", return_value=None), \
         patch("callbacks.db._insert") as mock_insert:
        
        await db.log_event(None, None, 0, 0)
        mock_insert.assert_not_called()

@pytest.mark.asyncio
async def test_log_event_success(cleanup_pool):
    """Test log_event correctly parses data and calls _insert."""
    mock_pool = AsyncMock()
    with patch("callbacks.db._get_pool", return_value=mock_pool), \
         patch("callbacks.db._insert", new_callable=AsyncMock) as mock_insert:
        
        request_data = {
            "model": "gpt-4",
            "metadata": {"tenant_id": "tenant-xyz"}
        }
        response_data = {
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 5,
                "total_tokens": 10
            },
            "status": "success",
            "response_cost": 0.001,
            "id": "req-abc"
        }
        start_time = 1000.0
        end_time = 1000.5 # 500ms latency
        
        await db.log_event(request_data, response_data, start_time, end_time)
        
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        pool_arg = call_args[0][0]
        row_arg = call_args[0][1]
        
        assert pool_arg is mock_pool
        assert row_arg["tenant_id"] == "tenant-xyz"
        assert row_arg["model"] == "gpt-4"
        assert row_arg["latency_ms"] == 500
        assert row_arg["cost_usd"] == 0.001

@pytest.mark.asyncio
async def test_log_event_exception_handling(cleanup_pool):
    """Test log_event handles exceptions during insert."""
    mock_pool = AsyncMock()
    # Mock _insert to raise an exception
    with patch("callbacks.db._get_pool", return_value=mock_pool), \
         patch("callbacks.db._insert", side_effect=Exception("DB Error")):
        
        # Should not raise exception
        await db.log_event({}, {}, 0, 0)
