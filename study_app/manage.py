#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'study_app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
                raise ImportError(
            "Couldn't import Django. Ensure Django is installed in your environment. "
            "You may need to activate your virtual environment or install Django using pip."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
