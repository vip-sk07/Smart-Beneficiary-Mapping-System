from django.contrib import admin
from .models import Category, CustomUser, UserCategories, Scheme, UserEligibility,RuleEngine

admin.site.register(Category)
admin.site.register(CustomUser)
admin.site.register(UserCategories)
admin.site.register(Scheme)
admin.site.register(UserEligibility)
admin.site.register(RuleEngine)