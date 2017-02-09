import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

import django
if hasattr(django, 'setup'):
    django.setup()

from django.core import management

apps = sys.argv[1:]

if not apps:
    apps = [
        'tests.cases.resources.tests',
        'tests.cases.forms.tests',
        'tests.cases.base.tests',
        'tests.cases.sets.tests',
    ]

management.call_command('test', *apps, interactive=False)
