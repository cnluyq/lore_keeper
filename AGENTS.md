# AGENTS.md
This file contains guidelines for agentic coding assistants working in this repository.

## Project Overview
A Django 4.2-based knowledge and experience tracking application with two main components:
- **Problems**: Track problems, root causes, and solutions with file attachments
- **CV Base**: Daily work/achievement journal with calendar-based interface

Both support multi-file uploads, markdown/plain text editor modes, sensitive data masking, public/private content sharing via UUID tokens, and data export/import with encryption.

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

### Static Files
```bash
# Collect static files (run after adding/updating static assets)
python manage.py collectstatic --noinput
```

### Running the Server
```bash
# Run development server
python manage.py runserver
python manage.py runserver [ip]:[port]
```

### Django Shell
```bash
# Open Django shell
python manage.py shell
```

## Testing

### Integration Tests
Integration test scripts are located at the project root and require the Django server to be running:
- `test_export.py` - Test data export functionality
- `test_import.py` - Test data import functionality
- `test_merge_import.py` - Test import with merged attachments
- `test_static_files.py` - Test static file accessibility

```bash
# Run integration test (requires running server)
python3 test_export.py
python3 test_import.py
python3 test_merge_import.py
python3 test_static_files.py
```

Note: No Django unit tests currently exist. Add tests in `problems/tests.py` or `problems/tests/`.

```bash
# Run Django tests (when added)
python manage.py test
python manage.py test problems
python manage.py test problems.tests.TestClassName.test_method_name --verbosity=2
```

## Code Style Guidelines

### Naming Conventions
- **Variables/Functions**: `snake_case` - e.g., `problem_list`, `get_file_count`, `parse_files`
- **Classes**: `PascalCase` - e.g., `Problem`, `SensitiveDataProcessor`, `RegisterForm`
- **Constants**: `UPPER_SNAKE_CASE` - e.g., `FILE_DELIMITER`, `MAX_FILE_SIZE`
- **Private methods**: `_leading_underscore` - e.g., `_parse_files`, `_build_filename_string`

### Import Organization
Order imports: standard library, third-party (Django first), then local. Group blank lines between sections.
```python
import json
import os
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Problem
from .forms import ProblemForm
```
Avoid duplicate imports.

### Formatting
- **No linting/formatting tools configured** - no black, ruff, flake8, mypy
- **No type hints** - the codebase does not use type hints
- **No explicit line length limit** - follow Django conventions (~79-120 chars)
- **Comments**: Mix of English and Chinese - maintain existing language per file

### Django Patterns

#### Views
- Use function-based views with `@login_required` decorator for auth-required views
- Custom access control decorators: `@owner_or_superuser_required`, `@cv_base_owner_or_superuser_required`, `@superuser_required`
- Custom decorators defined in views.py:82-95
- Use `@csrf_exempt` sparingly (e.g., for image upload endpoints in views.py:966)
- Use `@require_POST` for POST-only endpoints (views.py:1058)

#### URLs
- App-level URLs in `problems/urls.py (34 lines)
- Main URL conf in `problem_manager/urls.py (14 lines)
- Use `path()` with `name='...'` for reverse resolution
- Static file serving configured for MEDIA_URL

#### Models
- Inherit from `django.db.models.Model`
- Use `Meta` class for ordering and verbose_name
- Implement `__str__()` method
- Models in `problems/models.py`:
  - `Problem` (line 6): Main problem tracker with multi-file fields
  - `CvBase` (line 109): Daily CV/journal records
  - `SensitiveWord` (line 160): Sensitive data filtering
  - `SiteConfig` (line 176): Site-wide configuration (singleton pattern)

#### Forms
- Use `forms.ModelForm` for Django model forms
- Override `clean()` for custom validation
- Forms in `problems/forms.py`:
  - `ProblemForm` (line 8): HTML escapes all text fields
  - `CvBaseForm` (line 116): HTML escapes title, preserves markdown content
  - `RegisterForm`, `StaffUserCreationForm`
  - `SensitiveWordForm`, `SiteConfigForm`

#### Templates
- Located in `problems/templates/problems/`
- 17 HTML templates total
- Base template: `base.html`
- Problem templates: `problem_list.html`, `problem_form.html`, `view_detail.html`
- CV Base templates: `cv_base_list.html`, `cv_base_form.html`, `cv_base_detail.html`
- User management: `user_list.html`, `user_add.html`, `user_delete_confirm.html`
- Sensitive words: `sensitive_word_list.html`, `sensitive_word_form.html`
- Site config: `site_config_edit.html`
- Resource management: `resource_management.html`
- Auth: `login.html`, `register.html`

