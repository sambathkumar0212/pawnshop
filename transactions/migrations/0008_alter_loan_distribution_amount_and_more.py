# Generated by Django 5.2.1 on 2025-06-12 11:30

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0007_add_loan_last_updated_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loan',
            name='distribution_amount',
            field=models.DecimalField(decimal_places=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='loan',
            name='principal_amount',
            field=models.DecimalField(decimal_places=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='loan',
            name='processing_fee',
            field=models.DecimalField(decimal_places=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
