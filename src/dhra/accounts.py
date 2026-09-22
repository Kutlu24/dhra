"""Accounts and private workspaces.

Same append-only-log discipline as the corpus itself (`dhra.store.events`)
applied to a genuinely separate concern: WHO can access a workspace, not
WHAT they researched. `accounts.jsonl` lives next to (not inside) any
corpus store -- one `AccountStore` per deployment, one `DHRARepo` store
directory per account (`AccountStore.user_store_path`).

Password hashing is stdlib PBKDF2-HMAC-SHA256 (`hashlib.pbkdf2_hmac`),
not a new dependency -- matches this project's established low-dependency
style (see `dhra.evidence`'s module docstring for the same reasoning
applied elsewhere). 600_000 iterations follows OWASP's 2023 PBKDF2-SHA256
guidance.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dhra.store.events import EventLog
from dhra.ulid import new_ulid

_ACCOUNT_EVENT_TYPES = frozenset({"account.created"})
_PBKDF2_ITERATIONS = 600_000


class AccountsError(Exception):
    """A real, user-facing account failure (duplicate username, bad
    login) -- callers show this message directly, it's never a stand-in
    for an internal bug."""


@dataclass(frozen=True)
class Account:
    user_id: str
    username: str
    password_hash: str
    created_at: datetime


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, iterations_s, salt_hex, digest_hex = password_hash.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations_s))
    return hmac.compare_digest(digest.hex(), digest_hex)


class AccountStore:
    """`accounts_dir` holds `accounts.jsonl` (the account registry) and
    `users/<user_id>/store/` (one DHRARepo root per account, same shape
    as any other DHRARepo store -- see `dhra.repo.DHRARepo.__init__`)."""

    def __init__(self, accounts_dir: str | Path):
        self.accounts_dir = Path(accounts_dir)
        self.events = EventLog(self.accounts_dir / "accounts.jsonl", allowed_types=_ACCOUNT_EVENT_TYPES)
        self.users_dir = self.accounts_dir / "users"

    def _fold(self) -> tuple[dict[str, Account], dict[str, Account]]:
        by_id: dict[str, Account] = {}
        by_username: dict[str, Account] = {}
        for event in self.events.read_all():
            account = Account(
                user_id=event["user_id"],
                username=event["username"],
                password_hash=event["password_hash"],
                created_at=datetime.fromisoformat(event["created_at"]),
            )
            by_id[account.user_id] = account
            by_username[account.username.lower()] = account
        return by_id, by_username

    def get_by_username(self, username: str) -> Account | None:
        _by_id, by_username = self._fold()
        return by_username.get(username.lower())

    def get_by_id(self, user_id: str) -> Account | None:
        by_id, _by_username = self._fold()
        return by_id.get(user_id)

    def user_store_path(self, user_id: str) -> Path:
        return self.users_dir / user_id / "store"

    def create_account(self, username: str, password: str) -> Account:
        username = username.strip()
        if not username:
            raise AccountsError("Username is required.")
        if len(password) < 8:
            raise AccountsError("Password must be at least 8 characters.")
        if self.get_by_username(username) is not None:
            raise AccountsError("That username is already taken.")

        user_id = new_ulid()
        created_at = datetime.now(timezone.utc)
        self.events.append(
            "account.created",
            user_id=user_id,
            username=username,
            password_hash=hash_password(password),
            created_at=created_at.isoformat(),
        )
        self.user_store_path(user_id).mkdir(parents=True, exist_ok=True)
        return Account(user_id=user_id, username=username, password_hash="", created_at=created_at)

    def authenticate(self, username: str, password: str) -> Account:
        account = self.get_by_username(username)
        if account is None or not verify_password(password, account.password_hash):
            raise AccountsError("Incorrect username or password.")
        return account
