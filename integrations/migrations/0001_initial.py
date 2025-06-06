# Generated by Django 5.2.1 on 2025-05-31 19:18

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('branches', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Integration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('integration_type', models.CharField(choices=[('pos', 'Point of Sale'), ('accounting', 'Accounting Software'), ('crm', 'Customer Relationship Management'), ('sms', 'SMS Service'), ('email', 'Email Service'), ('payment', 'Payment Gateway'), ('ecommerce', 'E-Commerce Platform'), ('other', 'Other')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('api_key', models.CharField(blank=True, max_length=255, null=True)),
                ('api_secret', models.CharField(blank=True, max_length=255, null=True)),
                ('api_endpoint', models.URLField(blank=True, null=True)),
                ('other_credentials', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('error', 'Error'), ('pending', 'Pending Setup')], default='pending', max_length=10)),
                ('is_global', models.BooleanField(default=False, help_text='If true, available to all branches')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_sync', models.DateTimeField(blank=True, null=True)),
                ('branches', models.ManyToManyField(blank=True, related_name='integrations', to='branches.branch')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'integration',
                'verbose_name_plural': 'integrations',
            },
        ),
        migrations.CreateModel(
            name='CRMIntegration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crm_provider', models.CharField(max_length=100)),
                ('sync_customers', models.BooleanField(default=True)),
                ('sync_transactions', models.BooleanField(default=True)),
                ('sync_communications', models.BooleanField(default=True)),
                ('field_mapping', models.JSONField(default=dict)),
                ('integration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='crm_details', to='integrations.integration')),
            ],
            options={
                'verbose_name': 'CRM integration',
                'verbose_name_plural': 'CRM integrations',
            },
        ),
        migrations.CreateModel(
            name='AccountingIntegration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accounting_provider', models.CharField(max_length=100)),
                ('sync_sales', models.BooleanField(default=True)),
                ('sync_purchases', models.BooleanField(default=True)),
                ('sync_inventory', models.BooleanField(default=True)),
                ('sync_customers', models.BooleanField(default=True)),
                ('chart_of_accounts_mapping', models.JSONField(default=dict)),
                ('integration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='accounting_details', to='integrations.integration')),
            ],
            options={
                'verbose_name': 'accounting integration',
                'verbose_name_plural': 'accounting integrations',
            },
        ),
        migrations.CreateModel(
            name='IntegrationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('event_type', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('success', 'Success'), ('error', 'Error'), ('warning', 'Warning'), ('info', 'Information')], max_length=10)),
                ('message', models.TextField()),
                ('data', models.JSONField(blank=True, default=dict, null=True)),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='integrations.integration')),
            ],
            options={
                'verbose_name': 'integration log',
                'verbose_name_plural': 'integration logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='POSIntegration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pos_provider', models.CharField(max_length=100)),
                ('inventory_sync_enabled', models.BooleanField(default=True)),
                ('transaction_sync_enabled', models.BooleanField(default=True)),
                ('customer_sync_enabled', models.BooleanField(default=True)),
                ('mapping_config', models.JSONField(default=dict)),
                ('integration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pos_details', to='integrations.integration')),
            ],
            options={
                'verbose_name': 'POS integration',
                'verbose_name_plural': 'POS integrations',
            },
        ),
        migrations.CreateModel(
            name='WebhookEndpoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('endpoint_url', models.CharField(max_length=255, unique=True)),
                ('secret_key', models.CharField(default=uuid.uuid4, editable=False, max_length=64)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('integration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhooks', to='integrations.integration')),
            ],
            options={
                'verbose_name': 'webhook endpoint',
                'verbose_name_plural': 'webhook endpoints',
            },
        ),
    ]
