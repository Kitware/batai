from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from bats_ai.core.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_select_related = ["profile"]

    # See https://code.djangoproject.com/ticket/36926#ticket
    list_display = [*BaseUserAdmin.list_display, "is_verified"]
    list_filter = [*BaseUserAdmin.list_filter, "profile__verified"]

    @admin.display(
        boolean=True,
        description="Is Verified?",
    )
    def is_verified(self, obj):
        return obj.profile.verified
