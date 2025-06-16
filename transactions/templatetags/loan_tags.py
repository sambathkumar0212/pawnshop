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
        if not item_photos:
            return "/static/img/placeholder-item.png"
            
        if isinstance(item_photos, str):
            # If it's already a base64 image, return it directly
            if item_photos.startswith('data:image/'):
                return item_photos
                
            # Parse the JSON string to get the list of photo URLs
            photo_list = json.loads(item_photos)
            if photo_list and len(photo_list) > 0:
                # Handle the case where the first item itself is a list or dict
                if isinstance(photo_list[0], (list, dict)):
                    if isinstance(photo_list[0], dict) and 'url' in photo_list[0]:
                        return photo_list[0]['url']
                    return "/static/img/placeholder-item.png"
                return photo_list[0]
        elif isinstance(item_photos, list) and len(item_photos) > 0:
            # If it's already a list, just return the first item
            if isinstance(item_photos[0], dict) and 'url' in item_photos[0]:
                return item_photos[0]['url']
            return item_photos[0]
    except (json.JSONDecodeError, IndexError, TypeError) as e:
        print(f"Error in first_item_photo filter: {e}, input: {type(item_photos)}")
    
    # Return a default placeholder image if no photo is available
    return "/static/img/placeholder-item.png"

@register.filter
def item_photos_count(item_photos):
    """Return the count of item photos"""
    try:
        if isinstance(item_photos, str):
            # If it's a base64 string, it's one photo
            if item_photos.startswith('data:image/'):
                return 1
                
            # Try to parse as JSON
            photo_list = json.loads(item_photos)
            if isinstance(photo_list, list):
                return len(photo_list)
            return 1
        elif isinstance(item_photos, list):
            # If it's already a list, just return the length
            return len(item_photos)
        return 0
    except (json.JSONDecodeError, TypeError):
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

@register.filter
def split(value, arg):
    """Split the value by the delimiter."""
    return value.split(arg)

@register.filter
def calculate_total_items(item_name):
    """
    Parse item name to extract and sum numbers after hyphens for multiple items.
    Format expected: "ring-6, chain-1, dollar-1, thodu-2" would return 10
    """
    try:
        # Split items by comma (and optional space)
        items = [item.strip() for item in item_name.split(',')]
        
        # Initialize total count
        total = 0
        
        # Process each item
        for item in items:
            # Check if the item contains a hyphen
            if '-' in item:
                # Split by hyphen and get the second part (the count)
                parts = item.split('-', 1)
                if len(parts) > 1:
                    try:
                        # Try to convert the count to integer and add it
                        count = int(parts[1].strip())
                        total += count
                    except ValueError:
                        # Skip if not a valid number
                        continue
                        
        return total
    except Exception:
        # Return 0 if any error occurs
        return 0

@register.filter
def is_base64(value):
    """Check if a string is a base64 image"""
    if not isinstance(value, str):
        return False
    return value.startswith('data:image/')