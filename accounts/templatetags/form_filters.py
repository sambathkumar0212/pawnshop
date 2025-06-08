from django import template

register = template.Library()

@register.filter
def get_field(form, field_name):
    """Get a field from a form by name"""
    try:
        return form[field_name]
    except (KeyError, TypeError):
        return None

@register.filter
def getattribute(obj, attr_name):
    """Get an attribute of an object dynamically by name"""
    try:
        return getattr(obj, attr_name)
    except (AttributeError, TypeError):
        return None
