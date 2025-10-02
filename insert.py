import mysql.connector
import csv
import json

# Connect to MySQL server
db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2006",
    database="smart_beneficiary_system"
)

cursor = db.cursor()

# Path to your CSV file (updated with provided full path)
csv_file_path = r"D:\sem-3\Mini Project\Python+DBMS\schemes_full.csv"

# Dictionary to map category names to their IDs
categories_map = {}

# Read and process the CSV
with open(csv_file_path, mode='r', encoding='utf-8') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        # Extract row data
        scheme_id_csv = int(row['scheme_id'])  # Note: We'll use AUTO_INCREMENT, so this is ignored
        scheme_name = row['scheme_name'].strip()
        category_name = row['category'].strip()
        description = row['description'].strip()
        official_link = row['official_link'].strip()
        benefit_type = row['benefit_type'].strip()
        state = row['state'].strip()

        # Handle category: insert if not exists, get or create ID
        if category_name not in categories_map:
            # Insert category if it doesn't exist
            cursor.execute(
                "INSERT IGNORE INTO Categories (category_name, description) VALUES (%s, %s)",
                (category_name, f"Beneficiary category for schemes targeting {category_name}.")
            )
            # Fetch the ID
            cursor.execute("SELECT category_id FROM Categories WHERE category_name = %s", (category_name,))
            result = cursor.fetchone()
            if result:
                categories_map[category_name] = result[0]
            else:
                # If still not found (edge case), re-query
                cursor.execute("SELECT category_id FROM Categories WHERE category_name = %s", (category_name,))
                categories_map[category_name] = cursor.fetchone()[0]
        category_id = categories_map[category_name]

        # Insert scheme into Schemes table
        # eligibility_rules: empty JSON for now (can be populated later with actual rules)
        cursor.execute("""
            INSERT INTO Schemes (
                scheme_name, description, target_category, 
                eligibility_rules, benefits, official_link, benefit_type, state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                description = VALUES(description),
                target_category = VALUES(target_category),
                eligibility_rules = VALUES(eligibility_rules),
                benefits = VALUES(benefits),
                official_link = VALUES(official_link),
                benefit_type = VALUES(benefit_type),
                state = VALUES(state)
        """, (
            scheme_name,
            description,
            category_id,
            json.dumps({}),  # Empty JSON for eligibility_rules
            benefit_type,  # Store benefit_type in benefits field
            official_link,
            benefit_type,
            state
        ))

# Commit all inserts
db.commit()

# Optional: Print summary of inserted data
cursor.execute("SELECT COUNT(*) FROM Categories")
num_categories = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM Schemes")
num_schemes = cursor.fetchone()[0]
print(f" Populated database successfully!")
print(f"   - Inserted/Updated {num_categories} unique categories.")
print(f"   - Inserted/Updated {num_schemes} schemes.")

# Close connection
cursor.close()
db.close()