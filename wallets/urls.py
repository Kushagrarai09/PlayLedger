from django.urls import path
from .views import MyWalletView, MyAccountsView
urlpatterns = [
    path("wallet/", MyWalletView.as_view(), name="my-wallet"),
    path("accounts/", MyAccountsView.as_view(), name="my-accounts"),
]
