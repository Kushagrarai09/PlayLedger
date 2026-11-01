import hashlib
import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from wallets.models import Account
from .models import LedgerEntry, LedgerTransaction

User = get_user_model()

class LedgerError(Exception):
    """A safe, expected business-rule failure."""

def _fingerprint(payload):
    packed = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(packed.encode()).hexdigest()

def _existing(actor, key, fingerprint, kind):
    previous = LedgerTransaction.objects.filter(initiated_by=actor, idempotency_key=key).first()
    if previous:
        if previous.request_hash != fingerprint or previous.kind != kind:
            raise LedgerError("This idempotency key was already used for a different request.")
        return previous
    return None

def _validate_key(key):
    if not key or len(key) > 128 or not key.strip():
        raise LedgerError("A non-empty Idempotency-Key header (max 128 characters) is required.")

def _create_transaction(actor, key, fingerprint, kind, description=""):
    return LedgerTransaction.objects.create(initiated_by=actor, idempotency_key=key,
        request_hash=fingerprint, kind=kind, status=LedgerTransaction.Status.POSTED, description=description)

def _locked_accounts(ids):
    rows = Account.objects.select_for_update().filter(id__in=sorted(set(ids))).order_by("id")
    return {a.id: a for a in rows}

def _post_entries(txn, pairs):
    if not pairs or sum(amount for _, amount in pairs) != 0:
        raise LedgerError("Ledger invariant failed: transaction entries must sum to zero.")
    LedgerEntry.objects.bulk_create([LedgerEntry(transaction=txn, account=account, amount_minor=amount) for account, amount in pairs if amount != 0])

def issue_credits(*, actor, recipient_user_id, amount, idempotency_key, description="Initial virtual credits"):
    """Staff-only operation; caller must enforce actor.is_staff in the API layer."""
    _validate_key(idempotency_key)
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise LedgerError("Amount must be a positive integer number of credits.")
    payload = {"kind": "issue", "recipient_user_id": int(recipient_user_id), "amount": amount, "description": description or ""}
    fingerprint = _fingerprint(payload)
    with transaction.atomic():
        existing = _existing(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.ISSUE)
        if existing:
            return existing, True
        recipient = Account.objects.filter(owner_id=recipient_user_id, account_type=Account.Type.USER_WALLET).first()
        if not recipient:
            raise LedgerError("Recipient wallet not found.")
        system = Account.objects.filter(owner__isnull=True, account_type=Account.Type.ISSUANCE, name="Virtual credit issuance").first()
        if not system:
            raise LedgerError("System issuance account is missing. Run `python manage.py bootstrap_system_accounts`.")
        locked = _locked_accounts([recipient.id, system.id])
        recipient, system = locked[recipient.id], locked[system.id]
        if recipient.status != Account.Status.ACTIVE:
            raise LedgerError("Recipient wallet is not active.")
        existing = _existing(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.ISSUE)
        if existing:
            return existing, True
        txn = _create_transaction(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.ISSUE, description)
        recipient.balance_minor += amount
        system.balance_minor -= amount
        recipient.save(update_fields=["balance_minor", "updated_at"])
        system.save(update_fields=["balance_minor", "updated_at"])
        _post_entries(txn, [(system, -amount), (recipient, amount)])
        return txn, False

def transfer_credits(*, actor, recipient_user_id, amount, idempotency_key, description=""):
    _validate_key(idempotency_key)
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise LedgerError("Amount must be a positive integer number of credits.")
    if int(recipient_user_id) == actor.id:
        raise LedgerError("You cannot transfer credits to yourself.")
    payload = {"kind": "transfer", "recipient_user_id": int(recipient_user_id), "amount": amount, "description": description or ""}
    fingerprint = _fingerprint(payload)
    with transaction.atomic():
        existing = _existing(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.TRANSFER)
        if existing:
            return existing, True
        sender = Account.objects.filter(owner=actor, account_type=Account.Type.USER_WALLET).first()
        recipient = Account.objects.filter(owner_id=recipient_user_id, account_type=Account.Type.USER_WALLET).first()
        if not sender or not recipient:
            raise LedgerError("Sender or recipient wallet not found.")
        locked = _locked_accounts([sender.id, recipient.id])
        sender, recipient = locked[sender.id], locked[recipient.id]
        # Re-check after acquiring the sender lock to serialize retries from the same actor.
        existing = _existing(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.TRANSFER)
        if existing:
            return existing, True
        if sender.status != Account.Status.ACTIVE or recipient.status != Account.Status.ACTIVE:
            raise LedgerError("Both wallets must be active.")
        if sender.balance_minor < amount:
            raise LedgerError("Insufficient funds.")
        txn = _create_transaction(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.TRANSFER, description)
        sender.balance_minor -= amount
        recipient.balance_minor += amount
        sender.save(update_fields=["balance_minor", "updated_at"])
        recipient.save(update_fields=["balance_minor", "updated_at"])
        _post_entries(txn, [(sender, -amount), (recipient, amount)])
        return txn, False

def reverse_transaction(*, actor, transaction_id, idempotency_key):
    _validate_key(idempotency_key)
    payload = {"kind": "reversal", "transaction_id": str(transaction_id)}
    fingerprint = _fingerprint(payload)
    with transaction.atomic():
        existing = _existing(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.REVERSAL)
        if existing:
            return existing, True
        original = LedgerTransaction.objects.select_for_update().filter(id=transaction_id).first()
        if not original:
            raise LedgerError("Transaction not found.")
        if hasattr(original, "reversed_by"):
            raise LedgerError("This transaction has already been reversed.")
        entries = list(original.entries.select_related("account").order_by("account_id"))
        accounts = _locked_accounts([e.account_id for e in entries])
        txn = _create_transaction(actor, idempotency_key, fingerprint, LedgerTransaction.Kind.REVERSAL, f"Reversal of {original.id}")
        for entry in entries:
            account = accounts[entry.account_id]
            new_balance = account.balance_minor - entry.amount_minor
            if account.account_type == Account.Type.USER_WALLET and new_balance < 0:
                raise LedgerError("Reversal would make a user wallet negative.")
            account.balance_minor = new_balance
            account.save(update_fields=["balance_minor", "updated_at"])
        _post_entries(txn, [(accounts[e.account_id], -e.amount_minor) for e in entries])
        # The reversal transaction points back to the original transaction.
        txn.reversal_of = original
        txn.save(update_fields=["reversal_of"])
        return txn, False

def reconciliation_report():
    """Read-only checks. An empty discrepancy list means the checks passed."""
    unbalanced = []
    for txn in LedgerTransaction.objects.all().iterator():
        total = txn.entries.aggregate(total=Sum("amount_minor"))["total"] or 0
        count = txn.entries.count()
        if total != 0 or count < 2:
            unbalanced.append({"transaction_id": str(txn.id), "net_amount": total, "entry_count": count})
    balance_mismatches = []
    for account in Account.objects.all().iterator():
        ledger_balance = account.entries.aggregate(total=Sum("amount_minor"))["total"] or 0
        if ledger_balance != account.balance_minor:
            balance_mismatches.append({"account_id": account.id, "cached_balance": account.balance_minor, "ledger_balance": ledger_balance})
    return {"status": "ok" if not unbalanced and not balance_mismatches else "discrepancies_found",
            "transactions_checked": LedgerTransaction.objects.count(), "accounts_checked": Account.objects.count(),
            "unbalanced_transactions": unbalanced, "balance_mismatches": balance_mismatches}
