from django.conf import settings
from django.db import models
from django.db.models import Q

class Account(models.Model):
    class Type(models.TextChoices):
        USER_WALLET = "user_wallet", "User wallet"
        ISSUANCE = "issuance", "Virtual credit issuance"
        FEES = "fees", "Platform fees"
        CLEARING = "clearing", "Clearing"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FROZEN = "frozen", "Frozen"
        CLOSED = "closed", "Closed"

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="wallet_account")
    account_type = models.CharField(max_length=24, choices=Type.choices)
    name = models.CharField(max_length=120)
    # Signed balance: user wallets must remain >= 0; system issuance may be negative.
    balance_minor = models.BigIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(balance_minor__gte=0) | ~Q(account_type="user_wallet"), name="user_wallet_balance_nonnegative"),
            models.UniqueConstraint(fields=["account_type", "name"], condition=Q(owner__isnull=True), name="unique_system_account_name_type"),
        ]
        indexes = [models.Index(fields=["account_type", "status"], name="wallets_acc_account_5d0a2e_idx")]

    def __str__(self):
        return f"{self.name} ({self.balance_minor} credits)"
