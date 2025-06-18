from django import template

register = template.Library()

@register.filter(name='split')
def split_filter(value, arg):
    """Split a string by the given delimiter"""
    return value.split(arg)

@register.filter(name='replace')
def replace_filter(value, arg):
    """Replace characters in a string with a space"""
    return value.replace(arg, " ")