import hashlib
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture()
def account_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "account.db"))
    monkeypatch.setattr(main, "PHOTO_DIR", str(tmp_path / "photos"))
    main.init_db()
    with TestClient(main.app) as client:
        yield client, tmp_path


def register(client, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def setup_pair(client):
    first = register(client, "delete@example.com")
    response = client.post(
        "/pair/setup",
        headers={"X-Auth-Token": first["token"]},
        json={"user_id": first["user_id"], "name": "Delete me"},
    )
    assert response.status_code == 200, response.text

    second = register(client, "partner@example.com")
    response = client.post(
        "/pair/setup",
        headers={"X-Auth-Token": second["token"]},
        json={
            "user_id": second["user_id"],
            "name": "Partner",
            "partner_code": first["pair_code"],
        },
    )
    assert response.status_code == 200, response.text
    return first, second


def test_delete_account_requires_current_password(account_api):
    client, _ = account_api
    user = register(client, "password@example.com")
    response = client.request(
        "DELETE",
        "/account",
        headers={"X-Auth-Token": user["token"]},
        json={"user_id": user["user_id"], "password": "wrong123"},
    )
    assert response.status_code == 401

    con = sqlite3.connect(main.DB)
    assert con.execute("SELECT 1 FROM users WHERE id=?", (user["user_id"],)).fetchone()
    con.close()


def test_delete_account_removes_linked_data_and_keeps_partner(account_api):
    client, tmp_path = account_api
    user, partner = setup_pair(client)
    uid = user["user_id"]
    partner_id = partner["user_id"]
    pair_key = f"{min(uid, partner_id)}:{max(uid, partner_id)}"
    photo_name = f"{uuid.uuid4().hex}.jpg"
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    photo_path = photo_dir / photo_name
    photo_path.write_bytes(b"photo")

    con = sqlite3.connect(main.DB)
    con.executescript(
        f"""
        UPDATE users SET avatar='/photos/{photo_name}' WHERE id={uid};
        INSERT INTO moods(user_id,mood,ts) VALUES({uid},'ok','2026-01-01');
        INSERT INTO journal(user_id,title,ts) VALUES({uid},'private','2026-01-01');
        INSERT INTO events(user_id,title,date) VALUES({uid},'private','2026-01-01');
        INSERT INTO taps(user_id,ts) VALUES({uid},'2026-01-01');
        INSERT INTO locations(user_id,lat,lon,ts) VALUES({uid},1,2,'2026-01-01');
        INSERT INTO locations(user_id,lat,lon,ts) VALUES({partner_id},3,4,'2026-01-01');
        INSERT INTO exact_widget_shares(owner_id,grantee_id,consented_at)
            VALUES({uid},{partner_id},'2026-01-01');
        INSERT INTO push_tokens(token,user_id,updated_at)
            VALUES('push-delete',{uid},'2026-01-01');
        INSERT INTO wishlist(pair_key,author_id,title,created_at)
            VALUES('{pair_key}',{partner_id},'shared','2026-01-01');
        INSERT INTO couple_games(pair_key,kind,state,updated_at)
            VALUES('{pair_key}','sync','{{}}','2026-01-01');
        INSERT INTO companions(pair_key,state,updated_at)
            VALUES('{pair_key}','{{}}','2026-01-01');
        INSERT INTO movie_rounds(pair_low_id,pair_high_id,status,created_at)
            VALUES({min(uid, partner_id)},{max(uid, partner_id)},'active','2026-01-01');
        INSERT INTO community_map_posts(
            pair_low_id,pair_high_id,created_by_user_id,country_code,photo,comment,
            low_approved,high_approved,created_at,updated_at)
            VALUES({min(uid, partner_id)},{max(uid, partner_id)},{uid},'RU',
            '/photos/{photo_name}','Map post',1,1,'2026-01-01','2026-01-01');
        INSERT INTO community_map_reports(post_id,reporter_user_id,reason,created_at)
            VALUES(last_insert_rowid(),{partner_id},'other','2026-01-01');
        INSERT INTO tg(user_id,tg_id) VALUES({uid},9001);
        INSERT INTO refs(tg_id,referrer) VALUES(9001,{uid});
        INSERT INTO tg_payments(charge_id,user_id,tg_id,currency,total_amount,payload,ts)
            VALUES('charge-delete',{uid},9001,'XTR',1,'premium:{uid}','2026-01-01');
        INSERT INTO referral_payouts(
            id,user_id,amount_rub,recipient,status,created_at)
            VALUES(1,{uid},100,'+79991234567 · Банк','paid','2026-01-01');
        INSERT INTO referral_rewards(
            referred_tg_id,referrer_user_id,referred_user_id,choice,status,
            amount_rub,bonus_days,payout_id,created_at)
            VALUES(9002,{uid},{partner_id},'cash','paid',100,7,1,'2026-01-01');
        """
    )
    email_hash = hashlib.sha256(b"delete@example.com").hexdigest()
    con.execute(
        "INSERT INTO auth_login_limits(scope,key_hash,failures,window_started_at) "
        "VALUES('email',?,1,1)",
        (email_hash,),
    )
    con.commit()
    con.close()

    response = client.request(
        "DELETE",
        "/account",
        headers={"X-Auth-Token": user["token"]},
        json={"user_id": uid, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True}

    con = sqlite3.connect(main.DB)
    assert con.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone() is None
    surviving = con.execute(
        "SELECT partner_id FROM users WHERE id=?", (partner_id,)
    ).fetchone()
    assert surviving == (None,)
    for table in ("moods", "journal", "events", "taps", "push_tokens", "tg"):
        assert con.execute(
            f"SELECT 1 FROM {table} WHERE user_id=?", (uid,)
        ).fetchone() is None
    anonymized = con.execute(
        "SELECT charge_id, user_id, tg_id, payload FROM tg_payments "
        "WHERE charge_id='charge-delete'"
    ).fetchone()
    assert anonymized == ("charge-delete", 0, 0, "")
    assert con.execute(
        "SELECT 1 FROM referral_rewards WHERE referrer_user_id=? OR referred_user_id=?",
        (uid, uid),
    ).fetchone() is None
    assert con.execute(
        "SELECT user_id,recipient,status,amount_rub FROM referral_payouts WHERE id=1"
    ).fetchone() == (0, "", "paid", 100)
    assert con.execute("SELECT 1 FROM locations WHERE user_id=?", (uid,)).fetchone() is None
    assert con.execute(
        "SELECT 1 FROM locations WHERE user_id=?", (partner_id,)
    ).fetchone()
    assert con.execute("SELECT 1 FROM wishlist WHERE pair_key=?", (pair_key,)).fetchone() is None
    assert con.execute("SELECT 1 FROM couple_games WHERE pair_key=?", (pair_key,)).fetchone() is None
    assert con.execute("SELECT 1 FROM companions WHERE pair_key=?", (pair_key,)).fetchone() is None
    assert con.execute(
        "SELECT 1 FROM movie_rounds WHERE pair_low_id=? OR pair_high_id=?",
        (uid, uid),
    ).fetchone() is None
    assert con.execute(
        "SELECT 1 FROM community_map_posts WHERE pair_low_id=? OR pair_high_id=?",
        (uid, uid),
    ).fetchone() is None
    assert con.execute("SELECT 1 FROM community_map_reports").fetchone() is None
    assert con.execute(
        "SELECT 1 FROM exact_widget_shares WHERE owner_id=? OR grantee_id=?",
        (uid, uid),
    ).fetchone() is None
    assert con.execute(
        "SELECT 1 FROM auth_login_limits WHERE scope='email' AND key_hash=?",
        (email_hash,),
    ).fetchone() is None
    con.close()
    assert not photo_path.exists()

    con = sqlite3.connect(main.DB)
    assert con.execute(
        "SELECT 1 FROM tg_payments WHERE charge_id='charge-delete'"
    ).fetchone() is not None
    con.close()
