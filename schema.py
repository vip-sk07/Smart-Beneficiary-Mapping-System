"""
schema.py
Run this ONCE to create all tables, procedures, and triggers.
Usage: python schema.py
"""
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2006"
)
cursor = db.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS smart_beneficiary_system")
cursor.execute("USE smart_beneficiary_system")

# ── Tables ─────────────────────────────────────────────────────────────────
tables = [
    """
    CREATE TABLE IF NOT EXISTS Users (
        user_id    INT AUTO_INCREMENT PRIMARY KEY,
        name       VARCHAR(255) NOT NULL,
        dob        DATE NOT NULL,
        gender     VARCHAR(20),
        email      VARCHAR(255),
        phone      VARCHAR(20),
        aadhaar_no VARCHAR(20) UNIQUE NOT NULL,
        address    VARCHAR(255),
        income     DECIMAL(15,2),
        occupation VARCHAR(100),
        education  VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Categories (
        category_id   INT AUTO_INCREMENT PRIMARY KEY,
        category_name VARCHAR(100) NOT NULL,
        description   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS UserCategories (
        user_cat_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NOT NULL,
        category_id INT NOT NULL,
        selected_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_cat (user_id, category_id),
        FOREIGN KEY (user_id)     REFERENCES Users(user_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Schemes (
        scheme_id         INT AUTO_INCREMENT PRIMARY KEY,
        scheme_name       VARCHAR(255) NOT NULL,
        description       TEXT,
        target_category   INT,
        eligibility_rules JSON,
        benefits          TEXT,
        official_link     VARCHAR(500),
        registration_link VARCHAR(500),
        benefit_type      VARCHAR(100),
        state             VARCHAR(100),
        FOREIGN KEY (target_category) REFERENCES Categories(category_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Rule_Engine (
        rule_id                 INT AUTO_INCREMENT PRIMARY KEY,
        scheme_id               INT NOT NULL,
        category_id             INT NOT NULL,
        age_min                 INT,
        age_max                 INT,
        gender                  VARCHAR(10),
        location                VARCHAR(100),
        min_income              DECIMAL(15,2),
        max_income              DECIMAL(15,2),
        education_required      VARCHAR(100),
        pension_status          BOOLEAN,
        disability_cert         BOOLEAN,
        unemployment_status     BOOLEAN,
        business_turnover_limit DECIMAL(15,2),
        FOREIGN KEY (scheme_id)   REFERENCES Schemes(scheme_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS User_Eligibility (
        eligibility_id     INT AUTO_INCREMENT PRIMARY KEY,
        user_id            INT NOT NULL,
        scheme_id          INT NOT NULL,
        eligibility_status ENUM('Eligible','Not Eligible','Pending') NOT NULL DEFAULT 'Pending',
        reason             TEXT,
        applied_on         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_scheme (user_id, scheme_id),
        FOREIGN KEY (user_id)   REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Applications (
        app_id     INT AUTO_INCREMENT PRIMARY KEY,
        user_id    INT NOT NULL,
        scheme_id  INT NOT NULL,
        status     VARCHAR(50) DEFAULT 'Pending',
        remarks    TEXT,
        applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id)   REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Grievances (
        grievance_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id      INT NOT NULL,
        scheme_id    INT,
        complaint    TEXT,
        status       VARCHAR(20) DEFAULT 'Open',
        raised_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_on  TIMESTAMP NULL,
        FOREIGN KEY (user_id)   REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS SchemeAuditLog (
        log_id      INT AUTO_INCREMENT PRIMARY KEY,
        scheme_id   INT NOT NULL,
        action      VARCHAR(50),
        action_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_scheme (scheme_id)
    )
    """,
]

for t in tables:
    cursor.execute(t)
    db.commit()
print("✅ All tables created.")

# If Schemes table already exists but lacks registration_link, add it
try:
    cursor.execute("ALTER TABLE Schemes ADD COLUMN registration_link VARCHAR(500)")
    db.commit()
    print("✅ Added registration_link column to existing Schemes table.")
except Exception:
    pass  # Column already exists — that's fine

# ── Drop existing procedures & triggers ────────────────────────────────────
for proc in ["check_user_eligibility", "get_user_eligible_schemes", "get_schemes_by_category"]:
    cursor.execute(f"DROP PROCEDURE IF EXISTS {proc}")
