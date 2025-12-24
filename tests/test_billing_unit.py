import unittest
from unittest.mock import patch, MagicMock
import json
import os

# Set env vars before importing
os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
os.environ['PROXY_MASTER_KEY'] = 'sk_test'

from proxy.billing_service import app, update_litellm_budget

class TestBillingService(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('proxy.billing_service.stripe.Webhook.construct_event')
    @patch('proxy.billing_service.get_db_connection')
    @patch('proxy.billing_service.logger') # suppress logs
    def test_webhook_checkout_completed(self, mock_logger, mock_db_conn, mock_construct_event):
        # Mock Stripe Event
        mock_payload = {
            'id': 'evt_test',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'customer_details': {'email': 'test@example.com'},
                    'amount_total': 1000, # $10.00
                    'payment_intent': 'pi_test'
                }
            }
        }
        
        mock_construct_event.return_value = mock_payload
        
        # Mock DB
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [10.0] # New balance
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn

        # Mock requests (inside update_litellm_budget)
        # We can't easily mock requests inside the function if it's not imported or passed.
        # But update_litellm_budget is imported from the module.
        # Actually requests is used inside it. We should patch `proxy.billing_service.requests`?
        # Or patch `proxy.billing_service.update_litellm_budget` itself to avoid testing that interaction?
        # Let's test the webhook flow up to calling the update function.
        
        with patch('proxy.billing_service.update_litellm_budget') as mock_update:
            response = self.app.post(
                '/webhook/stripe',
                data=json.dumps(mock_payload),
                headers={'Stripe-Signature': 't=123,v1=signature'}
            )
            
            self.assertEqual(response.status_code, 200)
            mock_update.assert_called_with('test@example.com', 10.0)
            
            # Verify DB transactions
            # We expect INSERT into transactions
            self.assertTrue(mock_cursor.execute.called)
            args, _ = mock_cursor.execute.call_args_list[0]
            self.assertIn('INSERT INTO transactions', args[0])
            self.assertEqual(args[1][0], 'test@example.com') # tenant_id
            self.assertEqual(args[1][2], 10.0) # amount

    @patch('proxy.billing_service.get_db_connection')
    def test_update_litellm_budget(self, mock_db_conn):
        # Mock DB
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [20.0] 
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn
        
        # Mock requests only?
        # Let's assume LiteLLM call fails or succeeds, strictly strictly strictly speaking we should integration test,
        # but unit test verifies logic.
        
        result = update_litellm_budget('user@test.com', 5.0)
        self.assertTrue(result)
        
        # Verify DB calls
        self.assertTrue(mock_cursor.execute.called)
        args, _ = mock_cursor.execute.call_args
        self.assertIn('INSERT INTO customers', args[0])
        self.assertEqual(args[1][0], 'user@test.com')

if __name__ == '__main__':
    unittest.main()
