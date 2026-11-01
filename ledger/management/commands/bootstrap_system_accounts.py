from django.core.management.base import BaseCommand
from django.db import transaction
from wallets.models import Account

class Command(BaseCommand):
    help = "Create required system accounts for the virtual-credit ledger."
    @transaction.atomic
    def handle(self, *args, **options):
        definitions = [
            (Account.Type.ISSUANCE, "Virtual credit issuance"),
            (Account.Type.FEES, "Platform fees"),
            (Account.Type.CLEARING, "Platform clearing"),
        ]
        for account_type, name in definitions:
            account, created = Account.objects.get_or_create(owner=None, account_type=account_type, name=name, defaults={"status": Account.Status.ACTIVE, "balance_minor": 0})
            self.stdout.write(f"{'Created' if created else 'Exists'}: {account.name} (id={account.id})")
