import psycopg2
import sys

# AWS RDS connection details from .env
DB_CONFIG = {
    'host': 'agent-marketplace-db.cmt466aga8u0.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'user': 'postgres',
    'password': 'it371Ananda',
    'database': 'niyogen_usage_billing',
    'sslmode': 'require'
}

print("Connecting to AWS RDS...")
print(f"Host: {DB_CONFIG['host']}")
print(f"Database: {DB_CONFIG['database']}")

try:
    # First install psycopg2 if needed
    try:
        import psycopg2
    except ImportError:
        import subprocess
        print("Installing psycopg2-binary...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "--quiet"])
        import psycopg2
    
    # Connect to database
    conn = psycopg2.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        sslmode=DB_CONFIG['sslmode']
    )
    
    print("✅ Connected successfully!")
    
    # Read and apply schema
    with open('db/schema.sql', 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    print("Applying schema...")
    cursor = conn.cursor()
    cursor.execute(schema_sql)
    conn.commit()
    
    # Verify table was created
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'litellm_usage'
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Schema applied successfully!")
        print(f"✅ Table '{result[0]}' created")
        
        # Check indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'litellm_usage'
        """)
        indexes = cursor.fetchall()
        print(f"✅ Created {len(indexes)} indexes: {[idx[0] for idx in indexes]}")
    else:
        print("⚠️ Schema executed but table not found")
    
    cursor.close()
    conn.close()
    print("\n✅ All done!")
    
except psycopg2.Error as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
