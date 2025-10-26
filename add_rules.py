import mysql.connector

# Connect to DB
db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2006",
    database="smart_beneficiary_system"
)

cursor = db.cursor()

# Step 1: Delete all existing rules (clears excess/duplicates safely)
cursor.execute("DELETE FROM Rule_Engine")
print("Deleted all existing rules (cleared excess).")

# Step 2: Fetch all schemes and their categories
cursor.execute("""
    SELECT s.scheme_id, s.scheme_name, c.category_id, c.category_name 
    FROM Schemes s 
    JOIN Categories c ON s.target_category = c.category_id
""")
schemes = cursor.fetchall()

print(f"Processing {len(schemes)} schemes with real eligibility criteria...")

count = 0
for scheme_id, scheme_name, category_id, category_name in schemes:
    # Real-world eligibility criteria based on actual schemes (annual income in ₹, age in years)
    if category_name == "Student":
        # NSP: Income ≤ ₹2.5L, age 15-35, Indian citizen, 50% marks for some
        age_min, age_max = 15, 35
        max_income = 250000.00
        education = "Any"  # Class 1+
        gender = None  # Any
        location = None  # Any
        min_income = 0.00
    elif category_name == "Farmer":
        # PM-Kisan: Landholding <2 ha, not institutional, Indian resident
        age_min, age_max = 18, None
        max_income = None  # No strict limit
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "Fishermen":
        # Kerala Fishermen: Registered, full-time, BPL, age 18-60
        age_min, age_max = 18, 60
        max_income = 150000.00  # BPL
        education = "Any"
        gender = None
        location = None  # Kerala preferred
        min_income = 0.00
    elif category_name == "Pregnant & Lactating Mothers":
        # JSY/PMMVY: Age 19+, BPL/SC/ST, up to 2 births, institutional delivery
        age_min, age_max = 19, 45
        max_income = 100000.00  # BPL
        education = "Any"
        gender = 'Female'
        location = None
        min_income = 0.00
    elif category_name == "Women":
        # Kudumbashree: BPL women, age 18+, SHG member
        age_min, age_max = 18, 60
        max_income = 150000.00  # BPL
        education = "Any"
        gender = 'Female'
        location = None  # Kerala
        min_income = 0.00
    elif category_name == "Elderly":
        # Rajasthan Senior Concession: Age 60+, resident
        age_min, age_max = 60, None
        max_income = None
        education = "Any"
        gender = None
        location = None  # Rajasthan
        min_income = 0.00
    elif category_name == "Disabled":
        # UDID: 40%+ disability, Indian citizen, no age/income limit
        age_min, age_max = None, None
        max_income = None
        education = "Any"
        gender = None
        location = None
        min_income = None
    elif category_name == "Unemployed Youth":
        # Bihar Allowance: Age 20-25, intermediate/graduate, resident, income <3L
        age_min, age_max = 20, 25
        max_income = 300000.00
        education = "Graduate"  # For allowance
        gender = None
        location = None  # Bihar
        min_income = 0.00
    elif category_name == "Small Business":
        # Karnataka MSME: MSME definition, resident, age 18+, turnover <5Cr
        age_min, age_max = 18, 55
        max_income = 5000000.00  # Turnover limit
        education = "Any"
        gender = None
        location = None  # Karnataka
        min_income = 0.00
    elif category_name == "Migrant Workers":
        # e-Shram: Age 15-59, BPL, unorganized workers
        age_min, age_max = 15, 59
        max_income = 120000.00  # BPL
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "Scheduled Tribes":
        # ST-specific: BPL, resident, no age limit
        age_min, age_max = None, None
        max_income = 100000.00  # BPL
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "Scheduled Castes":
        # SC-specific: BPL, resident, no age limit
        age_min, age_max = None, None
        max_income = 100000.00  # BPL
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "Rural":
        # PMAY Rural: BPL rural households, age 18+
        age_min, age_max = 18, None
        max_income = 150000.00  # BPL
        education = "Any"
        gender = None
        location = "Rural"
        min_income = 0.00
    elif category_name == "Women/SC/ST":
        # Targeted: BPL women/SC/ST, age 18-60
        age_min, age_max = 18, 60
        max_income = 120000.00  # BPL
        education = "Any"
        gender = 'Female'
        location = None
        min_income = 0.00
    elif category_name == "Low Income Families":
        # BPL families: Income <1L, no age limit
        age_min, age_max = None, None
        max_income = 100000.00
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "Old Age Pension":
        # NSAP: Age 60+, BPL
        age_min, age_max = 60, None
        max_income = 100000.00  # BPL
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "Low-income Families":
        # Duplicate of Low Income, BPL
        age_min, age_max = None, None
        max_income = 100000.00
        education = "Any"
        gender = None
        location = None
        min_income = 0.00
    elif category_name == "General":
        # No special limits
        age_min, age_max = None, None
        max_income = None
        education = "Any"
        gender = None
        location = None
        min_income = None
    else:
        # Default flexible
        age_min, age_max = None, None
        max_income = None
        education = "Any"
        gender = None
        location = None
        min_income = None

    cursor.execute("""
        INSERT INTO Rule_Engine (category_id, age_min, age_max, gender, location, min_income, max_income, education_required, scheme_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        age_min = VALUES(age_min), age_max = VALUES(age_max), gender = VALUES(gender), 
        location = VALUES(location), min_income = VALUES(min_income), max_income = VALUES(max_income),
        education_required = VALUES(education_required)
    """, (category_id, age_min, age_max, gender, location, min_income, max_income, education, scheme_id))
    count += 1

db.commit()
cursor.close()
db.close()

print(f"Added/Updated {count} real-world rules for schemes (no duplicates)!")