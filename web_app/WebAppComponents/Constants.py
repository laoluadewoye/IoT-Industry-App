from os import getenv

# Get core database environmental variables
DEFAULTS: dict[str, str] = {
    'DB_HOST': 'mongo-db', 'DB_PORT': '27017', 'DB_USER': 'web_view',
    'DB_PASSWORD_FILE': '../secrets/web_view_password.txt', 'PROXY_HOST': 'localhost', 'PROXY_PORT': '8079'
}

DB_HOST: str = getenv('DB_HOST', DEFAULTS['DB_HOST'])
DB_PORT: str = getenv('DB_PORT', DEFAULTS['DB_PORT'])
DB_USER: str = getenv('DB_USER', DEFAULTS['DB_USER'])
DB_PASSWORD_FILE: str = getenv('DB_PASSWORD_FILE', DEFAULTS['DB_PASSWORD_FILE'])
PROXY_HOST: str = getenv('PROXY_HOST', DEFAULTS['PROXY_HOST'])
PROXY_PORT: str = getenv('PROXY_PORT', DEFAULTS['PROXY_PORT'])

# Reload speed
FRAGMENT_RERUN_SPEED: int = 5
DATA_UPDATE_SPEED: int = 3
