"""
Directly connects to Railway MySQL and shows column list for each table.
Run: python check_db.py
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass

import mysql.connector

db = mysql.connector.connect(
    host=os.environ.get('MYSQLHOST', 'localhost'),
    port=int(os.environ.get('MYSQLPORT', 3306)),
    user=os.environ.get('MYSQLUSER', 'root'),
    password=os.environ.get('MYSQLPASSWORD', ''),
    database=os.environ.get('MYSQLDATABASE', 'railway'),
    connection_timeout=10,
)
cursor = db.cursor()

tables = ['Users', 'Rule_Engine', 'Schemes', 'Grievances', 'User_Eligibility', 'Applications']

for table in tables:
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
        cols = [row[0] for row in cursor.fetchall()]
        print(f"\n✅ {table}:")
        for c in cols:
            print(f"   - {c}")
    except Exception as e:
        print(f"\n❌ {table}: {e}")

cursor.close()
db.close()
