import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from wallets.models import Account
from ledger.models import LedgerEntry, LedgerTransaction
from ledger.services import LedgerError, issue_credits, transfer_credits, reconciliation_report

User = get_user_model()

@pytest.mark.django_db
def setup_users():
    admin = User.objects.create_user(username="admin", password="StrongPassword!234", is_staff=True)
    alice = User.objects.create_user(username="alice", password="StrongPassword!234")
    bob = User.objects.create_user(username="bob", password="StrongPassword!234")
    system = Account.objects.create(owner=None, account_type=Account.Type.ISSUANCE, name="Virtual credit issuance")
    return admin, alice, bob, system

@pytest.mark.django_db
def test_issue_and_transfer_balances():
    admin, alice, bob, system = setup_users()
    issue_credits(actor=admin, recipient_user_id=alice.id, amount=1000, idempotency_key="issue-alice-1")
    txn, replayed = transfer_credits(actor=alice, recipient_user_id=bob.id, amount=200, idempotency_key="transfer-1")
    assert not replayed
    assert Account.objects.get(owner=alice).balance_minor == 800
    assert Account.objects.get(owner=bob).balance_minor == 200
    assert sum(e.amount_minor for e in txn.entries.all()) == 0
    assert reconciliation_report()["status"] == "ok"

@pytest.mark.django_db
def test_idempotent_retry_does_not_double_transfer():
    admin, alice, bob, system = setup_users()
    issue_credits(actor=admin, recipient_user_id=alice.id, amount=100, idempotency_key="issue-1")
    first, replayed1 = transfer_credits(actor=alice, recipient_user_id=bob.id, amount=40, idempotency_key="same-key")
    second, replayed2 = transfer_credits(actor=alice, recipient_user_id=bob.id, amount=40, idempotency_key="same-key")
    assert first.id == second.id and not replayed1 and replayed2
    assert Account.objects.get(owner=alice).balance_minor == 60
    assert Account.objects.get(owner=bob).balance_minor == 40
    with pytest.raises(LedgerError):
        transfer_credits(actor=alice, recipient_user_id=bob.id, amount=41, idempotency_key="same-key")

@pytest.mark.django_db
def test_insufficient_funds_does_not_write_transaction():
    admin, alice, bob, system = setup_users()
    with pytest.raises(LedgerError, match="Insufficient funds"):
        transfer_credits(actor=alice, recipient_user_id=bob.id, amount=1, idempotency_key="no-funds")
    assert LedgerTransaction.objects.count() == 0
    assert LedgerEntry.objects.count() == 0

@pytest.mark.django_db
def test_api_registration_wallet_and_transfer():
    client = APIClient()
    response = client.post("/api/auth/register/", {"username": "charlie", "password": "VeryStrongPassword!123", "email": "charlie@example.com"}, format="json")
    assert response.status_code == 201
    assert "token" in response.data
    client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
    wallet_response = client.get("/api/wallet/")
    assert wallet_response.status_code == 200
    assert wallet_response.data["available_credits"] == 0

@pytest.mark.django_db(transaction=True)
def test_concurrent_transfers_never_overspend():
    """PostgreSQL integration test: 100 concurrent 20-credit transfers from 1,000 credits."""
    from concurrent.futures import ThreadPoolExecutor
    from django.db import close_old_connections, connection
    if connection.vendor != "postgresql":
        pytest.skip("Concurrency/row-locking test requires PostgreSQL.")
    admin, alice, bob, system = setup_users()
    issue_credits(actor=admin, recipient_user_id=alice.id, amount=1000, idempotency_key="issue-concurrency")

    def send(i):
        close_old_connections()
        try:
            actor = User.objects.get(pk=alice.pk)
            transfer_credits(actor=actor, recipient_user_id=bob.id, amount=20, idempotency_key=f"concurrent-{i}")
            return "success"
        except LedgerError:
            return "rejected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=20) as pool:
        outcomes = list(pool.map(send, range(100)))
    assert outcomes.count("success") == 50
    assert outcomes.count("rejected") == 50
    assert Account.objects.get(owner=alice).balance_minor == 0
    assert Account.objects.get(owner=bob).balance_minor == 1000
    assert reconciliation_report()["status"] == "ok"

@pytest.mark.django_db
def test_reversal_is_compensating_and_original_is_preserved():
    admin, alice, bob, system = setup_users()
    issue_credits(actor=admin, recipient_user_id=alice.id, amount=100, idempotency_key="issue-reversal")
    transfer, _ = transfer_credits(actor=alice, recipient_user_id=bob.id, amount=30, idempotency_key="transfer-reversal")
    from ledger.services import reverse_transaction
    reversal, replayed = reverse_transaction(actor=admin, transaction_id=transfer.id, idempotency_key="reverse-1")
    assert not replayed
    assert transfer.entries.count() == 2
    assert reversal.reversal_of_id == transfer.id
    assert Account.objects.get(owner=alice).balance_minor == 100
    assert Account.objects.get(owner=bob).balance_minor == 0
    assert reconciliation_report()["status"] == "ok"
