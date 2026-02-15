# AGENTS.md

This file contains guidelines for agentic coding assistants working in this repository.

## Project Overview
A Django-based knowledge and experience keeper application for tracking problems, solutions, and related resources.

## Build/Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations
python manage.py makemigrations problems

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Running the Server
```bash
# Run development server
python manage.py runserver

# Run on specific host/port
python manage.py runserver [ip]:[port]
```

### Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test problems

# Run specific test (use full path to test class/method)
python manage.py test problems.tests.TestClassName.test_method_name
```

### Django Shell
```bash
# Open Django shell
python manage.py shell
```

## Code Style Guidelines

### Naming Conventions
- **Variables/Functions**: `snake_case` - e.g., `problem_list`, `get_file_count`
- **Classes**: `PascalCase` - e.g., `Problem`, `SensitiveDataProcessor`
- **Constants**: `UPPER_SNAKE_CASE` - e.g., `FILE_DELIMITER`, `MAX_FILE_SIZE`
- **Private methods**: `_leading_underscore` - e.g., `_parse_files`, `_build_filename_string`

### Import Organization (standard library, third-party, local)
```python
import json
import os
import uuid

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Problem
from .forms import ProblemForm
```

### Django Patterns
- **Views**: Use function-based views (as seen in this codebase). Decorate with `@login_required` for auth-required views.
- **URLs**: defined in app-level `urls.py` and included in main `urlsconf` using `path()`. Use names for reverse resolution: `name='problem_add'`
- **Models**: inherit from `django.db.models.Model`, use `Meta` class for options, implement `__str__()`.
- **Forms**: Use forms.ModelForm for Django model forms. Override `clean()` for custom validation.
- **Templates**: Follow Django template conventions located in appname/templates/appname/ directories.

### Error Handling
- Use `get_object_or_404()` for retrieving objects that may not exist.
- Use Django messages for user-level feedback.
- Use try/except with logging or print for debuggable errors in file operations.

### File Upload Handling
- Multi-file storage uses delimiter `'|||'` to join filenames in FileField.name.
- File paths: `uploads/<problem_id>/<field_base>/<filename>` (e.g., root_cause, solutions, others).

### Security
- HTML escaping: sanitize HTML in text fields via `html.escape()` (as done in ProblemForm.clean()).
- Sensitive data: use `SensitiveDataProcessor` for filtering and redacting.

### Constants/Config
- Settings module: `problem_manager.settings`
- Secret key: placeholder in settings file; replace for production
- Database: SQLite at `db.sqlite3`
- Media files served at `/uploads/` (see .gitignore)

## Project Structure
- `problem_manager/` - Django project settings (settings.py, urls.py, wsgi.py)
- `problems/` - Main app with models, views, forms, templates
- `static/` - Static assets (favicon)
- `uploads/` - User-uploaded files (ignored by git)

## Notes
- No type hints are currently used in this codebase.
- Add test files in `problems/tests.py` or `problems/tests/` directories following Django's test patterns.
- Current requirements: asgiref, Django 4.2, setuptools, sqlparse, tzdata, wheel, cryptography.
