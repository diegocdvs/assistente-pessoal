"""Authentication providers."""
from app.auth.oauth import OAuthProvider, OAuthTokenError, StaticOAuthProvider
from app.auth.microsoft import MicrosoftOAuthProvider

__all__ = [
    "MicrosoftOAuthProvider",
    "OAuthProvider",
    "OAuthTokenError",
    "StaticOAuthProvider",
]
