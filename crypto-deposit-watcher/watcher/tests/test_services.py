from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from watcher.models import DepositAddress, Deposit, LedgerEntry, WithdrawalRequest
from watcher.services import credit_deposit, reserve_withdrawal

pytestmark=pytest.mark.django_db

@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="alice",password="test-password")

@pytest.fixture
def confirmed_deposit(user):
    addr=DepositAddress.objects.create(user=user,address="0x0000000000000000000000000000000000000001",derivation_index=1)
    return Deposit.objects.create(chain_id=11155111,tx_hash="0x"+"a"*64,log_index=0,address=addr,
        from_address="0x0000000000000000000000000000000000000002",to_address=addr.address,
        amount_wei=Decimal("1000000000000000000"),block_number=10,block_hash="0x"+"b"*64,
        status=Deposit.Status.CONFIRMED,confirmations=12)

def test_credit_is_idempotent(confirmed_deposit):
    assert credit_deposit(confirmed_deposit.pk) is True
    assert credit_deposit(confirmed_deposit.pk) is False
    assert LedgerEntry.objects.filter(reference__startswith="deposit:").count()==1

def test_only_confirmed_deposit_can_be_credited(confirmed_deposit):
    confirmed_deposit.status=Deposit.Status.DETECTED
    confirmed_deposit.save()
    with pytest.raises(ValueError): credit_deposit(confirmed_deposit.pk)

def test_withdrawal_reservation_is_idempotent(user,confirmed_deposit):
    credit_deposit(confirmed_deposit.pk)
    req=WithdrawalRequest.objects.create(user=user,destination="0x0000000000000000000000000000000000000003",
        amount_wei=Decimal("100000000000000000"),idempotency_key="withdrawal-test-1")
    assert reserve_withdrawal(req.pk) is True
    assert reserve_withdrawal(req.pk) is False
    assert LedgerEntry.objects.filter(reference="withdrawal-reserve:withdrawal-test-1").count()==1

def test_withdrawal_cannot_exceed_balance(user):
    req=WithdrawalRequest.objects.create(user=user,destination="0x0000000000000000000000000000000000000003",
        amount_wei=Decimal("100000000000000000"),idempotency_key="withdrawal-test-2")
    with pytest.raises(ValueError): reserve_withdrawal(req.pk)
