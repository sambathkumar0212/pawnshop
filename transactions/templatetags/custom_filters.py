from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='percentage')
def percentage(part, whole):
    """Calculate what percentage the part is of the whole"""
    try:
        if not whole:
            return 0
        return float(part) / float(whole) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract the arg from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0
