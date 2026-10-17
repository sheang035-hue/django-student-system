from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Returns the current query string with updated/added parameters,
    preserving all existing GET parameters (e.g. search, q, status, sort, per_page).
    Example: {% query_transform page=page_obj.next_page_number %}
    """
    request = context.get('request')
    if not request:
        return ''
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None and value != '':
            query[key] = value
        else:
            query.pop(key, None)
    return query.urlencode()

@register.filter
def get_item(dictionary, key):
    """Lookup a key in a dictionary or dict-like object."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

