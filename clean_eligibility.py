import mysql.connector

# Connect to DB
db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2006",
    database="smart_beneficiary_system"
)

cursor = db.cursor()

# Delete all User_Eligibility (clears excess)
cursor.execute("DELETE FROM User_Eligibility")
print("Deleted all User_Eligibility entries.")

# Re-trigger for your user (change name if needed)
user_name = 'Karan Raj T'  # Your user name
cursor.execute("SELECT user_id FROM Users WHERE name = %s", (user_name,))
user_result = cursor.fetchone()
if user_result:
    user_id = user_result[0]
    cursor.callproc('check_user_eligibility', [user_id])
    print(f"Re-triggered for '{user_name}' (ID {user_id}).")
else:
    print(f"User '{user_name}' not found. Run SELECT name FROM Users LIMIT 5;")

# Verify count
cursor.execute("SELECT COUNT(*) FROM User_Eligibility")
count = cursor.fetchone()[0]
print(f"User_Eligibility now has {count} entries.")

db.commit()
cursor.close()
db.close()