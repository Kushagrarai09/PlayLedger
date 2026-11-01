from django.contrib import admin
from .models import Account
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "account_type", "balance_minor", "status", "created_at")
    list_filter = ("account_type", "status")
    search_fields = ("name", "owner__username")
    readonly_fields = ("owner", "account_type", "name", "balance_minor", "created_at", "updated_at")
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
