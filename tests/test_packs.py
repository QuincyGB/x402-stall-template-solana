"""Pack accounting semantics (see app/packs.py docstring)."""

import sqlite3
import time

import pytest

from app.packs import PackError, PackStore


@pytest.fixture()
def store(tmp_path):
    return PackStore(str(tmp_path / "stall.db"))


def test_mint_is_idempotent_on_payment_identity(store):
    a = store.mint("my-stall", 250, "payment-header:abc")
    b = store.mint("my-stall", 250, "payment-header:abc")
    assert a["pack_id"] == b["pack_id"]
    assert a["credits_left"] == 250


def test_debit_and_balance(store):
    pack = store.mint("my-stall", 250, None)
    out = store.debit(pack["pack_id"], "my-stall")
    assert out["credits_left"] == 249
    assert store.balance(pack["pack_id"])["credits_left"] == 249


def test_exhausted_is_402_and_wrong_purpose_is_403(store):
    pack = store.mint("my-stall", 1, None)
    store.debit(pack["pack_id"], "my-stall")
    with pytest.raises(PackError) as e:
        store.debit(pack["pack_id"], "my-stall")
    assert e.value.http_status == 402 and e.value.code == "pack_exhausted"
    with pytest.raises(PackError) as e:
        store.balance(pack["pack_id"], "other-stall")
    assert e.value.http_status == 403


def test_expired_is_410(store, tmp_path):
    pack = store.mint("my-stall", 250, None)
    conn = sqlite3.connect(str(tmp_path / "stall.db"))
    conn.execute(
        "UPDATE packs SET expires_epoch = ? WHERE pack_id = ?",
        (time.time() - 1, pack["pack_id"]),
    )
    conn.commit()
    with pytest.raises(PackError) as e:
        store.debit(pack["pack_id"], "my-stall")
    assert e.value.http_status == 410
