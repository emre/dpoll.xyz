from django.contrib import admin
from .models import User, Question, Choice, PromotionTransaction, VoteAudit
from django.contrib.auth.admin import UserAdmin


class MyUserAdmin(UserAdmin):
    search_fields = ('username', )
    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('sp', 'vests', 'account_age', 'post_count')}),
    )


class ChoicesInline(admin.TabularInline):
    model = VoteAudit.choices.through
    extra = 0


class VoteAuditAdmin(admin.ModelAdmin):
    inlines = (ChoicesInline, )
    exclude = ('choices', )


admin.site.register(User, MyUserAdmin)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(PromotionTransaction)
admin.site.register(VoteAudit, VoteAuditAdmin)
