from django import template

register = template.Library()

@register.filter
def to_letter(value):
    try:
        return chr(96 + value)
    except (TypeError, ValueError):
        return value