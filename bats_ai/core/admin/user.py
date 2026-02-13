from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from bats_ai.core.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_select_related = ['profile']

    list_display = list(BaseUserAdmin.list_display) + ['is_verified']

    def is_verified(self, obj):
        return hasattr(obj, 'profile') and obj.profile.verified

    is_verified.boolean = True
    is_verified.short_description = 'Verified'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
