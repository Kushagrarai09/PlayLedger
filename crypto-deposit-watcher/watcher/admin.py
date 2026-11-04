from django.contrib import admin
from .models import DepositAddress, BlockCheckpoint, Deposit, LedgerEntry, WithdrawalRequest
admin.site.register(DepositAddress)
admin.site.register(BlockCheckpoint)
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display=("tx_hash","address","amount_wei","block_number","confirmations","status")
    list_filter=("status","chain_id")
admin.site.register(LedgerEntry)
admin.site.register(WithdrawalRequest)
