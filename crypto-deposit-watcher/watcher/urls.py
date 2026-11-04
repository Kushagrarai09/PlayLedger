from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepositAddressViewSet, DepositViewSet, WithdrawalViewSet, balance, create_test_address, health
router=DefaultRouter()
router.register("deposit-addresses",DepositAddressViewSet,basename="deposit-address")
router.register("deposits",DepositViewSet,basename="deposit")
router.register("withdrawals",WithdrawalViewSet,basename="withdrawal")
urlpatterns=[path("health/",health),path("balance/",balance),path("dev/deposit-addresses/",create_test_address),path("",include(router.urls))]
