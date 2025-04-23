# A template filter for safe rendering
# of markdown content in Django templates.
from django import template
from django.utils.safestring import mark_safe
import markdown

register = template.Library()
@register.filter
def markdownify(text):
    md = markdown.Markdown(extensions=[
        'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.tables', 'markdown.extensions.nl2br'
    ])
    return mark_safe(md.convert(text))

@register.simple_tag
def markdownify_tag(text):
    md = markdown.Markdown(extensions=[
        'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.tables', 'markdown.extensions.nl2br'
    ])
    return mark_safe(md.convert(text))

@register.simple_tag(takes_context=True)
def markdownify_tag_with_context(context, text):
    md = markdown.Markdown(extensions=[
        'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.tables', 'markdown.extensions.nl2br'
    ])
    return mark_safe(md.convert(text))