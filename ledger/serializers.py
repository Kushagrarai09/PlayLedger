from rest_framework import serializers
from .models import LedgerEntry, LedgerTransaction

class LedgerEntrySerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    class Meta:
        model = LedgerEntry
        fields = ("id", "account", "account_name", "amount_minor", "created_at")

class TransactionSerializer(serializers.ModelSerializer):
    entries = LedgerEntrySerializer(many=True, read_only=True)
    class Meta:
        model = LedgerTransaction
        fields = ("id", "kind", "status", "description", "created_at", "entries", "reversal_of")
