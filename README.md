# Lore Keeper

[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Django-based knowledge and experience tracking application designed for professionals who need to systematically document problems, solutions, and daily achievements.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Deployment](#deployment)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

### Problem Tracking
- **Multi-file Attachments**: Upload multiple files for root causes, solutions, and other documentation
- **Markdown & Plain Text Editor**: Choose between Markdown or plain text editing modes
- **Sensitive Data Masking**: Automatic detection and redaction of sensitive information (SSNs, emails, custom patterns)
- **Public/Private Sharing**: Share problems via unique UUID tokens with granular privacy controls
- **Full-text Search**: Search across all problem fields including keywords, descriptions, and solutions

### Daily Journal (CV Base)
- **Calendar-based Interface**: Visual calendar for navigating daily records
- **Date-based Organization**: Each user maintains unique daily entries
- **Rich Content Support**: Markdown support with image embedding
- **File Attachments**: Attach multiple files to daily entries
- **Automatic Cleanup**: Orphaned image files are automatically removed

### Security & Data Management
- **User Authentication**: Django-based authentication with optional registration
- **Access Control**: Role-based permissions (superuser, staff, regular users)
- **Encrypted Export/Import**: ChaCha20Poly1305 encryption for data portability with PBKDF2 key derivation
- **Sensitive Word Management**: Configurable sensitive word patterns with replacement strings
- **Resource Management**: Track disk usage and identify orphaned files

### Administration
- **Site Configuration**: Customizable pagination limits and file size restrictions
- **User Management**: Staff members can manage user accounts and permissions
- **Resource Monitoring**: Dashboard for tracking disk usage and large files
- **Static File Serving**: Configurable static file URLs and paths

## Architecture

### Tech Stack
- **Backend**: Django 4.2
- **Database**: SQLite (default, configurable for PostgreSQL/MySQL)
- **Frontend**: Bootstrap for responsive UI, Marked.js for Markdown rendering
- **Security**: ChaCha20Poly1305 encryption (via cryptography library)
- **File Storage**: Filesystem storage with custom multi-file handling

### Project Structure
```
lore_keeper/
├── problem_manager/          # Django project configuration
├── problems/                 # Main application
│   ├── models.py            # Problem, CvBase, SensitiveWord, SiteConfig
│   ├── views.py             # Business logic (1638 lines)
│   ├── forms.py             # Form definitions
│   ├── urls.py              # URL routing
│   ├── admin.py             # Django admin configuration
│   ├── sensitive_utils.py  # Sensitive data processing
│   └── templates/problems/  # HTML templates (17 files)
├── static/                   # Static assets (13 files)
├── uploads/                  # User-uploaded content
└── requirements.txt          # Python dependencies
```

### Data Models
- **Problem**: Stores problems with keywords, descriptions, root causes, solutions, and file attachments
- **CvBase**: Daily journal entries with date-based organization
- **SensitiveWord**: Configurable patterns for sensitive data detection
- **SiteConfig**: Singleton model for site-wide settings

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd lore_keeper
```

### Step 2: Set Up Virtual Environment
```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Database Setup
```bash
# Create migrations
python manage.py makemigrations
python manage.py makemigrations problems

# Apply migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser
```

### Step 5: Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Step 6: Run the Development Server
```bash
python manage.py runserver
```

Access the application at `http://127.0.0.1:8000/`

## Configuration

### Site Settings
Edit `problem_manager/settings.py` to configure:

- **Registration**: Set `REGISTRATION_OPEN = True` to enable self-registration
- **Allowed Hosts**: Add your domain to `ALLOWED_HOSTS`
- **Secret Key**: Replace `django-insecure-replace-me-in-production` with a secure key
- **Database**: Configure `DATABASES` for PostgreSQL/MySQL in production

### Site Configuration
Access `/site-config/edit/` as a superuser to configure:
- **Items per Page**: Number of items displayed per list page (1-100, default: 10)
- **Maximum File Size**: Upload limit (1-1000, unit: KB/MB, default: 2MB)

### Static Files for Production
For production deployments (e.g., PythonAnywhere):

1. **Configure Static Files**:
   ```
   URL: /static/
   Directory: /home/user/lore_keeper/staticfiles/
   ```

2. **Configure Media Files**:
   ```
   URL: /uploads/
   Directory: /home/user/lore_keeper/uploads/
   ```

## Usage

### Getting Started
1. Register a new account or login with existing credentials
2. Navigate to the problem list at `/` to view existing problems
3. Click "Add New Problem" to create your first entry
4. Use the calendar interface to create daily journal entries

### Problem Management
- **Create**: Click "Add New Problem" from the problem list
- **Edit**: Click the edit button on any problem you own
- **Delete**: Remove problems with associated files
- **Search**: Use the search bar to filter by keywords, title, or content
- **Share**: Use the public token to share problems with others

### Daily Journal
- **Calendar View**: Access CV Base from the main navigation to see a calendar view
- **Add Entry**: Click on any date to create or edit a daily entry
- **Rich Text**: Use Markdown for formatted content with image embedding
- **Attachments**: Upload files relevant to each day's work

### User Management (Staff Only)
- **View Users**: Navigate to `/staff/users/` to see all registered users
- **Add User**: Use `/staff/users/add/` to create staff accounts
- **Manage Access**: Toggle user activity or delete accounts as needed

### Data Export/Import (Superuser Only)
- **Export**: Send POST request to `/export/` with password in JSON body
- **Import**: Send POST request to `/import/` with password and encrypted file
- **Format**: Encrypted tar.gz containing `items.json`, `cv_base_records.json`, and `uploads/`

### Resource Management (Superuser Only)
- **Monitor Usage**: View disk usage at `/staff/resource-management/`
- **Clean Up**: Identify and delete orphaned image files
- **Large Files**: Track files exceeding configurable size thresholds

## Deployment

### Production Settings
1. Set `DEBUG = False` in `settings.py`
2. Update `ALLOWED_HOSTS` with your production domain
3. Configure a production database (PostgreSQL recommended)
4. Set up a proper secret key using environment variables
5. Configure static file serving through Nginx/Apache

### Environment Variables
Consider using `python-decouple` or similar for configuration:
```python
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
DATABASE_URL = config('DATABASE_URL')
```

### Nginx Configuration
Basic Nginx configuration for Django:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /uploads/ {
        alias /path/to/uploads/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### PythonAnywhere Deployment
1. Create a web app using manual configuration
2. Set up virtualenv and install dependencies
3. Configure static files as mentioned above
4. Update `ALLOWED_HOSTS` with your PythonAnywhere domain
5. Reload the web app using the dashboard

## Development

### Code Style
- Follow Django conventions for function-based views
- Use snake_case for variables and functions
- Use PascalCase for classes
- Maintain consistent import ordering: standard library, third-party, local

### Project-Specific Patterns
- Multi-file uploads use `|||` delimiter for filename storage
- Direct SQL updates for file fields to bypass Django validation
- Session-based image storage for markdown editor
- Custom decorators for access control (see AGENTS.md for details)

### Contributing
Please read [AGENTS.md](AGENTS.md) for detailed development guidelines before contributing.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code of Conduct
Be respectful and constructive in all interactions. Focus on technical discussions and improving the codebase.

## Troubleshooting

### Common Issues

**Static files not loading**:
```bash
python manage.py collectstatic --noinput
```

**Database migration errors**:
```bash
python manage.py migrate --run-syncdb
```

**File upload issues**:
- Check `MEDIA_ROOT` and `MEDIA_URL` settings
- Ensure proper permissions on the uploads directory
- Verify file size limits in site configuration

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Django Framework: https://www.djangoproject.com/
- Bootstrap: https://getbootstrap.com/
- Marked.js: https://marked.js.org/
- Cryptography Library: https://cryptography.io/

## Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Last Updated**: March 2026
**Version**: 1.0.0
