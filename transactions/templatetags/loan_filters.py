from django import template
from decimal import Decimal
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        return value * arg
    except (ValueError, TypeError):
        return 0

@register.filter
def date_add_days(value, days):
    """Add a number of days to a date"""
    try:
        days = int(days)
        return value + timedelta(days=days)
    except (ValueError, TypeError):
        return value