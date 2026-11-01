from django.urls import path
from .views import TransferView, TransactionListView, TransactionDetailView, AdminIssueCreditsView, AdminReconciliationView, AdminReverseView, AdminAccountStatusView
urlpatterns = [
    path("transfers/", TransferView.as_view(), name="transfer"),
    path("transactions/", TransactionListView.as_view(), name="transactions"),
    path("transactions/<uuid:transaction_id>/", TransactionDetailView.as_view(), name="transaction-detail"),
    path("admin/credits/issue/", AdminIssueCreditsView.as_view(), name="issue-credits"),
    path("admin/reconciliation/", AdminReconciliationView.as_view(), name="reconciliation"),
    path("admin/accounts/<int:account_id>/status/", AdminAccountStatusView.as_view(), name="account-status"),
    path("admin/transactions/<uuid:transaction_id>/reverse/", AdminReverseView.as_view(), name="reverse-transaction"),
]
