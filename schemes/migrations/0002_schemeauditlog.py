from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),  # Adjust this if needed
        ('schemes', '0001_initial'),    # Adjust this if needed
    ]

    operations = [
        migrations.CreateModel(
            name='SchemeAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('changes', models.JSONField(blank=True, null=True)),
                ('scheme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='schemes.scheme')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.customuser')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]