from rest_framework import serializers
from .models import Account

class AccountSerializer(serializers.ModelSerializer):
    available_credits = serializers.IntegerField(source="balance_minor", read_only=True)
    user_id = serializers.IntegerField(source="owner_id", read_only=True)
    class Meta:
        model = Account
        fields = ("id", "user_id", "name", "account_type", "status", "available_credits", "created_at")
