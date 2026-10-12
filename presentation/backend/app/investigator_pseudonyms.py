"""Pseudonyms for identifiers in outbound Investigator requests (operator decision 2026-10-12).

SSH usernames, IP addresses and person IDs are replaced by stable keyed
pseudonyms (USER-…, IP-…, PERSON-…) before a request leaves for OpenAI, and
mapped back in the answer locally. The key is DCG_PSEUDONYM_SALT or a random
per-install key kept in the data folder (never committed); the mapping never
leaves the machine. The same identifier always gets the same pseudonym, so the
model can still tell that two events involve the same person or address.
"""
import hashlib
import hmac
import re
import secrets
from pathlib import Path

from presentation.backend.app.authentication import local_setting
from presentation.backend.app.incident_store import _db_path

IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PERSON = re.compile(r"\bP\d{3,8}\b")
TOKEN = re.compile(r"\b(?:USER|IP|PERSON)-[0-9A-F]{10}\b")
PERSON_KEYS = {"person_id", "nearest_employee_id", "recognized_person_id"}
IP_KEYS = {"source_ip", "ip", "ip_address"}
USER_KEYS = {"usernames", "username", "user"}
NOT_IDENTIFIERS = {None, "", "UNKNOWN", "NONE"}


def _key():
    configured = local_setting("DCG_PSEUDONYM_SALT")
    if configured:
        return configured.encode()
    path = Path(_db_path()).parent / ".investigator_pseudonym_key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip().encode()


class Pseudonymizer:
    def __init__(self):
        self.key = _key()
        self.mapping = {}

    def token(self, prefix, value):
        value = str(value)
        if value.upper() in NOT_IDENTIFIERS:
            return value
        pseudonym = prefix + "-" + hmac.new(self.key, (prefix + ":" + value).encode(), hashlib.sha256).hexdigest()[:10].upper()
        self.mapping[pseudonym] = value
        return pseudonym

    def text(self, value):
        value = IPV4.sub(lambda m: self.token("IP", m.group(0)), value)
        value = PERSON.sub(lambda m: self.token("PERSON", m.group(0)), value)
        for pseudonym, original in list(self.mapping.items()):
            if pseudonym.startswith("USER-") and len(original) > 2:
                value = re.sub(r"\b" + re.escape(original) + r"\b", pseudonym, value)
        return value

    def mask(self, value, key=None):
        if isinstance(value, dict):
            return {k: self.mask(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.mask(v, key) for v in value]
        if isinstance(value, str):
            if key in USER_KEYS:
                return self.token("USER", value)
            if key in IP_KEYS:
                return self.token("IP", value)
            if key in PERSON_KEYS:
                return self.token("PERSON", value)
            return self.text(value)
        return value

    def unmask(self, answer):
        return TOKEN.sub(lambda m: self.mapping.get(m.group(0), m.group(0)), answer)
