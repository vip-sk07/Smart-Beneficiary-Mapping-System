import mysql.connector

# 1. Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2006"
)

cursor = db.cursor()

# 2. Create Database
cursor.execute("CREATE DATABASE IF NOT EXISTS smart_beneficiary_system")
cursor.execute("USE smart_beneficiary_system")

# 3. Create Tables
tables = [

    # Users
    """
    CREATE TABLE IF NOT EXISTS Users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        dob DATE NOT NULL,
        gender VARCHAR(20),
        email VARCHAR(255),
        phone VARCHAR(20),
        aadhaar_no VARCHAR(20) UNIQUE NOT NULL,
        address VARCHAR(255),
        income DECIMAL(15,2),
        occupation VARCHAR(100),
        education VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Categories
    """
    CREATE TABLE IF NOT EXISTS Categories (
        category_id INT AUTO_INCREMENT PRIMARY KEY,
        category_name VARCHAR(100) NOT NULL,
        description TEXT
    )
    """,

    # User ↔ Category
    """
    CREATE TABLE IF NOT EXISTS UserCategories (
        user_cat_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        category_id INT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """,

    # Schemes (Updated with missing fields from CSV: official_link, benefit_type, state)
    """
    CREATE TABLE IF NOT EXISTS Schemes (
        scheme_id INT AUTO_INCREMENT PRIMARY KEY,
        scheme_name VARCHAR(255) NOT NULL,
        description TEXT,
        target_category INT,
        eligibility_rules JSON,
        benefits TEXT,
        official_link VARCHAR(500),
        benefit_type VARCHAR(100),
        state VARCHAR(100),
        FOREIGN KEY (target_category) REFERENCES Categories(category_id)
    )
    """,

    # User Eligibility
    """
    CREATE TABLE IF NOT EXISTS User_Eligibility (
        eligibility_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        scheme_id INT NOT NULL,
        eligibility_status ENUM('Eligible','Not Eligible','Pending') NOT NULL DEFAULT 'Pending',
        reason TEXT,
        applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id),
        UNIQUE(user_id, scheme_id)
    )
    """,

    # Rule Engine
    """
    CREATE TABLE IF NOT EXISTS Rule_Engine (
        rule_id INT AUTO_INCREMENT PRIMARY KEY,
        category_id INT NOT NULL,
        age_min INT,
        age_max INT,
        gender VARCHAR(10),
        location VARCHAR(100),
        min_income DECIMAL(15,2),
        max_income DECIMAL(15,2),
        pension_status BOOLEAN,
        disability_cert BOOLEAN,
        unemployment_status BOOLEAN,
        education_required VARCHAR(100),
        business_turnover_limit DECIMAL(15,2),
        scheme_id INT NOT NULL,
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """,

    # Applications
    """
    CREATE TABLE IF NOT EXISTS Applications (
        app_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        scheme_id INT NOT NULL,
        status VARCHAR(50) DEFAULT 'Pending',
        remarks TEXT,
        applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id)
    )
    """,

    # Grievances
    """
    CREATE TABLE IF NOT EXISTS Grievances (
        grievance_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        scheme_id INT,
        complaint TEXT,
        status VARCHAR(20) DEFAULT 'Open',
        raised_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_on TIMESTAMP NULL,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id)
    )
    """,

    # Verification Documents
    """
    CREATE TABLE IF NOT EXISTS Verification_Documents (
        doc_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        category_id INT NOT NULL,
        doc_type VARCHAR(100),
        file_path VARCHAR(255),
        verified BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """
]

for query in tables:
    cursor.execute(query)

# 4. Drop old procedure if exists
cursor.execute("DROP PROCEDURE IF EXISTS check_user_eligibility")

# 5. Stored Procedure
procedure = """
CREATE PROCEDURE check_user_eligibility(IN p_user_id INT)
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE s_id INT;
    DECLARE c_id INT;
    DECLARE a_min, a_max INT;
    DECLARE g VARCHAR(10);
    DECLARE loc VARCHAR(100);
    DECLARE min_inc, max_inc DECIMAL(15,2);
    DECLARE edu_req VARCHAR(100);

    DECLARE u_age INT;
    DECLARE u_gender VARCHAR(20);
    DECLARE u_income DECIMAL(15,2);
    DECLARE u_address VARCHAR(255);
    DECLARE u_education VARCHAR(100);

    DECLARE cur CURSOR FOR
        SELECT r.scheme_id, r.category_id, r.age_min, r.age_max, r.gender, r.location, r.min_income, r.max_income, r.education_required
        FROM Rule_Engine r;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    -- Get user details
    SELECT TIMESTAMPDIFF(YEAR, dob, CURDATE()), gender, income, address, education
    INTO u_age, u_gender, u_income, u_address, u_education
    FROM Users WHERE user_id = p_user_id;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO s_id, c_id, a_min, a_max, g, loc, min_inc, max_inc, edu_req;
        IF done = 1 THEN
            LEAVE read_loop;
        END IF;

        SET @eligible := 'Eligible';
        SET @reason := 'Matched scheme eligibility criteria';

        -- Age check
        IF a_min IS NOT NULL AND u_age < a_min THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Age below minimum: ', a_min);
        END IF;
        IF a_max IS NOT NULL AND u_age > a_max THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Age exceeds maximum: ', a_max);
        END IF;

        -- Gender check
        IF g IS NOT NULL AND g <> '' AND u_gender <> g THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Required gender: ', g);
        END IF;

        -- Income check
        IF min_inc IS NOT NULL AND u_income < min_inc THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Income below minimum: ', min_inc);
        END IF;
        IF max_inc IS NOT NULL AND u_income > max_inc THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Income exceeds maximum: ', max_inc);
        END IF;

        -- Location check
        IF loc IS NOT NULL AND loc <> '' AND u_address NOT LIKE CONCAT('%', loc, '%') THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Must be resident of ', loc);
        END IF;

        -- Education check
        IF edu_req IS NOT NULL AND edu_req <> '' AND u_education <> edu_req THEN
            SET @eligible := 'Not Eligible';
            SET @reason := CONCAT('Required education: ', edu_req);
        END IF;

        -- Insert or update eligibility
        INSERT INTO User_Eligibility(user_id, scheme_id, eligibility_status, reason)
        VALUES (p_user_id, s_id, @eligible, @reason)
        ON DUPLICATE KEY UPDATE eligibility_status = @eligible, reason = @reason;

    END LOOP;
    CLOSE cur;
END
"""

cursor.execute(procedure)

# 6. Triggers
triggers = [
    """
    CREATE TRIGGER after_user_category_insert
    AFTER INSERT ON UserCategories
    FOR EACH ROW
    BEGIN
        CALL check_user_eligibility(NEW.user_id);
    END
    """,

    """
    CREATE TRIGGER after_user_category_update
    AFTER UPDATE ON UserCategories
    FOR EACH ROW
    BEGIN
        CALL check_user_eligibility(NEW.user_id);
    END
    """,

    """
    CREATE TRIGGER before_user_delete
    BEFORE DELETE ON Users
    FOR EACH ROW
    BEGIN
        DELETE FROM UserCategories WHERE user_id = OLD.user_id;
        DELETE FROM User_Eligibility WHERE user_id = OLD.user_id;
        DELETE FROM Applications WHERE user_id = OLD.user_id;
        DELETE FROM Grievances WHERE user_id = OLD.user_id;
        DELETE FROM Verification_Documents WHERE user_id = OLD.user_id;
    END
    """
]

for t in triggers:
    try:
        cursor.execute(t)
    except mysql.connector.Error as err:
        print(f"Trigger error: {err}")

# Commit changes
db.commit()
cursor.close()
db.close()
