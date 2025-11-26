# problems/templatetags/problem_extras.py
import json
from pathlib import PurePath
from django import template

register = template.Library()

@register.filter
def field_json(problem, field):
    """
    把 problem 的任意文本字段原样转义成 JSON，供 JS 直接嵌入。
    用法：{{ problem|field_json:'description' }}
    """
    value = getattr(problem, field) or ''
    return json.dumps(value)          # 自动转义引号、换行等

@register.filter
def basename(value):
    """
    去掉文件路径，只留文件名。
    用法：{{ problem.root_cause_file.name|basename }}
    """
    if not value:
        return ''
    return PurePath(value).name
