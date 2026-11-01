from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        from wallets.models import Account
        Account.objects.get_or_create(owner=instance, defaults={
            "account_type": Account.Type.USER_WALLET,
            "name": f"{instance.username} wallet",
        })
