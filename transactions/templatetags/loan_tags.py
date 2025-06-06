import json
from django import template
from django.utils.safestring import mark_safe
from decimal import Decimal

register = template.Library()

@register.filter
def status_color(status):
    """Return the appropriate Bootstrap color class for a loan status"""
    colors = {
        'active': 'success',
        'repaid': 'info',
        'defaulted': 'danger',
        'extended': 'warning',
        'foreclosed': 'secondary',
    }
    return colors.get(status, 'secondary')

@register.filter
def first_item_photo(item_photos):
    """Return the first item photo from the item_photos JSON data"""
    try:
        if isinstance(item_photos, str):
            # Parse the JSON string to get the list of photo URLs
            photo_list = json.loads(item_photos)
            if photo_list and len(photo_list) > 0:
                return photo_list[0]
        elif isinstance(item_photos, list) and len(item_photos) > 0:
            # If it's already a list, just return the first item
            return item_photos[0]
    except (json.JSONDecodeError, IndexError, TypeError):
        pass
    
    # Return a default placeholder image if no photo is available
    return "/static/img/placeholder-item.png"

@register.filter
def item_photos_count(item_photos):
    """Return the count of item photos"""
    try:
        if isinstance(item_photos, str):
            # Parse the JSON string to get the list of photo URLs
            photo_list = json.loads(item_photos)
            return len(photo_list)
        elif isinstance(item_photos, list):
            # If it's already a list, just return the length
            return len(item_photos)
    except (json.JSONDecodeError, TypeError):
        pass
    return 0

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
def subtract(value, arg):
    """Subtract the arg from the value."""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value
        
@register.filter
def add(value, arg):
    """Add the arg to the value."""
    try:
        return value + arg
    except (ValueError, TypeError):
        return value