import unittest
from unittest.mock import patch, MagicMock
import json
import os

# Set env vars before importing
os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
os.environ['PROXY_MASTER_KEY'] = 'sk_test'

from proxy.billing_service import app

class TestFreeTier(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('proxy.billing_service.requests.post')
    @patch('proxy.billing_service.get_db_connection')
    @patch('proxy.billing_service.logger')
    def test_signup_success(self, mock_logger, mock_db_conn, mock_post):
        # Mock DB - User check returns None (new user)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None 
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn

        # Mock LiteLLM Key Generation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "sk-litellm-123"}
        mock_post.return_value = mock_response

        # Call Signup
        response = self.app.post('/user/signup', json={'email': 'newuser@example.com'})
        
        # Verify Response
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['api_key'], "sk-litellm-123")
        self.assertIn("free credit", str(data)) # Or whatever simple message
        
        # Verify DB Insert
        self.assertTrue(mock_cursor.execute.called)
        # Check call args to ensure correct balance/email
        # We expect INSERT INTO customers ... VALUES (..., 0.0, 'newuser@example.com')
        # The exact order depends on implementation but we can search for the SQL
        calls = mock_cursor.execute.call_args_list
        found_insert = False
        for call in calls:
            if 'INSERT INTO customers' in call[0][0]:
                found_insert = True
                # Params are (email, email)
                self.assertEqual(call[0][1][0], 'newuser@example.com') # user/email
        self.assertTrue(found_insert, "Database insert not found")

        # Verify LiteLLM Call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn('/key/generate', args[0])
        self.assertEqual(kwargs['json']['max_budget'], 0.50)

    @patch('proxy.billing_service.get_db_connection')
    def test_signup_existing_user(self, mock_db_conn):
        # Mock DB - User check returns record
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('existing@example.com',)
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn

        response = self.app.post('/user/signup', json={'email': 'existing@example.com'})
        
        self.assertEqual(response.status_code, 409)
        self.assertIn("User already exists", str(response.data))

if __name__ == '__main__':
    unittest.main()
