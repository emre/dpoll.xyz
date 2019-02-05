from django.contrib import admin
from .models import User, Question, Choice, PromotionTransaction, VoteAudit
from django.contrib.auth.admin import UserAdmin



class CustomUserAdmin(UserAdmin):
    list_display = ('__str__', 'username')
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'is_active', 'is_staff')
        }),
    )


class ChoicesInline(admin.TabularInline):
    model = VoteAudit.choices.through
    extra = 0


class VoteAuditAdmin(admin.ModelAdmin):
    inlines = (ChoicesInline, )
    exclude = ('choices', )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(PromotionTransaction)
admin.site.register(VoteAudit, VoteAuditAdmin)
