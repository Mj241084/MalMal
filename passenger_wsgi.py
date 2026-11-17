"""cPanel (Passenger) entry point. Settings come from .env, which config/settings loads."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from config.wsgi import application  # noqa: E402,F401
