import mysql.connector

# Connect to MySQL server (no DB yet)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="2006"
)

cursor = db.cursor()

# 1. Create Database
cursor.execute("CREATE DATABASE IF NOT EXISTS smart_beneficiary_system")
cursor.execute("USE smart_beneficiary_system")

# 2. Tables
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

    # User ↔ Category mapping
    """
    CREATE TABLE IF NOT EXISTS UserCategories (
        user_cat_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        category_id INT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id)
    )
    """,

    # Schemes
    """
    CREATE TABLE IF NOT EXISTS Schemes (
        scheme_id INT AUTO_INCREMENT PRIMARY KEY,
        scheme_name VARCHAR(255) NOT NULL,
        description TEXT,
        target_category INT,
        eligibility_rules JSON,
        benefits TEXT,
        FOREIGN KEY (target_category) REFERENCES Categories(category_id)
    )
    """,

    # Eligibility Results
    """
    CREATE TABLE IF NOT EXISTS User_Eligibility (
        eligibility_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        scheme_id INT NOT NULL,
        eligibility_status ENUM('Eligible','Not Eligible','Pending') NOT NULL DEFAULT 'Pending',
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

# 3. Stored Procedure
cursor.execute("DROP PROCEDURE IF EXISTS check_user_eligibility")

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

    DECLARE u_age INT;
    DECLARE u_gender VARCHAR(20);
    DECLARE u_income DECIMAL(15,2);
    DECLARE u_address VARCHAR(255);

    DECLARE cur CURSOR FOR
        SELECT r.scheme_id, r.category_id, r.age_min, r.age_max, r.gender, r.location, r.min_income, r.max_income
        FROM Rule_Engine r;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    -- Get user details
    SELECT TIMESTAMPDIFF(YEAR, dob, CURDATE()), gender, income, address
    INTO u_age, u_gender, u_income, u_address
    FROM Users WHERE user_id = p_user_id;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO s_id, c_id, a_min, a_max, g, loc, min_inc, max_inc;
        IF done = 1 THEN
            LEAVE read_loop;
        END IF;

        SET @eligible := 'Eligible';

        -- Age check
        IF a_min IS NOT NULL AND u_age < a_min THEN
            SET @eligible := 'Not Eligible';
        END IF;
        IF a_max IS NOT NULL AND u_age > a_max THEN
            SET @eligible := 'Not Eligible';
        END IF;

        -- Gender check
        IF g IS NOT NULL AND g <> '' AND u_gender <> g THEN
            SET @eligible := 'Not Eligible';
        END IF;

        -- Income check
        IF min_inc IS NOT NULL AND u_income < min_inc THEN
            SET @eligible := 'Not Eligible';
        END IF;
        IF max_inc IS NOT NULL AND u_income > max_inc THEN
            SET @eligible := 'Not Eligible';
        END IF;

        -- Location check
        IF loc IS NOT NULL AND loc <> '' AND u_address NOT LIKE CONCAT('%', loc, '%') THEN
            SET @eligible := 'Not Eligible';
        END IF;

        -- Insert or update eligibility
        INSERT INTO User_Eligibility(user_id, scheme_id, eligibility_status)
        VALUES (p_user_id, s_id, @eligible)
        ON DUPLICATE KEY UPDATE eligibility_status = @eligible;

    END LOOP;
    CLOSE cur;
END
"""

cursor.execute(procedure)

# 4. Triggers
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

db.commit()
cursor.close()
db.close()

from django.db import models

class Users(models.Model):
    name = models.CharField(max_length=255)
    dob = models.DateField()
    gender = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    aadhaar_no = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Categories(models.Model):
    category_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

class UserCategories(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)

class Schemes(models.Model):
    scheme_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    target_category = models.ForeignKey(Categories, on_delete=models.CASCADE)
    eligibility_rules = models.JSONField(null=True, blank=True)
    benefits = models.TextField(null=True, blank=True)

class User_Eligibility(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Schemes, on_delete=models.CASCADE)
    eligibility_status = models.CharField(max_length=10, choices=[
        ('Eligible','Eligible'),
        ('Not Eligible','Not Eligible'),
        ('Pending','Pending')
    ], default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'scheme')

class Rule_Engine(models.Model):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)
    age_min = models.IntegerField(null=True, blank=True)
    age_max = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    min_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    max_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pension_status = models.BooleanField(null=True, blank=True)
    disability_cert = models.BooleanField(null=True, blank=True)
    unemployment_status = models.BooleanField(null=True, blank=True)
    business_turnover_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    scheme = models.ForeignKey(Schemes, on_delete=models.CASCADE)

class Applications(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Schemes, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='Pending')
    remarks = models.TextField(null=True, blank=True)
    applied_on = models.DateTimeField(auto_now_add=True)

class Grievances(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Schemes, on_delete=models.SET_NULL, null=True, blank=True)
    complaint = models.TextField()
    status = models.CharField(max_length=20, default='Open')
    raised_on = models.DateTimeField(auto_now_add=True)
    resolved_on = models.DateTimeField(null=True, blank=True)

class Verification_Documents(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=100)
    file_path = models.CharField(max_length=255, null=True, blank=True)
    verified = models.BooleanField(default=False)


from django.contrib import admin
from .models import Users, Categories, Schemes, User_Eligibility, Rule_Engine, Applications, Grievances, Verification_Documents

admin.site.register(Users)
admin.site.register(Categories)
admin.site.register(Schemes)
admin.site.register(User_Eligibility)
admin.site.register(Rule_Engine)
admin.site.register(Applications)
admin.site.register(Grievances)
admin.site.register(Verification_Documents)

from django.shortcuts import render, redirect
from .models import Schemes, Applications
from django.contrib.auth.decorators import login_required

@login_required
def scheme_list(request):
    schemes = Schemes.objects.all()
    return render(request, 'schemes/scheme_list.html', {'schemes': schemes})

@login_required
def apply_scheme(request, scheme_id):
    if request.method == 'POST':
        application = Applications.objects.create(
            user=request.user.users,  # Assumes 'users' is linked to auth.User
            scheme_id=scheme_id,
            status='Pending'
        )
        return redirect('scheme_list')
    scheme = Schemes.objects.get(id=scheme_id)
    return render(request, 'schemes/apply_scheme.html', {'scheme': scheme})

#napping urls using this . urls of scheme available
from django.urls import path
from . import views

urlpatterns = [
    path('schemes/', views.scheme_list, name='scheme_list'),
    path('schemes/apply/<int:scheme_id>/', views.apply_scheme, name='apply_scheme'),
    path('admin/', admin.site.urls),
]

