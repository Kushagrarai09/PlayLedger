from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_type', models.CharField(choices=[('user_wallet', 'User wallet'), ('issuance', 'Virtual credit issuance'), ('fees', 'Platform fees'), ('clearing', 'Clearing')], max_length=24)),
                ('name', models.CharField(max_length=120)),
                ('balance_minor', models.BigIntegerField(default=0)),
                ('status', models.CharField(choices=[('active', 'Active'), ('frozen', 'Frozen'), ('closed', 'Closed')], default='active', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='wallet_account', to=settings.AUTH_USER_MODEL)),
            ],
            options={'indexes': [models.Index(fields=['account_type', 'status'], name='wallets_acc_account_5d0a2e_idx')]},
        ),
        migrations.AddConstraint(model_name='account', constraint=models.CheckConstraint(condition=models.Q(('balance_minor__gte', 0), models.Q(('account_type', 'user_wallet'), _negated=True), _connector='OR'), name='user_wallet_balance_nonnegative')),
        migrations.AddConstraint(model_name='account', constraint=models.UniqueConstraint(condition=models.Q(('owner__isnull', True)), fields=('account_type', 'name'), name='unique_system_account_name_type')),
    ]
