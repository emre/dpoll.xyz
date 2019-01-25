from django.contrib import admin
from .models import User, Question, Choice, PromotionTransaction
from django.contrib.auth.admin import UserAdmin



class CustomUserAdmin(UserAdmin):
    list_display = ('__str__', 'username')
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'is_active', 'is_staff')
        }),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(PromotionTransaction)
