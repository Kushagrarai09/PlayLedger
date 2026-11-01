from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Account
from .serializers import AccountSerializer
from ledger.models import LedgerEntry

class MyWalletView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        account = Account.objects.get(owner=request.user, account_type=Account.Type.USER_WALLET)
        return Response(AccountSerializer(account).data)

class MyAccountsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Account.objects.filter(owner=request.user).order_by("id")
        return Response(AccountSerializer(qs, many=True).data)
