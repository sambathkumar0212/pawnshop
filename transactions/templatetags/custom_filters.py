from django import template
from decimal import Decimal
import json

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

@register.filter(name='get_first_photo')
def get_first_photo(item_photos):
    """Extract the first photo URL from JSON string of photos"""
    if not item_photos:
        return ""
    
    try:
        # If it's a string, try to parse as JSON
        if isinstance(item_photos, str):
            if item_photos.startswith('data:image/'):
                # It's already a direct base64 image
                return item_photos
            
            # Try to parse JSON
            photos = json.loads(item_photos)
            
            # If we got a list and it contains items
            if isinstance(photos, list) and photos:
                return photos[0]
            
            return ""
        
        # If it's already a list
        elif isinstance(item_photos, list) and item_photos:
            return item_photos[0]
        
        return ""
    except (json.JSONDecodeError, TypeError, IndexError):
        # If there's any error, return empty string
        return ""
