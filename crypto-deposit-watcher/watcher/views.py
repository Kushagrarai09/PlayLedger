import os
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from web3 import Web3
from .models import DepositAddress, Deposit, LedgerEntry, WithdrawalRequest
from .serializers import DepositAddressSerializer, DepositSerializer, WithdrawalCreateSerializer
from .services import reserve_withdrawal, WEI_PER_ETH

class DepositAddressViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=DepositAddressSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self): return DepositAddress.objects.filter(user=self.request.user,is_active=True)

class DepositViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=DepositSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self): return Deposit.objects.filter(address__user=self.request.user).order_by("-detected_at")

class WithdrawalViewSet(viewsets.ModelViewSet):
    serializer_class=WithdrawalCreateSerializer
    permission_classes=[IsAuthenticated]
    http_method_names=["get","post","head","options"]
    def get_queryset(self):
        qs=WithdrawalRequest.objects.select_related("user").prefetch_related("approved_by")
        return qs.filter(user=self.request.user) if not self.request.user.is_staff else qs
    def perform_create(self, serializer):
        amount=Decimal(serializer.validated_data["amount_wei"])
        if amount > Decimal(os.getenv("WITHDRAWAL_MAX_ETH","0.1"))*WEI_PER_ETH:
            raise ValueError("Withdrawal exceeds configured testnet maximum")
        req=serializer.save(user=self.request.user)
        try: reserve_withdrawal(req.pk)
        except Exception:
            req.delete()
            raise
    @action(detail=True,methods=["post"],permission_classes=[IsAdminUser])
    def approve(self,request,pk=None):
        req=self.get_object()
        single=Decimal(os.getenv("WITHDRAWAL_SINGLE_REVIEW_LIMIT_ETH","0.01"))*WEI_PER_ETH
        dual=Decimal(os.getenv("WITHDRAWAL_DUAL_REVIEW_LIMIT_ETH","0.1"))*WEI_PER_ETH
        if req.status != WithdrawalRequest.Status.RESERVED:
            return Response({"detail":"Only reserved requests can be approved."},status=400)
        if Decimal(req.amount_wei)>dual:
            return Response({"detail":"Amount exceeds testnet approval ceiling."},status=400)
        req.approved_by.add(request.user)
        required=1 if Decimal(req.amount_wei)<=single else 2
        if req.approved_by.count()>=required:
            req.status=WithdrawalRequest.Status.APPROVED
            req.save(update_fields=["status"])
        return Response({"status":req.status,"approvals":req.approved_by.count(),"required":required})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def balance(request):
    amount=LedgerEntry.objects.filter(user=request.user).aggregate(total=Sum("amount_wei"))["total"] or Decimal(0)
    return Response({"available_wei":str(amount),"available_eth":str(amount/WEI_PER_ETH)})

@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_test_address(request):
    user_id=request.data.get("user_id")
    address=request.data.get("address","")
    index=request.data.get("derivation_index")
    if not user_id or not index or not Web3.is_address(address):
        return Response({"detail":"user_id, positive derivation_index, and valid address are required"},status=400)
    try:
        user=get_user_model().objects.get(pk=user_id)
        row=DepositAddress.objects.create(user=user,address=Web3.to_checksum_address(address),derivation_index=index)
    except Exception as exc:
        return Response({"detail":str(exc)},status=400)
    return Response(DepositAddressSerializer(row).data,status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def health(request):
    return Response({"status":"ok","network":"sepolia-testnet-only"})
