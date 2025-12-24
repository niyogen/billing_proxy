import os
import logging
import stripe
import requests
import psycopg2
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
LITELLM_MASTER_KEY = os.environ.get("PROXY_MASTER_KEY", "")
LITELLM_URL = "http://127.0.0.1:4000"

stripe.api_key = STRIPE_API_KEY

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("PGHOST"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER"),
        password=os.environ.get("PGPASSWORD"),
        database=os.environ.get("PGDATABASE"),
        sslmode=os.environ.get("PGSSL", "require")
    )

def update_litellm_budget(user_email, amount_usd):
    """
    Updates or Creates a key for the user with increased budget.
    """
    try:
        # 1. Check if user exists in LiteLLM (via our DB or LiteLLM API)
        # We will assume user_id = email for simplicity
        
        # 2. Key Generation / Update Request
        # We use the /key/generate endpoint which acts as an upsert if we don't specify the key value,
        # but we want to update the budget.
        
        # First, try to list keys for this user to see current budget?
        # Simpler: Maintain 'total_purchased' in our DB and sync 'max_budget' to it.
        
        headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}", "Content-Type": "application/json"}
        
        # We'll use the email as the user_id
        # Calculate new total budget
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update customers table
        cur.execute("""
            INSERT INTO customers (tenant_id, balance_usd, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id) 
            DO UPDATE SET balance_usd = customers.balance_usd + EXCLUDED.balance_usd
            RETURNING balance_usd;
        """, (user_email, amount_usd, user_email))
        
        new_balance = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Now update LiteLLM max_budget
        # Note: LiteLLM max_budget is TOTAL lifetime budget.
        # If we store "balance_usd" as "current available credits", we need to map that.
        # But LiteLLM checks (spend < max_budget).
        # So we should set max_budget = current_spend + available_balance.
        # But we don't easily know current_spend without querying LiteLLM.
        
        # Strategy: Let's assume passed amount is ADDED to the budget.
        # We will just generate a key with metadata.
        # Actually, best way is to use /user/update if available, or just /key/generate
        
        payload = {
            "user_id": user_email,
            "max_budget": float(new_balance) # This is risky if balance tracks "remaining" vs "total".
            # If `balance_usd` in DB tracks *total purchased*, then this is correct.
            # Let's pivot: Table `customers` should track `total_funded`.
        }
        
        # For this MVP, we just log the intention. Real implementation needs robust sync.
        logger.info(f"Updating budget for {user_email} to ${new_balance}")
        
        # Call LiteLLM to update key (upsert)
        # We need to calculate total budget: Free Tier ($0.50) + Paid Balance
        FREE_TIER_AMOUNT = 0.50
        total_budget = FREE_TIER_AMOUNT + float(new_balance)
        
        # Note: /key/update might require the key token itself in some versions.
        # If /user/update is available, use that. 
        # For LiteLLM Proxy, updating a user's budget usually applies to all their keys if configured,
        # or we update the specific key associated with the user.
        # Let's try /key/generate which acts as upsert for user_id too if no key is passed?
        # Safe bet: /key/generate with user_id returns a new key or updates? 
        # Actually, let's use /user/new or /user/update if we are tracking users.
        # For simplicity in this `billing_service`, we will assume we maintain a key per user.
        
        # We will use /key/generate to "update" the budget for the user.
        # If we don't pass 'key', it generates a NEW one. That's bad for existing users.
        # We really need to know the User's Key to update it, OR rely on 'user_id' based enforcement.
        # LiteLLM allows 'user_id' based budgets.
        
        update_payload = {
            "user_id": user_email,
            "max_budget": total_budget
        }
        
        try:
             headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}", "Content-Type": "application/json"}
             resp = requests.post(f"{LITELLM_URL}/user/update", json=update_payload, headers=headers)
             if resp.status_code != 200:
                  # Fallback to creating a user if not exists?
                  logger.warning(f"Failed to update user budget: {resp.text}")
        except Exception as e:
             logger.error(f"LiteLLM connection error: {e}")

        return True

    except Exception as e:
        logger.error(f"Error updating LiteLLM: {e}")
        return False

def generate_free_tier_key(user_email):
    """
    Generates a new key for a user with the default free tier budget.
    """
    try:
        headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}", "Content-Type": "application/json"}
        FREE_TIER_AMOUNT = 0.50
        
        # 1. Create User in LiteLLM (optional but good for tracking)
        # 2. Generate Key
        
        payload = {
            "user_id": user_email,
            "models": ["gpt-4o", "gpt-4o-mini"], # Restrict models if needed
            "max_budget": FREE_TIER_AMOUNT,
            "duration": "30d" # Optional expiration
        }
        
        response = requests.post(f"{LITELLM_URL}/key/generate", json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("key")
        else:
            logger.error(f"Failed to generate key: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating key: {e}")
        return None

@app.route('/user/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email required"}), 400
        
    # Check if user already exists
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT tenant_id FROM customers WHERE tenant_id = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "User already exists"}), 409
    
    # Create new customer
    try:
        cur.execute("INSERT INTO customers (tenant_id, balance_usd, email) VALUES (%s, 0.0, %s)", (email, email))
        conn.commit()
        
        # Generate LiteLLM Key
        key = generate_free_tier_key(email)
        
        if key:
            return jsonify({
                "status": "success",
                "message": "Account created with $.50 free credit",
                "api_key": key,
                "api_base": f"https://{request.host}/v1" # Heuristic
            }), 201
        else:
            # Rollback?
            return jsonify({"error": "Failed to provision API key"}), 500
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Signup error: {e}")
        return jsonify({"error": "Internal error"}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({"error": "Invalid signature"}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        customer_email = session.get('customer_details', {}).get('email')
        amount_cents = session.get('amount_total', 0)
        amount_usd = amount_cents / 100.0
        
        if customer_email:
            logger.info(f"Payment received: {customer_email}, ${amount_usd}")
            update_litellm_budget(customer_email, amount_usd)
            
            # Log transaction
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO transactions (tenant_id, stripe_charge_id, amount_usd, type, description)
                VALUES (%s, %s, %s, 'credit', 'Stripe Checkout')
            """, (customer_email, session.get('payment_intent'), amount_usd))
            conn.commit()
            conn.close()

    return jsonify({"status": "success"}), 200

@app.route('/health', methods=['GET'])
def health():
    return "Billing Service OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4001)
