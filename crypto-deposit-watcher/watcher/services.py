import os
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from web3 import Web3
from .models import Deposit, LedgerEntry, WithdrawalRequest
WEI_PER_ETH = Decimal(10) ** 18

def env_int(name, default):
    try: return int(os.getenv(name, str(default)))
    except (TypeError, ValueError): return default

def credit_deposit(deposit_id):
    with transaction.atomic():
        dep = Deposit.objects.select_for_update().select_related("address__user").get(pk=deposit_id)
        if dep.status == Deposit.Status.CREDITED: return False
        if dep.status != Deposit.Status.CONFIRMED: raise ValueError("Only confirmed deposits can be credited")
        LedgerEntry.objects.get_or_create(
            reference=f"deposit:{dep.chain_id}:{dep.tx_hash}:{dep.log_index}",
            defaults={"user":dep.address.user,"kind":LedgerEntry.Kind.DEPOSIT,"amount_wei":dep.amount_wei,
                      "metadata":{"tx_hash":dep.tx_hash,"block_hash":dep.block_hash}})
        dep.status=Deposit.Status.CREDITED
        dep.credited_at=timezone.now()
        dep.save(update_fields=["status","credited_at"])
        return True

def available_balance_wei(user):
    return LedgerEntry.objects.filter(user=user).aggregate(total=Sum("amount_wei"))["total"] or Decimal(0)

def reserve_withdrawal(withdrawal_id):
    with transaction.atomic():
        req=WithdrawalRequest.objects.select_for_update().select_related("user").get(pk=withdrawal_id)
        if req.status == WithdrawalRequest.Status.RESERVED: return False
        if req.status != WithdrawalRequest.Status.REQUESTED: raise ValueError("Withdrawal is not requestable")
        if available_balance_wei(req.user) < req.amount_wei: raise ValueError("Insufficient available test balance")
        LedgerEntry.objects.create(user=req.user,kind=LedgerEntry.Kind.WITHDRAWAL_RESERVATION,
            reference=f"withdrawal-reserve:{req.idempotency_key}",amount_wei=-req.amount_wei,metadata={"withdrawal_id":req.pk})
        req.status=WithdrawalRequest.Status.RESERVED
        req.save(update_fields=["status"])
        return True

def check_sepolia(w3):
    actual=w3.eth.chain_id
    if actual != 11155111 or actual != env_int("EXPECTED_CHAIN_ID",11155111):
        raise RuntimeError(f"Refusing to run: expected Sepolia chain ID 11155111, RPC returned {actual}")
    return actual

def web3_client():
    url=os.getenv("ETH_RPC_URL","")
    if not url or ".example.invalid" in url or "REPLACE_WITH" in url:
        raise RuntimeError("Set ETH_RPC_URL in .env to a real Sepolia RPC endpoint")
    w3=Web3(Web3.HTTPProvider(url,request_kwargs={"timeout":20}))
    if not w3.is_connected(): raise RuntimeError("Cannot connect to configured Sepolia RPC endpoint")
    check_sepolia(w3)
    return w3
