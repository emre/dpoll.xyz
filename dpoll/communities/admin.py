from django.contrib import admin

from .models import Community


class CommunityAdmin(admin.ModelAdmin):
    pass


admin.site.register(Community, CommunityAdmin)