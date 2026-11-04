from rest_framework import serializers
from .models import DepositAddress, Deposit, WithdrawalRequest
class DepositAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositAddress
        fields = ["id","address","derivation_index","created_at","is_active"]
        read_only_fields = fields
class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ["id","tx_hash","to_address","amount_wei","block_number","confirmations","status","detected_at","credited_at"]
        read_only_fields = fields
class WithdrawalCreateSerializer(serializers.ModelSerializer):
    amount_wei = serializers.DecimalField(max_digits=78, decimal_places=0, min_value=1)
    class Meta:
        model = WithdrawalRequest
        fields = ["id","destination","amount_wei","idempotency_key","status","requested_at"]
        read_only_fields = ["id","status","requested_at"]
    def validate_destination(self, value):
        from web3 import Web3
        if not Web3.is_address(value):
            raise serializers.ValidationError("Destination must be a valid EVM address")
        return Web3.to_checksum_address(value)