#### Template Tags
- Custom tags in `problems/templatetags/problem_extras.py`
- Key filters:
  - `basename`: Extract filename from path
  - `get_field_files`: Get list of (filename, url) tuples for multi-file fields
  - `get_file_count`: Count files in a multi-file field

### File Upload Handling
- Multi-file storage uses delimiter `'|||'` (FILE_DELIMITER constant)
- Delimiter defined in: models.py:28, views.py:51, templatetags/problem_extras.py:10
- Problem file paths: `uploads/<problem_id>/<field_name>/<filename>` (e.g., root_cause, solutions, others)
- CvBase file paths: `uploads/cv_base/<cv_base_id>/<field_name>/<filename>` (e.g., content)
- Uploaded images: `uploads/upload_images/<filename>`
- Manual file handling: Use `FileSystemStorage` with custom directory paths
- Session-based uploads: Store uploaded image filenames in `request.session['uploaded_images']`
- File size validation via `SiteConfig.get_config().get_max_file_size_bytes()`

### Direct SQL Patterns
Direct SQL is used for file field updates to bypass Django's FileField validation:
```python
from django.db import connection
cursor = connection.cursor()
cursor.execute(
    f"UPDATE {table_name} SET {file_field_column} = %s WHERE id = %s",
    [file_string, _obj.id]
)
```
Used in:
- `problem_add` view (views.py:271-274)
- `problem_edit` view (views.py:481-483)
- `cv_base_add` view (views.py:1462-1465)
- `cv_base_edit` view (views.py:1286-1289, 1322-1325)

### Security
- **HTML escaping**: Auto-escaped in form `clean()` methods (ProblemForm, CvBaseForm title)
- **No escaping for markdown**: Content in markdown editor mode is NOT escaped to preserve formatting
- **Sensitive data**: `SensitiveDataProcessor` from `sensitive_utils.py` with 5-minute cache
- **Export/Import**: ChaCha20Poly1305 encryption with PBKDF2 key derivation (100,000 iterations, salt: 'lore_keeper_sb')
- **CSRF**: Minimal use of `@csrf_exempt` (only for upload_image endpoint)
- **Authentication**: Registration controlled by `REGISTRATION_OPEN` setting (default: False in settings.py:67)
- **File access control**: `owner_or_superuser_required` decorator ensures users can only access their own content
- **Public sharing**: UUID-based `public_token` field allows public read access when `is_public=True`

### Error Handling
- Use `get_object_or_404()` for retrieving objects that may not exist
- Use Django `messages` for user-level feedback (`messages.success`, `messages.error`, `messages.warning`)
- Use `try/except` with `print()` statements for debuggable errors in file operations
- Use `HttpResponseForbidden` or `PermissionDenied` for access violations (views.py:179, 357, 538, 634, 727, 869, 1238, 1516, 1526, 1538)
- No structured logging - uses `print()` for debugging

### Project Structure
```
lore_keeper/
├── problem_manager/           # Django project settings
│   ├── settings.py           # Project configuration
│   ├── urls.py               # Main URL configuration
│   └── wsgi.py               # WSGI entry point
├── problems/                 # Main app
│   ├── models.py             # Problem, CvBase, SensitiveWord, SiteConfig models
│   ├── views.py              # All views (1638 lines)
│   ├── forms.py              # All forms
│   ├── urls.py               # App URLs (34 lines)
│   ├── admin.py              # Django admin configuration
│   ├── sensitive_utils.py    # Sensitive data processing
│   ├── templatetags/
│   │   └── problem_extras.py # Custom template filters
│   └── templates/problems/   # HTML templates (17 files)
├── static/                   # Static assets (bootstrap, marked, prismjs, clipboard)
├── staticfiles/              # Collected static files
├── uploads/                  # User-uploaded files (ignored by git)
│   ├── <problem_id>/        # Problem-specific uploads
│   │   ├── root_cause/
│   │   ├── solutions/
│   │   └── others/
│   ├── cv_base/             # CvBase-specific uploads
│   │   └── <cv_base_id>/
│   │       └── content/
│   └── upload_images/       # Editor images
├── db.sqlite3               # SQLite database
├── manage.py                # Django management script
├── requirements.txt         # Python dependencies
└── test_*.py               # Integration tests
```

