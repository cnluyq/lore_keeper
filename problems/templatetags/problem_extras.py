# problems/templatetags/problem_extras.py
import json
from pathlib import PurePath
from django import template

register = template.Library()

@register.filter
def basename(value):
    """
    去掉文件路径，只留文件名。
    用法：{{ problem.root_cause_file.name|basename }}
    """
    if not value:
        return ''
    return PurePath(value).name
