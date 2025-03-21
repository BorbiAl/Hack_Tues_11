import os
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Run SQL script'

    def handle(self):
        script_path = os.path.join(settings.BASE_DIR, "core", "sql", "studyapp", "core", "MySQL", "script.sql")

        if not os.path.exists(script_path):
            self.stdout.write(self.style.ERROR(f"SQL script not found at: {script_path}"))
            return

        with open(script_path, 'r') as file:
            sql_script = file.read()

        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(sql_script)

        self.stdout.write(self.style.SUCCESS('Successfully executed the command'))