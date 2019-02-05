from django.contrib import admin
from .models import User, Question, Choice, PromotionTransaction, VoteAudit


class ChoicesInline(admin.TabularInline):
    model = VoteAudit.choices.through
    extra = 0


class VoteAuditAdmin(admin.ModelAdmin):
    inlines = (ChoicesInline, )
    exclude = ('choices', )


admin.site.register(User)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(PromotionTransaction)
admin.site.register(VoteAudit, VoteAuditAdmin)
