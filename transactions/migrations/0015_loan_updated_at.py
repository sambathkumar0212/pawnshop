# Generated by Django 5.2.1 on 2025-06-21 20:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0014_remove_loan_last_updated_remove_loan_last_updated_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
