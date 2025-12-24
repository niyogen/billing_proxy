import subprocess
import sys

# First, install psycopg2-binary if not available
try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "--quiet"])
    import psycopg2

# Get password from Secret Manager
print("Getting database password from Secret Manager...")
password_result = subprocess.run(
    ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=pgpassword'],
    capture_output=True,
    text=True,
    check=True
)
password = password_result.stdout.strip().replace('\ufeff', '')

# Get Cloud SQL IP address
print("Getting Cloud SQL IP address...")
ip_result = subprocess.run(
    ['gcloud', 'sql', 'instances', 'describe', 'litellm-billing-db', '--format=value(ipAddresses[0].ipAddress)'],
    capture_output=True,
    text=True,
    check=True
)
ip_address = ip_result.stdout.strip()
print(f"Connecting to {ip_address}...")

# Read schema file
with open('db/schema_billing.sql', 'r', encoding='utf-8') as f:
    schema_sql = f.read()

# Connect and apply schema
try:
    conn = psycopg2.connect(
        host=ip_address,
        port=5432,
        user='litellm_user',
        password=password,
        database='litellm',
        sslmode='require',
        connect_timeout=10
    )
    
    print("Connected successfully! Applying billing schema...")
    cursor = conn.cursor()
    cursor.execute(schema_sql)
    conn.commit()
    
    # Verify tables
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name IN ('customers', 'transactions')
    """)
    tables = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if len(tables) == 2:
        print("✅ Billing schema applied successfully!")
        print(f"✅ Tables created: {[t[0] for t in tables]}")
    else:
        print(f"⚠️  Some tables might be missing. Found: {tables}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
