from routes.admin._blueprint import (
    admin_bp,
    login_required,
    _failed_logins,
    _prune_failed_logins,
    _client_ip,
    _check_admin_credentials,
    _save_uploaded_image,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_SECONDS,
    ADMIN_PASSWORD_HASH,
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
)

# Register all route sub-modules
from routes.admin import auth, posts, portfolio, orders, services, tools  # noqa: F401

__all__ = [
    'admin_bp',
    'login_required',
    '_failed_logins',
    '_prune_failed_logins',
    '_client_ip',
    '_check_admin_credentials',
    '_save_uploaded_image',
    'LOGIN_MAX_ATTEMPTS',
    'LOGIN_WINDOW_SECONDS',
    'ADMIN_PASSWORD_HASH',
    'ADMIN_PASSWORD',
    'ADMIN_USERNAME',
]
