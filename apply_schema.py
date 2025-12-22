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
password = password_result.stdout.strip().replace('\ufeff', '')  # Remove BOM if present

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
with open('db/schema.sql', 'r', encoding='utf-8') as f:
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
    
    print("Connected successfully! Applying schema...")
    cursor = conn.cursor()
    cursor.execute(schema_sql)
    conn.commit()
    
    # Verify tables were created
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'litellm_usage'
    """)
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if result:
        print("✅ Schema applied successfully!")
        print(f"✅ Table 'litellm_usage' created")
    else:
        print("⚠️  Schema executed but table not found")
        
except psycopg2.Error as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
