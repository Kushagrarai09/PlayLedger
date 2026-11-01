import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('wallets', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='LedgerTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('idempotency_key', models.CharField(max_length=128)),
                ('request_hash', models.CharField(max_length=64)),
                ('kind', models.CharField(choices=[('issue', 'Issue virtual credits'), ('transfer', 'Transfer'), ('reversal', 'Reversal')], max_length=16)),
                ('status', models.CharField(choices=[('posted', 'Posted')], default='posted', max_length=12)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('initiated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ledger_transactions', to=settings.AUTH_USER_MODEL)),
                ('reversal_of', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reversed_by', to='ledger.ledgertransaction')),
            ],
            options={'ordering': ['-created_at'], 'indexes': [models.Index(fields=['kind', 'created_at'], name='ledger_ledger_kind_7b4fd2_idx'), models.Index(fields=['initiated_by', 'created_at'], name='ledger_ledger_initi_7b88ce_idx')]},
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=80)),
                ('target_type', models.CharField(blank=True, max_length=80)),
                ('target_id', models.CharField(blank=True, max_length=80)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ledger_audit_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'indexes': [models.Index(fields=['action', 'created_at'], name='ledger_audit_action_2e4a9d_idx')]},
        ),
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('amount_minor', models.BigIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entries', to='wallets.account')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entries', to='ledger.ledgertransaction')),
            ],
            options={'indexes': [models.Index(fields=['account', 'created_at'], name='ledger_entry_account_3fcb19_idx'), models.Index(fields=['transaction', 'account'], name='ledger_entry_transac_ef50a3_idx')]},
        ),
        migrations.AddConstraint(model_name='ledgerentry', constraint=models.CheckConstraint(condition=~models.Q(('amount_minor', 0)), name='ledger_entry_nonzero')),
        migrations.AddConstraint(model_name='ledgertransaction', constraint=models.UniqueConstraint(fields=('initiated_by', 'idempotency_key'), name='unique_actor_idempotency_key')),
    ]
