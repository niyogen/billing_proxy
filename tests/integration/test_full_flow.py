import os
import sys
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Config
PROXY_URL = "http://localhost:8080"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "litellm_user",
    "password": "test_password",
    "database": "litellm"
}
TOKEN = "sk-1234"

def wait_for_proxy():
    print("Waiting for proxy to be ready...")
    for _ in range(30):
        try:
            resp = requests.get(f"{PROXY_URL}/health/liveness")
            if resp.status_code == 200:
                print("Proxy is ready!")
                return
        except requests.ConnectionError:
            pass
        time.sleep(1)
    raise Exception("Proxy failed to start")

def test_proxy_request():
    print("Sending test request to proxy...")
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello world"}]
    }
    
    resp = requests.post(f"{PROXY_URL}/chat/completions", headers=headers, json=data)
    
    if resp.status_code != 200:
        print(f"Request failed: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    json_resp = resp.json()
    print("Response received:", json_resp)
    
    # Verify mock response content
    content = json_resp["choices"][0]["message"]["content"]
    assert "mock response" in content
    print("✅ Proxy response verified")
    
    return json_resp["id"]

def verify_database(request_id):
    print("Verifying database record...")
    # It might take a moment for async write
    time.sleep(2)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM litellm_usage WHERE request_id = %s", (request_id,))
        row = cur.fetchone()
        
        if not row:
            print("❌ No DB record found for request_id:", request_id)
            # Dump all rows for debugging
            cur.execute("SELECT * FROM litellm_usage")
            all_rows = cur.fetchall()
            print("All rows:", all_rows)
            sys.exit(1)
            
        print("DB Row:", dict(row))
        
        # Verify fields
        assert row["model"] == "gpt-4o"
        assert row["total_tokens"] == 30 # 10 prompt + 20 mock completion
        assert row["request_id"] == request_id
        
        print("✅ Database record verified")
        conn.close()
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        sys.exit(1)

def main():
    try:
        wait_for_proxy()
        
        # We need to apply schema first!
        # In this setup, we can rely on a migration container or apply it here via python
        # Let's apply it here for simplicity
        print("Applying schema...")
        conn = psycopg2.connect(**DB_CONFIG)
        with open("../../db/schema.sql", "r") as f:
            sql = f.read()
            # Split by ';' if needed or run as full script
            # psycopg2 execute can run multiple statements usually if properly formatted
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
            cur.close()
        conn.close()
        print("Schema applied.")
        
        req_id = test_proxy_request()
        verify_database(req_id)
        
        print("\n🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
