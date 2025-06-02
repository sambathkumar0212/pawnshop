from django import template

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