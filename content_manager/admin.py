from django.contrib import admin
from .models import Scheme

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'scheme_type', 'interest_rate', 'duration_days', 'no_interest_period_days', 'branch', 'is_active')
    list_filter = ('scheme_type', 'is_active', 'branch')
    search_fields = ('name', 'code', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'scheme_type', 'description', 'is_active')
        }),
        ('Financial Parameters', {
            'fields': ('interest_rate', 'processing_fee_percentage')
        }),
        ('Duration Settings', {
            'fields': ('duration_days', 'no_interest_period_days', 'minimum_period_days')
        }),
        ('Branch Association', {
            'fields': ('branch',)
        }),
    )
