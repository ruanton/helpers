import logging
from django import template
from django.template.defaultfilters import stringfilter

# local imports
from helpers.misc import exception_descr, compact_debug_info

register = template.Library()
log = logging.getLogger(__name__)


@register.filter
@stringfilter
def debug_info_compact(value):
    """Compact debug info using misc.compact_debug_info."""
    try:
        return compact_debug_info(value)
    except Exception as ex:
        return exception_descr(ex)


@register.filter
@stringfilter
def debug_info_minimize(value):
    """Compact debug info using misc.compact_debug_info with removing all protected attributes."""
    try:
        return compact_debug_info(value, remove_protected=True)
    except Exception as ex:
        return exception_descr(ex)
