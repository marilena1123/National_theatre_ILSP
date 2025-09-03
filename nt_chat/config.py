import decouple

TOP_K_RESULTS = 10
RESPONSE_TIME_OUT = 140

OPENAI_KEY = decouple.config("OPENAI_API_KEY", "")
# https://platform.openai.com/account/rate-limits
MODEL_NAME = decouple.config("MODEL_NAME", default="gpt-3.5-turbo")
SQLITE_DB_PATH = decouple.config("SQLITE_DB_PATH", "")
UNICODE_PLUGIN_PATH = decouple.config("UNICODE_PLUGIN_PATH", "")
USE_CACHE = decouple.config("USE_CACHE", default=False, cast=bool)
MAX_PARALLEL_CALLS = decouple.config("MAX_PARALLEL_CALLS", default=32, cast=int)
LOGGING_FILE = decouple.config("LOGGING_FILE", default="/app/logs/nt_app.log")
