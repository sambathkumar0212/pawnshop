from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def status_color(status):
    """Returns the appropriate Bootstrap color class for a loan status"""
    color_map = {
        'active': 'success',
        'paid': 'info',
        'defaulted': 'danger',
        'extended': 'warning',
        'expired': 'danger',
        'foreclosed': 'secondary'
    }
    return color_map.get(status, 'secondary')

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        return value * arg
    except (ValueError, TypeError):
        return 0