import sys
import runpy
import subprocess
from unittest.mock import MagicMock, call, patch
import pytest

# Ensure path includes current directory
sys.path.append(".")

def test_apply_schema_aws_success():
    """Test successful AWS schema application."""
    
    with patch("builtins.open", new_callable=MagicMock) as mock_open, \
         patch("psycopg2.connect") as mock_connect:
        
        # Mock file read
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "CREATE TABLE..."
        mock_open.return_value = mock_file
        
        # Mock DB connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # 1. Verify table fetchone returns ("litellm_usage",)
        # 2. Verify indexes fetchall returns list of indexes
        mock_cursor.fetchone.return_value = ("litellm_usage",)
        mock_cursor.fetchall.return_value = [("idx_1",), ("idx_2",)]
        
        runpy.run_path("apply_schema_aws.py", run_name="__main__")
        
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
        
        # Verify calls
        mock_cursor.execute.assert_any_call("CREATE TABLE...")

def test_apply_schema_aws_table_not_found():
    """Test verification failure (table not found)."""
    with patch("builtins.open", new_callable=MagicMock) as mock_open, \
         patch("psycopg2.connect") as mock_connect:
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        mock_cursor.fetchone.return_value = None
        
        runpy.run_path("apply_schema_aws.py", run_name="__main__")
        
        # Should not fetch indexes
        mock_cursor.fetchall.assert_not_called()

def test_apply_schema_aws_db_error():
    """Test handling of database connection error."""
    with patch("psycopg2.connect") as mock_connect:
        import psycopg2
        mock_connect.side_effect = psycopg2.Error("Connection Failed")
        
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_path("apply_schema_aws.py", run_name="__main__")
        
        assert excinfo.value.code == 1

def test_apply_schema_aws_generic_error():
    """Test handling of generic exception."""
    with patch("builtins.open", side_effect=Exception("File Error")):
         with pytest.raises(SystemExit) as excinfo:
            runpy.run_path("apply_schema_aws.py", run_name="__main__")
         
         assert excinfo.value.code == 1
