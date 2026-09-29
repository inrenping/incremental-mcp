"""Mint short-lived probe tokens using the production secret from local .env.

Only the resulting tokens are printed; the secret itself is never emitted.
Tokens expire in 5 minutes and are used solely to exercise the /mcp endpoint.
"""

import time

import jwt

from app.config import settings
from app.mcp_server import MCP_RESOURCE

now = int(time.time())
base = {"sub": "1", "iat": now, "exp": now + 300}


def mk(extra=None):
    payload = dict(base)
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


print("RESOURCE=" + str(MCP_RESOURCE))
print("T_WITH_AUD=" + mk({"aud": MCP_RESOURCE, "scope": "read"}))
print("T_NO_AUD=" + mk({"scope": "read"}))
print("T_BAD_AUD=" + mk({"aud": "https://evil.example/mcp", "scope": "read"}))
