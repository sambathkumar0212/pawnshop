from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return None

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return None

@register.filter
def sub(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return None

@register.filter
def add(value, arg):
    """Add the argument to the value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return None

@register.filter
def calculate_monthly_payment(principal, scheme):
    """Calculate the monthly payment for a loan based on scheme"""
    try:
        interest_rate = float(scheme.interest_rate) / 100 / 12  # Monthly interest rate
        term_months = float(scheme.duration_days) / 30  # Duration in months
        
        if interest_rate == 0:
            return principal / term_months
            
        # Standard loan payment formula
        numerator = principal * interest_rate * ((1 + interest_rate) ** term_months)
        denominator = ((1 + interest_rate) ** term_months) - 1
        return numerator / denominator
    except (ValueError, TypeError, ZeroDivisionError, AttributeError):
        return None