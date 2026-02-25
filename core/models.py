from django.db import models


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Categories'

    def __str__(self):
        return self.category_name


class CustomUser(models.Model):
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    dob = models.DateField()
    gender = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    aadhaar_no = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    income = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    education = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'Users'

    def __str__(self):
        return self.name


class UserCategories(models.Model):
    user_cat_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column='user_id')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id')
    selected_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'UserCategories'
        unique_together = ('user', 'category')


class Scheme(models.Model):
    scheme_id = models.AutoField(primary_key=True)
    scheme_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_category = models.ForeignKey(
        Category, on_delete=models.DO_NOTHING, db_column='target_category'
    )
    eligibility_rules = models.JSONField(default=dict, blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)
    official_link = models.URLField(max_length=500, blank=True, null=True)
    registration_link = models.URLField(max_length=500, blank=True, null=True)
    benefit_type = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    # is_active removed: column does not exist in Railway MySQL
    # Will be re-added after DB migration is fixed

    class Meta:
        managed = False
        db_table = 'Schemes'

    def __str__(self):
        return self.scheme_name


class Announcement(models.Model):
    message = models.TextField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False   # Table created by run_setup.py, not by Django migrations
        db_table = 'Announcements'

    def __str__(self):
        return f"Announcement (Active: {self.is_active})"


class UserEligibility(models.Model):
    ELIGIBILITY_CHOICES = [
        ('Eligible', 'Eligible'),
        ('Not Eligible', 'Not Eligible'),
        ('Pending', 'Pending'),
    ]
    eligibility_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column='user_id')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, db_column='scheme_id')
    eligibility_status = models.CharField(
        max_length=20, choices=ELIGIBILITY_CHOICES, default='Pending'
    )
    reason = models.TextField(blank=True, null=True)
    applied_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'User_Eligibility'
        unique_together = ('user', 'scheme')

    def __str__(self):
        return f"{self.user.name} - {self.scheme.scheme_name} ({self.eligibility_status})"


class RuleEngine(models.Model):
    rule_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id')
    age_min = models.IntegerField(blank=True, null=True)
    age_max = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    min_income = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    max_income = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    pension_status = models.BooleanField(blank=True, null=True)
    disability_cert = models.BooleanField(blank=True, null=True)
    unemployment_status = models.BooleanField(blank=True, null=True)
    education_required = models.CharField(max_length=100, blank=True, null=True)
    business_turnover_limit = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True
    )
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, db_column='scheme_id')

    class Meta:
        managed = False
        db_table = 'Rule_Engine'


# ── NEW MODELS ─────────────────────────────────────────────────────────────

class Application(models.Model):
    STATUS_CHOICES = [
        ('Pending',  'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Withdrawn', 'Withdrawn'),
    ]
    app_id     = models.AutoField(primary_key=True)
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column='user_id')
    scheme     = models.ForeignKey(Scheme, on_delete=models.CASCADE, db_column='scheme_id')
    status     = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    remarks    = models.TextField(blank=True, null=True)
    applied_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False          # table already exists in MySQL (created by schema.py)
        db_table = 'Applications'

    def __str__(self):
        return f"BB-{self.app_id} | {self.user.name} → {self.scheme.scheme_name}"


class Grievance(models.Model):
    STATUS_CHOICES = [
        ('Open',     'Open'),
        ('Resolved', 'Resolved'),
    ]
    grievance_id = models.AutoField(primary_key=True)
    user         = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column='user_id')
    scheme       = models.ForeignKey(Scheme, on_delete=models.CASCADE,
                                     db_column='scheme_id', blank=True, null=True)
    complaint    = models.TextField()
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    admin_remark = models.TextField(blank=True, null=True)
    raised_on    = models.DateTimeField(auto_now_add=True)
    resolved_on  = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False          # table already exists in MySQL (created by schema.py)
        db_table = 'Grievances'

    def __str__(self):
        return f"GRV-{self.grievance_id} | {self.user.name} ({self.status})"