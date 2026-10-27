"""Prepaid credit packs: the accounting pattern.

Semantics (the fleet's, unchanged — buyers plan around them):

- Minting is idempotent on the payment's identity: re-presenting a
  settled payment returns the pack it already bought, never a second
  pack.
- A pack is bound to ONE purpose key (here: the stall name) and a
  credit balance; debits are atomic (BEGIN IMMEDIATE).
- Exhausted pack -> PackError 402. Expired pack -> PackError 410.
- NO silent fallback: a refused pack never becomes a per-call charge.
- Balance reads are free and never debit.
"""

from __future__ import annotations

import secrets
import sqlite3
import threading
import time

EXPIRY_SECONDS = 90 * 24 * 3600


class PackError(Exception):
    def __init__(self, code: str, message: str, http_status: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _now_iso(epoch: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch or time.time()))


class PackStore:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS packs (
                pack_id TEXT PRIMARY KEY,
                purpose TEXT NOT NULL,
                credits_total INTEGER NOT NULL,
                credits_left INTEGER NOT NULL,
                created_epoch REAL NOT NULL,
                expires_epoch REAL NOT NULL,
                mint_key TEXT UNIQUE
            );
            """
        )
        self._conn.commit()

    def mint(self, purpose: str, credits: int, mint_key: str | None) -> dict:
        with self._lock:
            if mint_key:
                row = self._conn.execute(
                    "SELECT * FROM packs WHERE mint_key = ?", (mint_key,)
                ).fetchone()
                if row is not None:
                    return self._view(row)
            now = time.time()
            pack_id = "pack_" + secrets.token_hex(16)
            self._conn.execute(
                "INSERT INTO packs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pack_id, purpose, credits, credits, now, now + EXPIRY_SECONDS, mint_key),
            )
            self._conn.commit()
            return self.balance(pack_id)

    def balance(self, pack_id: str, purpose: str | None = None) -> dict:
        row = self._conn.execute(
            "SELECT * FROM packs WHERE pack_id = ?", (pack_id,)
        ).fetchone()
        if row is None:
            raise PackError("unknown_pack", "unknown pack_id", 404)
        if purpose is not None and row["purpose"] != purpose:
            raise PackError("wrong_purpose", "pack is bound to a different purpose", 403)
        return self._view(row)

    def debit(self, pack_id: str, purpose: str, credits: int = 1) -> dict:
        """Atomically spend credits. Raises PackError (410 expired /
        402 exhausted) without debiting anything."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT * FROM packs WHERE pack_id = ?", (pack_id,)
                ).fetchone()
                if row is None:
                    raise PackError("unknown_pack", "unknown pack_id", 404)
                if row["purpose"] != purpose:
                    raise PackError("wrong_purpose", "pack is bound to a different purpose", 403)
                if time.time() >= row["expires_epoch"]:
                    raise PackError("pack_expired", "pack expired; renewal is a new pack", 410)
                if row["credits_left"] < credits:
                    raise PackError("pack_exhausted", "pack has no credits left", 402)
                self._conn.execute(
                    "UPDATE packs SET credits_left = credits_left - ? WHERE pack_id = ?",
                    (credits, pack_id),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            return self.balance(pack_id)

    @staticmethod
    def _view(row: sqlite3.Row) -> dict:
        return {
            "pack_id": row["pack_id"],
            "purpose": row["purpose"],
            "credits_total": row["credits_total"],
            "credits_left": row["credits_left"],
            "created_at": _now_iso(row["created_epoch"]),
            "expires_at": _now_iso(row["expires_epoch"]),
            "expired": time.time() >= row["expires_epoch"],
        }