for trig in [
    "trg_after_usercategory_insert", "trg_after_usercategory_delete",
    "trg_before_user_delete", "trg_after_scheme_insert", "trg_after_rule_update",
    "after_user_category_insert", "after_user_category_update", "before_user_delete"
]:
    cursor.execute(f"DROP TRIGGER IF EXISTS {trig}")
db.commit()
print("✅ Old procedures & triggers dropped.")

# ── Stored Procedure 1: check_user_eligibility ───────────────────────────
cursor.execute("""
CREATE PROCEDURE check_user_eligibility(IN p_user_id INT)
BEGIN
    DECLARE v_done        INT DEFAULT 0;
    DECLARE v_scheme_id   INT;
    DECLARE v_category_id INT;
    DECLARE v_age_min     INT;
    DECLARE v_age_max     INT;
    DECLARE v_gender      VARCHAR(20);
    DECLARE v_location    VARCHAR(100);
    DECLARE v_min_income  DECIMAL(15,2);
    DECLARE v_max_income  DECIMAL(15,2);
    DECLARE v_edu_req     VARCHAR(100);
    DECLARE v_pension     BOOLEAN;
    DECLARE v_disability  BOOLEAN;
    DECLARE v_unemployed  BOOLEAN;
    DECLARE v_turnover    DECIMAL(15,2);

    DECLARE u_age         INT;
    DECLARE u_gender      VARCHAR(20);
    DECLARE u_income      DECIMAL(15,2);
    DECLARE u_address     VARCHAR(255);
    DECLARE u_education   VARCHAR(100);

    DECLARE rule_cur CURSOR FOR
        SELECT r.scheme_id, r.category_id,
               r.age_min, r.age_max, r.gender, r.location,
               r.min_income, r.max_income, r.education_required,
               r.pension_status, r.disability_cert,
               r.unemployment_status, r.business_turnover_limit
        FROM   Rule_Engine r
        WHERE  r.category_id IN (
                   SELECT category_id FROM UserCategories WHERE user_id = p_user_id
               );

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    SELECT TIMESTAMPDIFF(YEAR, dob, CURDATE()),
           gender, income, address, education
    INTO   u_age, u_gender, u_income, u_address, u_education
    FROM   Users
    WHERE  user_id = p_user_id;

    OPEN rule_cur;
    eligibility_loop: LOOP
        FETCH rule_cur INTO
            v_scheme_id, v_category_id,
            v_age_min, v_age_max, v_gender, v_location,
            v_min_income, v_max_income, v_edu_req,
            v_pension, v_disability, v_unemployed, v_turnover;

        IF v_done = 1 THEN LEAVE eligibility_loop; END IF;

        SET @status = 'Eligible';
        SET @reason = 'Matched all eligibility criteria';

        IF v_age_min IS NOT NULL AND u_age < v_age_min THEN
            SET @status = 'Not Eligible';
            SET @reason = CONCAT('Minimum age required: ', v_age_min, ' years');
        ELSEIF v_age_max IS NOT NULL AND u_age > v_age_max THEN
            SET @status = 'Not Eligible';
            SET @reason = CONCAT('Maximum age allowed: ', v_age_max, ' years');
        ELSEIF v_gender IS NOT NULL AND v_gender <> ''
               AND LOWER(u_gender) <> LOWER(v_gender) THEN
            SET @status = 'Not Eligible';
            SET @reason = CONCAT('Scheme is for ', v_gender, ' only');
        ELSEIF v_max_income IS NOT NULL AND u_income > v_max_income THEN
            SET @status = 'Not Eligible';
            SET @reason = CONCAT('Annual income must be <= Rs.', v_max_income);
        ELSEIF v_location IS NOT NULL AND v_location <> ''
               AND u_address NOT LIKE CONCAT('%', v_location, '%') THEN
            SET @status = 'Not Eligible';
            SET @reason = CONCAT('Available only in ', v_location);
        ELSEIF v_edu_req IS NOT NULL AND v_edu_req <> ''
               AND UPPER(v_edu_req) <> 'ANY' THEN
            -- Education hierarchy: higher qualification satisfies lower requirement
            -- Levels: 10th=1, 12th=2, Diploma=3, Graduate=4, Postgraduate=5, PhD=6
            SET @u_edu_level = CASE
                WHEN LOWER(u_education) LIKE '%phd%'                        THEN 6
                WHEN LOWER(u_education) LIKE '%postgrad%'
                  OR LOWER(u_education) LIKE '%post grad%'
                  OR LOWER(u_education) LIKE '%post-grad%'
                  OR LOWER(u_education) LIKE '%m.tech%'
                  OR LOWER(u_education) LIKE '%mtech%'
                  OR LOWER(u_education) LIKE '%mba%'
                  OR LOWER(u_education) LIKE '%masters%'
                  OR LOWER(u_education) LIKE '%m.sc%'                       THEN 5
                WHEN LOWER(u_education) LIKE '%graduat%'
                  OR LOWER(u_education) LIKE '%b.tech%'
                  OR LOWER(u_education) LIKE '%btech%'
                  OR LOWER(u_education) LIKE '%b.sc%'
                  OR LOWER(u_education) LIKE '%b.com%'
                  OR LOWER(u_education) LIKE '%b.a%'
                  OR LOWER(u_education) LIKE '%degree%'                     THEN 4
                WHEN LOWER(u_education) LIKE '%diploma%'
                  OR LOWER(u_education) LIKE '%polytechnic%'                THEN 3
                WHEN LOWER(u_education) LIKE '%12%'
                  OR LOWER(u_education) LIKE '%hsc%'
                  OR LOWER(u_education) LIKE '%higher secondary%'
                  OR LOWER(u_education) LIKE '%plus two%'
                  OR LOWER(u_education) LIKE '%intermediate%'               THEN 2
                WHEN LOWER(u_education) LIKE '%10%'
                  OR LOWER(u_education) LIKE '%sslc%'
                  OR LOWER(u_education) LIKE '%matric%'
                  OR LOWER(u_education) LIKE '%secondary%'                  THEN 1
                ELSE 0
            END;
            SET @r_edu_level = CASE
                WHEN LOWER(v_edu_req) LIKE '%phd%'                          THEN 6
                WHEN LOWER(v_edu_req) LIKE '%postgrad%'
                  OR LOWER(v_edu_req) LIKE '%post grad%'
                  OR LOWER(v_edu_req) LIKE '%post-grad%'
                  OR LOWER(v_edu_req) LIKE '%masters%'                      THEN 5
                WHEN LOWER(v_edu_req) LIKE '%graduat%'
                  OR LOWER(v_edu_req) LIKE '%degree%'                       THEN 4
                WHEN LOWER(v_edu_req) LIKE '%diploma%'
                  OR LOWER(v_edu_req) LIKE '%polytechnic%'                  THEN 3
                WHEN LOWER(v_edu_req) LIKE '%12%'
                  OR LOWER(v_edu_req) LIKE '%hsc%'
                  OR LOWER(v_edu_req) LIKE '%higher secondary%'
                  OR LOWER(v_edu_req) LIKE '%12th pass%'
                  OR LOWER(v_edu_req) LIKE '%intermediate%'                 THEN 2
                WHEN LOWER(v_edu_req) LIKE '%10%'
                  OR LOWER(v_edu_req) LIKE '%sslc%'
                  OR LOWER(v_edu_req) LIKE '%matric%'
                  OR LOWER(v_edu_req) LIKE '%secondary%'                    THEN 1
                ELSE 0
            END;
            IF @u_edu_level < @r_edu_level THEN
                SET @status = 'Not Eligible';
                SET @reason = CONCAT('Required education: ', v_edu_req);
            END IF;
        END IF;

        INSERT INTO User_Eligibility (user_id, scheme_id, eligibility_status, reason)
        VALUES (p_user_id, v_scheme_id, @status, @reason)
        ON DUPLICATE KEY UPDATE
            eligibility_status = @status,
            reason             = @reason,
            applied_on         = CURRENT_TIMESTAMP;

    END LOOP;
    CLOSE rule_cur;
END
""")
db.commit()
print("✅ Procedure check_user_eligibility created.")

