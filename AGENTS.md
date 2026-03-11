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

# Run with verbose output
python manage.py test --verbosity=2
```

### Django Shell
```bash
# Open Django shell
python manage.py shell
```

## Code Style Guidelines

### Naming Conventions
- **Variables/Functions**: `snake_case` - e.g., `problem_list`, `get_file_count`, `parse_files`
- **Classes**: `PascalCase` - e.g., `Problem`, `SensitiveDataProcessor`, `RegisterForm`
- **Constants**: `UPPER_SNAKE_CASE` - e.g., `FILE_DELIMITER`, `MAX_FILE_SIZE`
- **Private methods**: `_leading_underscore` - e.g., `_parse_files`, `_build_filename_string`, `_scan_disk_upload_images`

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
- **Views**: Use function-based views with `@login_required` decorator for auth-required views.
- **URLs**: Defined in app-level `urls.py`, included in main `urlsconf` using `path()`. Use `name='...'` for reverse resolution.
- **Models**: Inherit from `django.db.models.Model`, use `Meta` class for ordering/options, implement `__str__()`.
- **Forms**: Use `forms.ModelForm` for Django model forms. Override `clean()` for custom validation.
- **Templates**: Located in `appname/templates/appname/` directories following Django conventions.
- **Decorators**: Use custom decorators like `@owner_or_superuser_required` and `@superuser_required` for access control.

### Direct SQL Patterns
Direct SQL is used sparingly for file field updates to bypass Django's FileField validation:
```python
from django.db import connection
cursor = connection.cursor()
cursor.execute(
    f"UPDATE {table_name} SET {file_field_column} = %s WHERE id = %s",
    [file_string,_obj.id]
)
```

### File Upload Handling
- Multi-file storage uses delimiter `'|||'` to join filenames in FileField.name.
- File paths: `uploads/<problem_id>/<field_base>/<filename>` (e.g., root_cause, solutions, others).
- Manual file handling: Use `FileSystemStorage` with custom directory paths.
- Session-based uploads: Store uploaded image filenames in `request.session['uploaded_images']`.

### Security
- **HTML escaping**: Sanitize HTML text fields via `html.escape()` in `ProblemForm.clean()`.
- **Sensitive data**: Use `SensitiveDataProcessor` for filtering and redacting with cached lookups.
- **Export/Import**: Use ChaCha20Poly1305 encryption for data export with PBKDF2 key derivation.
- **CSRF**: Use `@csrf_exempt` sparingly (e.g., for image upload endpoints).

### Authentication & Authorization
- User registration controlled by `REGISTRATION_OPEN` setting (default: False).
- Superuser-only views: Use `@superuser_required` or `@staff_member_required`.
- Owner access: Use `@owner_or_superuser_required` custom decorator.
- Permissions: Check `request.user.is_superuser` or `obj.created_by == request.user`.

### Error Handling
- Use `get_object_or_404()` for retrieving objects that may not exist.
- Use Django `messages` for user-level feedback (`messages.success`, `messages.error`, `messages.warning`).
- Use `try/except` with `print()` statements for debuggable errors in file operations.
- Use `HttpResponseForbidden` or `PermissionDenied` for access violations.

### Constants/Config
- Settings module: `problem_manager.settings`
- File delimiter constant: `FILE_DELIMITER = '|||'` in views.py and models.py
- Database: SQLite at `db.sqlite3`
- Media files served at `/uploads/` (see .gitignore)
- Site configuration: Single-row `SiteConfig` model retrieved via `SiteConfig.get_config()` classmethod.

### Signal Handlers
Define signal handlers at the bottom of models.py file using `@receiver` decorator. Example: `@receiver(post_delete, sender=Problem)` for auto-deleting files on problem deletion.

## Project Structure
- `problem_manager/` - Django project settings (settings.py, urls.py, wsgi.py)
- `problems/` - Main app with models, views, forms, templates, templatetags, sensitive_utils.py
- `static/` - Static assets (favicon)
- `uploads/` - User-uploaded files (ignored by git)

## Notes
- **No type hints** are currently used in this codebase.
- **No tests** currently exist - add test files in `problems/tests.py` or `problems/tests/` directories.
- **No linting/formatting tools** configured (no black, ruff, flake8, mypy setup).
- Current requirements: asgiref, Django 4.2, setuptools, sqlparse, tzdata, wheel, cryptography.
- Mix of English and Chinese comments in codebase.
- File field naming: `root_cause_file`, `solutions_file`, `others_file` store multiple filenames as delimiter-separated strings.