### Constants/Config
- Settings module: `problem_manager.settings`
- File delimiter: `FILE_DELIMITER = '|||'` (in models.py:28, views.py:51)
- Database: SQLite at BASE_DIR / 'db.sqlite3'
- Media files served at `/uploads/` (MEDIA_URL in settings.py:53)
- Media root: BASE_DIR / 'uploads' (MEDIA_ROOT in settings.py:54)
- Login URL: '/login/' (LOGIN_URL in settings.py:61)
- Login redirect: '/' (LOGIN_REDIRECT_URL in settings.py:64)
- Registration: `REGISTRATION_OPEN = False` (settings.py:67)
- Site config: Single-row `SiteConfig` model retrieved via `SiteConfig.get_config()` classmethod
- Default items per page: 10 (SiteConfig default)
- Default max file size: 2MB (SiteConfig default)

### Signal Handlers
Signal handlers defined at bottom of models.py (line 221-322):
- `@receiver(post_delete, sender=Problem)` (line 228): Auto-deletes uploaded files on Problem deletion
- `@receiver(post_delete, sender=CvBase)` (line 268): Auto-deletes uploaded files and cleans up orphaned images on CvBase deletion

### Key Features

#### Multi-file Upload System
- Uses `|||` delimiter to store multiple filenames in single FileField.name
- Upload processing via temporary directories then move to final location
- Delete individual files via `delete_file_from_disk()` (views.py:66-76, 1618-1628)
- Utilities in models: `_parse_files()`, `build_filename_string()`, `get_*_files()`, `add_*_file()`, `remove_*_file()`

#### Sensitive Data Handling
- Model in `models.py:SensitiveWord`
- Processor in `sensitive_utils.py:SensitiveDataProcessor`
- Caching: 5-minute cache via Django cache framework (sensitive_utils.py:16)
- Automatic detection and redaction on form submission
- Redacts SSN patterns (XXX-XX-XXXX) and email addresses (***@domain)
- Methods: `get_active_sensitive_words()`, `contains_sensitive_data()`, `desensitize_text()`, `validate_and_process_form()`

#### Public/Private Sharing
- `is_public` boolean field on Problem model
- `public_token` UUID field (auto-generated, unique)
- Public view: `/view/<uuid:token>/` endpoint (views.py:1176-1190)
- Anonymous users only see public problems
- Authenticated users see their problems plus public ones

#### Export/Import
- Requires superuser permissions (`@superuser_required`)
- Export: POST on `/export/` with password in JSON body
- Import: POST on `/import/` with password and file
- Encryption: ChaCha20Poly1305 with PBKDF2-HMAC-SHA256 derived key (100,000 iterations, salt: 'lore_keeper_sb')
- Export format: tar.gz containing `items.json`, `cv_base_records.json`, `uploads/` directory
- Import merges CvBase records by date, creates new Problems with new IDs
- ID mapping preserved for file path reconstruction

#### CV Base (Daily Journal)
- Model: `CvBase` (models.py:109-158)
- Calendar-based interface
- Unique dates per user
- Date-based navigation: `/cv-base/calendar-days/?year=YYYY&month=MM`
- Create by date: POST `/cv-base/create-by-date/`
- Support for markdown/plain text editing
- Multi-file attachments to `content` field
- Auto-cleanup of orphaned images on delete

#### Resource Management
- Endpoint: `/staff/resource-management/` (views.py:1082-1174)
- Superuser-only access
- Identifies orphaned upload_images not referenced in DB
- Identifies large files (> 512KB default, configurable)
- Shows file owners by scanning Problem and CvBase records
- Delete isolated images via POST `/staff/isolated-images/delete/`
- Home directory size via `du -sh` command

### Editor Types
Both Problem and CvBase models support two editor types:
- `plain`: Plain text, HTML escaped on save
- `markdown`: Markdown rendering, NOT escaped (preserves HTML/formatting)
- Editor choice stored per text field in `*_editor_type` fields
- Frontend uses marked.js for markdown rendering