# ── Stored Procedure 2: get_user_eligible_schemes ─────────────────────────
cursor.execute("""
CREATE PROCEDURE get_user_eligible_schemes(IN p_user_id INT)
BEGIN
    SELECT s.scheme_id, s.scheme_name, s.description,
           s.benefits, s.benefit_type, s.state, s.official_link, s.registration_link,
           c.category_name,
           ue.eligibility_status, ue.reason, ue.applied_on
    FROM   User_Eligibility ue
    JOIN   Schemes    s ON s.scheme_id    = ue.scheme_id
    JOIN   Categories c ON c.category_id = s.target_category
    WHERE  ue.user_id           = p_user_id
      AND  ue.eligibility_status = 'Eligible'
    ORDER  BY c.category_name, s.scheme_name;
END
""")
db.commit()
print("✅ Procedure get_user_eligible_schemes created.")

# ── Stored Procedure 3: get_schemes_by_category ───────────────────────────
cursor.execute("""
CREATE PROCEDURE get_schemes_by_category(IN p_category_id INT)
BEGIN
    SELECT s.scheme_id, s.scheme_name, s.description,
           s.benefits, s.benefit_type, s.state, s.official_link, s.registration_link
    FROM   Schemes s
    WHERE  s.target_category = p_category_id
    ORDER  BY s.scheme_name;
END
""")
db.commit()
print("✅ Procedure get_schemes_by_category created.")

