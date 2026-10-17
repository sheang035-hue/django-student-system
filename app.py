"""
Application entry-point alias for Cloud platforms (such as Render)
that default to `gunicorn app:app` or `app.py`.
"""
import sys
from django.core.management import call_command
from student_system.wsgi import application

# Automatically run database migrations on server startup
# Ensures tables (students_student, courses_course, etc.) always exist
try:
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"Startup migration notice: {e}", file=sys.stderr)

# Expose WSGI application callable as `app`
app = application