### File Utilities
- `parse_files()`: Split `|||`-delimited string to list (views.py:54-58, templatetags:71-75)
- `build_filename_string()`: Join list with `|||` delimiter (views.py:61-63, templatetags:77-79)
- `delete_file_from_disk()`: Delete single file (Problem) (views.py:66-76)
- `delete_file_from_disk_cvbase()`: Delete single file (CvBase) (views.py:1618-1628)

### Current Dependencies
Requirements.txt content:
```
asgiref==3.9.1
Django==4.2
setuptools==80.9.0
sqlparse==0.5.3
tzdata==2025.2
wheel==0.45.1
cryptography==46.0.1
```

### Views Summary
Main views file (views.py): 1638 lines
- Problem CRUD: problem_list, problem_add, problem_edit, problem_delete
- Problem public view: view_detail (via UUID token)
- CV Base CRUD: cv_base_list, cv_base_add, cv_base_edit, cv_base_delete, cv_base_detail
- CV Base utilities: cv_base_calendar_days, cv_base_create_by_date, cv_base_cancel
- Auth: register_view, login_view, logout_view
- User management (superuser): user_list, user_add, user_toggle_active, user_delete
- Sensitive word management (superuser): sensitive_word_list, sensitive_word_add, sensitive_word_edit, sensitive_word_toggle, sensitive_word_delete
- Site config (superuser): site_config_edit
- Export/Import (superuser): export_json, import_json
- Image upload: upload_image (csrf_exempt)
- Session management: clear_uploaded_images
- Resource management (superuser): resource_management, isolated_images_delete

### URL Patterns Summary
- `/` - Problem list (public/private)
- `/add/` - Add new problem
- `/edit/<pk>/` - Edit problem
- `/delete/<pk>/` - Delete problem
- `/export/` - Export all data (superuser, POST)
- `/import/` - Import data (superuser, POST)
- `/view/<token>/` - Public view of problem via UUID token
- `/register/` - User registration
- `/login/` - User login
- `/logout/` - User logout
- `/cv-base/` - CV Base list
- `/cv-base/add/` - Add CV record
- `/cv-base/edit/<pk>/` - Edit CV record
- `/cv-base/detail/<pk>/` - View CV detail
- `/cv-base/delete/<pk>/` - Delete CV record
- `/cv-base/calendar-days/` - Get calendar dates (API)
- `/cv-base/create-by-date/` - Create record by date (API)
- `/cv-base/cancel/<pk>/` - Cancel edit/delete empty record
- `/sensitive-words/` - Sensitive word list
- `/upload-image/` - Upload image for editor
- `/upload_images/` - Image files served
- `/staff/users/` - User list
- `/users/<pk>/toggle/` - Toggle user active
- `/users/<pk>/delete/` - Delete user
- `/staff/resource-management/` - Resource management
- `/site-config/edit/` - Site configuration

### Admin Interface
Django admin configured for Problem model:
- list_display: id, title, key_words, created_by, create_time
- search_fields: title, key_words, description

### Common Tasks

#### Add New View Function
1. Add function in `problems/views.py`
2. Use appropriate decorators: `@login_required`, `@superuser_required`, `@owner_or_superuser_required`
3. Handle `request.method == 'POST'` for form submissions
4. Use `messages.success/error/warning` for user feedback
5. Add URL pattern in `problems/urls.py` with `name` parameter
6. Create template in `problems/templates/problems/` to render response

#### Add New Model Field
1. Add field to model class in `problems/models.py`
2. Create and run migrations:
   ```bash
   python manage.py makemigrations problems
   python manage.py migrate
   ```
3. Add to form fields list in `problems/forms.py` (inside class Meta)
4. Update template to display/handle field
5. If needed for export/import, add to values() list in export_json/import_json views

#### Add Custom Decorator
1. Import `get_object_or_404`, `PermissionDenied`
2. Define decorator function accepting `view_func`
3. Add access control logic
4. Return or raise `PermissionDenied`
5. Apply to views with `@decorator_name`

#### Handle Multi-file Upload
1. Check `request.FILES.getlist('field_name')`
2. Validate file size using `SiteConfig.get_config().get_max_file_size_bytes()`
3. Clean filename: `f.name.replace(' ', '_').replace('/', '_').replace('\\', '_')`
4. Use `FileSystemStorage` to save to target directory
5. Update DB via direct SQL or build `|||`-delimited string
6. Handle deletions via POST parameter with `request.POST.getlist('field_name_delete')`
