from django.conf import settings
from django.db import models

class DepositAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deposit_addresses")
    address = models.CharField(max_length=42, unique=True)
    derivation_index = models.PositiveIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.user_id}:{self.address}"

class BlockCheckpoint(models.Model):
    chain_id = models.PositiveBigIntegerField(default=11155111)
    block_number = models.PositiveBigIntegerField(unique=True)
    block_hash = models.CharField(max_length=66)
    parent_hash = models.CharField(max_length=66)
    scanned_at = models.DateTimeField(auto_now=True)

class Deposit(models.Model):
    class Status(models.TextChoices):
        DETECTED = "DETECTED"
        CONFIRMING = "CONFIRMING"
        CONFIRMED = "CONFIRMED"
        CREDITED = "CREDITED"
        REORGED = "REORGED"
        FAILED = "FAILED"
    chain_id = models.PositiveBigIntegerField(default=11155111)
    tx_hash = models.CharField(max_length=66)
    log_index = models.PositiveIntegerField(default=0)
    address = models.ForeignKey(DepositAddress, on_delete=models.PROTECT, related_name="deposits")
    from_address = models.CharField(max_length=42)
    to_address = models.CharField(max_length=42)
    amount_wei = models.DecimalField(max_digits=78, decimal_places=0)
    block_number = models.PositiveBigIntegerField()
    block_hash = models.CharField(max_length=66)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DETECTED)
    confirmations = models.PositiveIntegerField(default=0)
    detected_at = models.DateTimeField(auto_now_add=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["chain_id","tx_hash","log_index"], name="uniq_chain_tx_event")]
        indexes = [models.Index(fields=["status","block_number"])]
    def __str__(self):
        return f"{self.tx_hash}:{self.status}"

class LedgerEntry(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "DEPOSIT"
        WITHDRAWAL_RESERVATION = "WITHDRAWAL_RESERVATION"
        WITHDRAWAL_RELEASE = "WITHDRAWAL_RELEASE"
        WITHDRAWAL_SETTLEMENT = "WITHDRAWAL_SETTLEMENT"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    reference = models.CharField(max_length=160, unique=True)
    amount_wei = models.DecimalField(max_digits=78, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED"
        RESERVED = "RESERVED"
        APPROVED = "APPROVED"
        BROADCAST = "BROADCAST"
        CONFIRMED = "CONFIRMED"
        REJECTED = "REJECTED"
        FAILED = "FAILED"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="withdrawals")
    destination = models.CharField(max_length=42)
    amount_wei = models.DecimalField(max_digits=78, decimal_places=0)
    idempotency_key = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="approved_withdrawals", blank=True)
    tx_hash = models.CharField(max_length=66, blank=True)
    error = models.TextField(blank=True)
    class Meta:
        indexes = [models.Index(fields=["status","requested_at"])]
