from django import template
from decimal import Decimal
from datetime import timedelta
import re
from num2words import num2words

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

@register.filter
def calculate_total_items(item_name):
    """
    Calculate the total number of items from an item name string
    Format: "ring-6, chain-1" would return 7
    """
    if not item_name:
        return 0
    
    total_count = 0
    # Split by commas to handle multiple items
    items = [item.strip() for item in item_name.split(',') if item.strip()]
    
    for item in items:
        # Find patterns like "item-3" or "item - 5"
        match = re.search(r'(\w+)\s*-\s*(\d+)', item)
        if match:
            try:
                count = int(match.group(2))
                total_count += count
            except ValueError:
                pass
    
    return total_count

@register.filter
def number_to_words(value):
    """Convert a number to words in Indian format"""
    try:
        # Convert to float and format to handle decimals properly
        amount = float(value)
        return num2words(amount, lang='en_IN').title()
    except (ValueError, TypeError):
        return ''