from django.contrib import admin

from .models import Customer, CustomerPayment, Receivable


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "phone", "is_active")
    search_fields = ("name", "phone")


@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "business",
        "original_amount",
        "amount_paid",
        "due_date",
    )
    readonly_fields = ("amount_paid",)


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display = ("created_at", "business", "customer", "amount", "method")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
