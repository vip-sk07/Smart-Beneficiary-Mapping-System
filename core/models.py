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

    class Meta:
        managed = False
        db_table = 'UserCategories'
        unique_together = ('user', 'category')

class Scheme(models.Model):
    scheme_id = models.AutoField(primary_key=True)
    scheme_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, db_column='target_category')
    eligibility_rules = models.JSONField(default=dict, blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)
    official_link = models.URLField(blank=True, null=True)
    benefit_type = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Schemes'

    def __str__(self):
        return self.scheme_name

class UserEligibility(models.Model):
    ELIGIBILITY_CHOICES = [
        ('Eligible', 'Eligible'),
        ('Not Eligible', 'Not Eligible'),
        ('Pending', 'Pending'),
    ]
    eligibility_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column='user_id')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, db_column='scheme_id')
    eligibility_status = models.CharField(max_length=20, choices=ELIGIBILITY_CHOICES, default='Pending')
    reason = models.TextField(blank=True, null=True)
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.scheme.scheme_name} ({self.eligibility_status})"

    class Meta:
        managed = False
        db_table = 'User_Eligibility'
        unique_together = ('user', 'scheme')

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
    business_turnover_limit = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, db_column='scheme_id')

    class Meta:
        managed = False
        db_table = 'Rule_Engine'
        # Optional: Add unique_together if rules are unique per category-scheme
        # unique_together = ('category', 'scheme')