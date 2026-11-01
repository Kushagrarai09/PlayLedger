import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

class LedgerTransaction(models.Model):
    class Kind(models.TextChoices):
        ISSUE = "issue", "Issue virtual credits"
        TRANSFER = "transfer", "Transfer"
        REVERSAL = "reversal", "Reversal"

    class Status(models.TextChoices):
        POSTED = "posted", "Posted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_transactions")
    idempotency_key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    description = models.CharField(max_length=255, blank=True)
    reversal_of = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversed_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["initiated_by", "idempotency_key"], name="unique_actor_idempotency_key")]
        indexes = [models.Index(fields=["kind", "created_at"], name="ledger_ledger_kind_7b4fd2_idx"), models.Index(fields=["initiated_by", "created_at"], name="ledger_ledger_initi_7b88ce_idx")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind}:{self.id}"


class LedgerEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    transaction = models.ForeignKey(
        LedgerTransaction,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    account = models.ForeignKey(
        "wallets.Account",
        on_delete=models.PROTECT,
        related_name="entries",
    )
    amount_minor = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["account", "created_at"],
                name="le_account_created_idx",
            ),
            models.Index(
                fields=["transaction", "account"],
                name="le_trans_account_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount_minor=0),
                name="ledger_entry_nonzero",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk and LedgerEntry.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "Posted ledger entries are immutable; use a reversal transaction."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Posted ledger entries cannot be deleted.")


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ledger_audit_events")
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "created_at"], name="ledger_audit_action_2e4a9d_idx")]