# ── Trigger 1: Auto eligibility check on category insert ─────────────────
cursor.execute("""
CREATE TRIGGER trg_after_usercategory_insert
AFTER INSERT ON UserCategories
FOR EACH ROW
BEGIN
    CALL check_user_eligibility(NEW.user_id);
END
""")
db.commit()
print("✅ Trigger trg_after_usercategory_insert created.")

# ── Trigger 2: Clean eligibility on category delete ───────────────────────
cursor.execute("""
CREATE TRIGGER trg_after_usercategory_delete
AFTER DELETE ON UserCategories
FOR EACH ROW
BEGIN
    DELETE FROM User_Eligibility
    WHERE user_id   = OLD.user_id
      AND scheme_id IN (
              SELECT scheme_id FROM Schemes
              WHERE  target_category = OLD.category_id
          );
END
""")
db.commit()
print("✅ Trigger trg_after_usercategory_delete created.")

# ── Trigger 3: Cascade clean before user delete ────────────────────────────
cursor.execute("""
CREATE TRIGGER trg_before_user_delete
BEFORE DELETE ON Users
FOR EACH ROW
BEGIN
    DELETE FROM User_Eligibility WHERE user_id = OLD.user_id;
    DELETE FROM UserCategories    WHERE user_id = OLD.user_id;
    DELETE FROM Applications      WHERE user_id = OLD.user_id;
    DELETE FROM Grievances        WHERE user_id = OLD.user_id;
END
""")
db.commit()
print("✅ Trigger trg_before_user_delete created.")

# ── Trigger 4: Audit log on new scheme insert ─────────────────────────────
cursor.execute("""
CREATE TRIGGER trg_after_scheme_insert
AFTER INSERT ON Schemes
FOR EACH ROW
BEGIN
    INSERT INTO SchemeAuditLog (scheme_id, action, action_time)
    VALUES (NEW.scheme_id, 'INSERTED', NOW());
END
""")
db.commit()
print("✅ Trigger trg_after_scheme_insert created.")

# ── Trigger 5: Re-run eligibility when a rule changes ─────────────────────
cursor.execute("""
CREATE TRIGGER trg_after_rule_update
AFTER UPDATE ON Rule_Engine
FOR EACH ROW
BEGIN
    DECLARE v_done    INT DEFAULT 0;
    DECLARE v_user_id INT;
    DECLARE user_cur CURSOR FOR
        SELECT DISTINCT user_id FROM UserCategories
        WHERE  category_id = NEW.category_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    OPEN user_cur;
    recheck_loop: LOOP
        FETCH user_cur INTO v_user_id;
        IF v_done = 1 THEN LEAVE recheck_loop; END IF;
        CALL check_user_eligibility(v_user_id);
    END LOOP;
    CLOSE user_cur;
END
""")
db.commit()
print("✅ Trigger trg_after_rule_update created.")

cursor.close()
db.close()
print("\n🎉 Schema setup complete! Now run: python Load.py")