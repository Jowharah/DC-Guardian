"""Local-only HTTP Basic identity adapter for controlled prototype.

No default credentials. The username/password/role/zone values are supplied
through process environment variables or the local repository .env file. HTTP Basic is not a production session
system and must not be used over unencrypted network connections.
"""
import hmac
import os
from pathlib import Path
from dotenv import dotenv_values
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from presentation.backend.app.authorization import Principal, Permission, allowed

PROJECT_ENV = Path(__file__).resolve().parents[3] / ".env"
security = HTTPBasic(auto_error=False)

def local_setting(name: str) -> str:
    """Process environment takes precedence; local .env is a fallback."""
    if name in os.environ:
        return os.environ[name]
    if PROJECT_ENV.is_file():
        return str(dotenv_values(PROJECT_ENV).get(name) or "")
    return ""

def current_principal(credentials: HTTPBasicCredentials | None = Depends(security)) -> Principal:
    user = local_setting("DCG_LOCAL_USER")
    password = local_setting("DCG_LOCAL_PASSWORD")
    role = local_setting("DCG_LOCAL_ROLE")
    zones = local_setting("DCG_LOCAL_ZONES")
    valid = (
        bool(user and password and role and zones and credentials)
        and hmac.compare_digest(credentials.username.encode(), user.encode())
        and hmac.compare_digest(credentials.password.encode(), password.encode())
    )
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication required",
                            headers={"WWW-Authenticate": "Basic"})
    principal = Principal(user, frozenset({role}), frozenset(z.strip() for z in zones.split(",") if z.strip()))
    if not allowed(principal, Permission.INCIDENT_READ):
        raise HTTPException(status_code=403, detail="Access denied")
    return principal

def authorize(principal: Principal, permission: Permission, zone: str | None = None) -> None:
    if not allowed(principal, permission, zone):
        raise HTTPException(status_code=403, detail="Access denied")
