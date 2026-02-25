import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

from django.db import connection

queries = [
    """
    CREATE TABLE IF NOT EXISTS Users (
        user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
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
        category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name VARCHAR(100) NOT NULL,
        description   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS UserCategories (
        user_cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INT NOT NULL,
        category_id INT NOT NULL,
        selected_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, category_id),
        FOREIGN KEY (user_id)     REFERENCES Users(user_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Schemes (
        scheme_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_name     VARCHAR(255) NOT NULL,
        description     TEXT,
        benefits        TEXT,
        target_category_id INT,
        eligibility_criteria TEXT,
        state           VARCHAR(100),
        benefit_type    VARCHAR(100),
        official_link   VARCHAR(255),
        registration_link VARCHAR(255),
        is_active       BOOLEAN DEFAULT 1,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (target_category_id) REFERENCES Categories(category_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Applications (
        app_id     INTEGER PRIMARY KEY AUTOINCREMENT,
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
        grievance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INT NOT NULL,
        scheme_id    INT,
        complaint    TEXT,
        status       VARCHAR(20) DEFAULT 'Open',
        admin_remark TEXT NULL,
        raised_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_on  TIMESTAMP NULL,
        FOREIGN KEY (user_id)   REFERENCES Users(user_id),
        FOREIGN KEY (scheme_id) REFERENCES Schemes(scheme_id)
    )
    """
]
print("Fixing SQLite DB...")
with connection.cursor() as cursor:
    for q in queries:
        cursor.execute(q)
print("Done.")
