# Generated by Django 5.2.1 on 2025-06-01 11:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
        ('biometrics', '0002_alter_faceauthlog_options_and_more'),
        ('inventory', '0001_initial'),
        ('transactions', '0002_loan_gold_karat_loan_gross_weight_loan_net_weight_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchases', to='accounts.customer'),
        ),
        migrations.AlterField(
            model_name='loan',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to='accounts.customer'),
        ),
        migrations.RemoveField(
            model_name='loan',
            name='gold_karat',
        ),
        migrations.RemoveField(
            model_name='loan',
            name='gross_weight',
        ),
        migrations.RemoveField(
            model_name='loan',
            name='item',
        ),
        migrations.RemoveField(
            model_name='loan',
            name='net_weight',
        ),
        migrations.RemoveField(
            model_name='loan',
            name='ornament_type',
        ),
        migrations.RemoveField(
            model_name='loan',
            name='stone_weight',
        ),
        migrations.CreateModel(
            name='LoanItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gold_karat', models.DecimalField(decimal_places=2, help_text='Purity of gold in karats', max_digits=4)),
                ('gross_weight', models.DecimalField(decimal_places=3, help_text='Total weight of the ornament in grams', max_digits=7)),
                ('net_weight', models.DecimalField(decimal_places=3, help_text='Weight of pure gold content in grams', max_digits=7)),
                ('stone_weight', models.DecimalField(blank=True, decimal_places=3, help_text='Weight of stones if any in grams', max_digits=7, null=True)),
                ('market_price_22k', models.DecimalField(decimal_places=2, help_text='Market price of 22K gold per gram at the time of loan', max_digits=10)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.item')),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transactions.loan')),
            ],
            options={
                'unique_together': {('loan', 'item')},
            },
        ),
        migrations.AddField(
            model_name='loan',
            name='items',
            field=models.ManyToManyField(related_name='loans', through='transactions.LoanItem', to='inventory.item'),
        ),
        migrations.DeleteModel(
            name='Customer',
        ),
    ]
