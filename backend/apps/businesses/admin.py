from django.contrib import admin

from .models import Branch, Business, BusinessMembership


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "business_type", "currency", "is_active", "created_at")
    search_fields = ("name", "owner_name", "email")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "is_primary", "is_active")


@admin.register(BusinessMembership)
class BusinessMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "business", "role", "is_active")
    list_filter = ("role", "is_active")
