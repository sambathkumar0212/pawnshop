# Generated by Django 5.2.1 on 2025-05-31 19:18

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('branches', '0001_initial'),
        ('transactions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BiometricSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('face_recognition_enabled', models.BooleanField(default=False)),
                ('face_recognition_threshold', models.FloatField(default=0.6)),
                ('face_recognition_required_for_staff', models.BooleanField(default=False)),
                ('face_recognition_required_for_customers', models.BooleanField(default=False)),
                ('fingerprint_enabled', models.BooleanField(default=False)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('branch', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='biometric_settings', to='branches.branch')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'biometric setting',
                'verbose_name_plural': 'biometric settings',
            },
        ),
        migrations.CreateModel(
            name='CustomerFaceEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('face_encoding', models.BinaryField()),
                ('face_image', models.ImageField(blank=True, null=True, upload_to='customer_face_images/')),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='face_enrollment', to='transactions.customer')),
            ],
            options={
                'verbose_name': 'customer face enrollment',
                'verbose_name_plural': 'customer face enrollments',
            },
        ),
        migrations.CreateModel(
            name='FaceAuthLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('success', 'Success'), ('failure', 'Failure'), ('error', 'Error')], max_length=10)),
                ('confidence_score', models.FloatField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('device_info', models.TextField(blank=True, null=True)),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='transactions.customer')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'face auth log',
                'verbose_name_plural': 'face auth logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='FaceEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('face_encoding', models.BinaryField()),
                ('face_image', models.ImageField(blank=True, null=True, upload_to='face_images/')),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='face_enrollment', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'face enrollment',
                'verbose_name_plural': 'face enrollments',
            },
        ),
    ]
