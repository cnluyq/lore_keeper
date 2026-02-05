# problems/templatetags/problem_extras.py
import json
from pathlib import PurePath
from django import template
import os

register = template.Library()

# Delimiter for storing multiple filenames in a single string
FILE_DELIMITER = '|||'

@register.filter
def basename(value):
    """
    去掉文件路径，只留文件名。
    用法：{{ problem.root_cause_file.name|basename }}
    """
    if not value:
        return ''
    return PurePath(value).name

@register.filter
def get_field_files(problem, field):
    """
    Return list of (filename, url) tuples for a multi-file field.
    Usage: {{ problem|get_field_files:'root_cause' }}
    Files are stored at: uploads/<id>/<field>/<filename>
    """
    file_field = getattr(problem, f'{field}_file')
    if not file_field or not file_field.name:
        return []

    file_path = file_field.name

    # Check if it's new multi-file format (contains ||| delimiter)
    if FILE_DELIMITER in file_path:
        filenames = file_path.split(FILE_DELIMITER)
        return [(f, f'/uploads/{problem.id}/{field}/{f}') for f in filenames]
    else:
        # Single file format - just the filename stored directly
        # Generate URL as /uploads/<id>/<field>/<filename>
        filename = os.path.basename(file_path)
        return [(filename, f'/uploads/{problem.id}/{field}/{filename}')]

@register.filter
def get_file_count(file_field_value):
    """
    Return the count of files stored in a FileField value.
    Usage: {{ problem.root_cause_file.name|get_file_count }}
    """
    if not file_field_value:
        return 0
    if FILE_DELIMITER in file_field_value:
        return len(file_field_value.split(FILE_DELIMITER))
    return 1  # Single file


# Utility functions used in views
def parse_files(file_field_value):
    """Parse 'file1.pdf|||file2.doc' -> ['file1.pdf', 'file2.doc']"""
    if not file_field_value:
        return []
    return file_field_value.split(FILE_DELIMITER)

def build_filename_string(filenames):
    """Build ['file1.pdf', 'file2.doc'] -> 'file1.pdf|||file2.doc'"""
    return FILE_DELIMITER.join(filenames)
