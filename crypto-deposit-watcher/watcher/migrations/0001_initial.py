from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name="BlockCheckpoint",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("chain_id",models.PositiveBigIntegerField(default=11155111)),
            ("block_number",models.PositiveBigIntegerField(unique=True)),
            ("block_hash",models.CharField(max_length=66)),("parent_hash",models.CharField(max_length=66)),
            ("scanned_at",models.DateTimeField(auto_now=True))]),
        migrations.CreateModel(name="DepositAddress",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("address",models.CharField(max_length=42,unique=True)),
            ("derivation_index",models.PositiveIntegerField(unique=True)),
            ("created_at",models.DateTimeField(auto_now_add=True)),("is_active",models.BooleanField(default=True)),
            ("user",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="deposit_addresses",to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="Deposit",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("chain_id",models.PositiveBigIntegerField(default=11155111)),("tx_hash",models.CharField(max_length=66)),
            ("log_index",models.PositiveIntegerField(default=0)),("from_address",models.CharField(max_length=42)),
            ("to_address",models.CharField(max_length=42)),("amount_wei",models.DecimalField(decimal_places=0,max_digits=78)),
            ("block_number",models.PositiveBigIntegerField()),("block_hash",models.CharField(max_length=66)),
            ("status",models.CharField(choices=[("DETECTED","DETECTED"),("CONFIRMING","CONFIRMING"),("CONFIRMED","CONFIRMED"),("CREDITED","CREDITED"),("REORGED","REORGED"),("FAILED","FAILED")],default="DETECTED",max_length=16)),
            ("confirmations",models.PositiveIntegerField(default=0)),("detected_at",models.DateTimeField(auto_now_add=True)),
            ("credited_at",models.DateTimeField(blank=True,null=True)),("error",models.TextField(blank=True)),
            ("address",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="deposits",to="watcher.depositaddress"))],
            options={"constraints":[models.UniqueConstraint(fields=("chain_id","tx_hash","log_index"),name="uniq_chain_tx_event")]}),
        migrations.CreateModel(name="LedgerEntry",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("kind",models.CharField(choices=[("DEPOSIT","DEPOSIT"),("WITHDRAWAL_RESERVATION","WITHDRAWAL_RESERVATION"),("WITHDRAWAL_RELEASE","WITHDRAWAL_RELEASE"),("WITHDRAWAL_SETTLEMENT","WITHDRAWAL_SETTLEMENT")],max_length=32)),
            ("reference",models.CharField(max_length=160,unique=True)),("amount_wei",models.DecimalField(decimal_places=0,max_digits=78)),
            ("created_at",models.DateTimeField(auto_now_add=True)),("metadata",models.JSONField(blank=True,default=dict)),
            ("user",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="WithdrawalRequest",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("destination",models.CharField(max_length=42)),("amount_wei",models.DecimalField(decimal_places=0,max_digits=78)),
            ("idempotency_key",models.CharField(max_length=128,unique=True)),
            ("status",models.CharField(choices=[("REQUESTED","REQUESTED"),("RESERVED","RESERVED"),("APPROVED","APPROVED"),("BROADCAST","BROADCAST"),("CONFIRMED","CONFIRMED"),("REJECTED","REJECTED"),("FAILED","FAILED")],default="REQUESTED",max_length=16)),
            ("requested_at",models.DateTimeField(auto_now_add=True)),("tx_hash",models.CharField(blank=True,max_length=66)),
            ("error",models.TextField(blank=True)),("approved_by",models.ManyToManyField(blank=True,related_name="approved_withdrawals",to=settings.AUTH_USER_MODEL)),
            ("user",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="withdrawals",to=settings.AUTH_USER_MODEL))]),
    ]
