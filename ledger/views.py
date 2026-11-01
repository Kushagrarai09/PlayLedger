from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from wallets.models import Account
from .models import AuditLog, LedgerEntry, LedgerTransaction
from .serializers import TransactionSerializer
from .services import LedgerError, issue_credits, transfer_credits, reverse_transaction, reconciliation_report

User = get_user_model()

class TransferInputSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(min_value=1)
    amount = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

class TransferView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        data = TransferInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key", "")
        try:
            txn, replayed = transfer_credits(actor=request.user, recipient_user_id=data.validated_data["recipient_id"], amount=data.validated_data["amount"], idempotency_key=key, description=data.validated_data["description"])
        except LedgerError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT if "Insufficient" in str(exc) or "idempotency" in str(exc).lower() or "already" in str(exc).lower() else status.HTTP_400_BAD_REQUEST)
        AuditLog.objects.create(actor=request.user, action="transfer_replayed" if replayed else "transfer_posted", target_type="LedgerTransaction", target_id=str(txn.id), metadata={"amount": data.validated_data["amount"]})
        return Response({"transaction": TransactionSerializer(txn).data, "replayed": replayed}, status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED)

class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        account_ids = Account.objects.filter(owner=request.user).values_list("id", flat=True)
        qs = LedgerTransaction.objects.filter(entries__account_id__in=account_ids).distinct().prefetch_related("entries__account")
        kind = request.query_params.get("kind")
        if kind in {choice[0] for choice in LedgerTransaction.Kind.choices}:
            qs = qs.filter(kind=kind)
        return Response(TransactionSerializer(qs[:100], many=True).data)

class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, transaction_id):
        account_ids = Account.objects.filter(owner=request.user).values_list("id", flat=True)
        txn = LedgerTransaction.objects.filter(id=transaction_id, entries__account_id__in=account_ids).distinct().prefetch_related("entries__account").first()
        if not txn:
            return Response({"detail": "Transaction not found."}, status=404)
        return Response(TransactionSerializer(txn).data)

class AdminIssueCreditsView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request):
        recipient_id = request.data.get("recipient_id")
        amount = request.data.get("amount")
        description = request.data.get("description", "Initial virtual credits")
        if not isinstance(recipient_id, int) or not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            return Response({"detail": "recipient_id and positive integer amount are required."}, status=400)
        try:
            txn, replayed = issue_credits(actor=request.user, recipient_user_id=recipient_id, amount=amount, idempotency_key=request.headers.get("Idempotency-Key", ""), description=str(description)[:255])
        except LedgerError as exc:
            return Response({"detail": str(exc)}, status=409 if "idempotency" in str(exc).lower() else 400)
        AuditLog.objects.create(actor=request.user, action="credits_issued" if not replayed else "credit_issue_replayed", target_type="LedgerTransaction", target_id=str(txn.id), metadata={"recipient_id": recipient_id, "amount": amount})
        return Response({"transaction": TransactionSerializer(txn).data, "replayed": replayed}, status=200 if replayed else 201)

class AdminReconciliationView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        report = reconciliation_report()
        AuditLog.objects.create(actor=request.user, action="reconciliation_run", target_type="Reconciliation", metadata={"status": report["status"]})
        return Response(report, status=200 if report["status"] == "ok" else 409)

class AdminReverseView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, transaction_id):
        try:
            txn, replayed = reverse_transaction(actor=request.user, transaction_id=transaction_id, idempotency_key=request.headers.get("Idempotency-Key", ""))
        except LedgerError as exc:
            return Response({"detail": str(exc)}, status=409 if "already" in str(exc).lower() else 400)
        AuditLog.objects.create(actor=request.user, action="transaction_reversed", target_type="LedgerTransaction", target_id=str(txn.id), metadata={"original_id": str(transaction_id)})
        return Response({"transaction": TransactionSerializer(txn).data, "replayed": replayed}, status=200 if replayed else 201)

class AdminAccountStatusView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, account_id):
        from django.db import transaction
        new_status = request.data.get("status")
        if new_status not in {Account.Status.ACTIVE, Account.Status.FROZEN, Account.Status.CLOSED}:
            return Response({"detail": "status must be active, frozen, or closed."}, status=400)
        with transaction.atomic():
            account = Account.objects.select_for_update().filter(pk=account_id).first()
            if not account:
                return Response({"detail": "Account not found."}, status=404)
            previous = account.status
            account.status = new_status
            account.save(update_fields=["status", "updated_at"])
            AuditLog.objects.create(actor=request.user, action="account_status_changed", target_type="Account", target_id=str(account.id), metadata={"from": previous, "to": new_status})
        return Response({"account_id": account.id, "status": account.status})
