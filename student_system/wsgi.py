"""
WSGI config for student_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_system.settings')

application = get_wsgi_application()

# Automatically run database migrations on server startup
# Ensures tables (students_student, courses_course, etc.) always exist
try:
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"Startup migration notice: {e}", file=sys.stderr)
