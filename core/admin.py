from django.contrib import admin
from .models import Category, CustomUser, UserCategories, Scheme, UserEligibility, RuleEngine, Application, Grievance


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display  = ['user_id', 'name', 'email', 'masked_aadhaar', 'gender', 'occupation', 'created_at']
    search_fields = ['name', 'email']
    readonly_fields = ['aadhaar_no', 'created_at']  # Never editable in admin
    list_per_page = 25

    @admin.display(description='Aadhaar No.')
    def masked_aadhaar(self, obj):
        if obj.aadhaar_no and len(obj.aadhaar_no) >= 4:
            return f"XXXX-XXXX-{obj.aadhaar_no[-4:]}"
        return '—'


admin.site.register(Category)
admin.site.register(UserCategories)
admin.site.register(Scheme)
admin.site.register(UserEligibility)
admin.site.register(RuleEngine)
admin.site.register(Application)
admin.site.register(Grievance)