from django.contrib import admin
from .models import LedgerEntry, LedgerTransaction, AuditLog

class EntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0
    can_delete = False
    readonly_fields = ("account", "amount_minor", "created_at")

@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "initiated_by", "created_at")
    list_filter = ("kind", "status", "created_at")
    search_fields = ("id", "idempotency_key", "description")
    readonly_fields = ("id", "initiated_by", "idempotency_key", "request_hash", "kind", "status", "description", "reversal_of", "created_at")
    inlines = [EntryInline]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "account", "amount_minor", "created_at")
    readonly_fields = ("transaction", "account", "amount_minor", "created_at")
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "action", "target_type", "target_id", "created_at")
    readonly_fields = ("actor", "action", "target_type", "target_id", "metadata", "created_at")
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
