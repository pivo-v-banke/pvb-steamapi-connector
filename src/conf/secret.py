import os

from utils.type_cast import strtobool

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "default")
API_SECRET_KEY_REQUIRED = strtobool(os.getenv("API_SECRET_KEY_REQUIRED", "true"))
