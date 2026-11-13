"""API tests on a real PostgreSQL: auth, CSRF, roles, step-up, tenancy, quotes, snapshots.

All data is the demo's invented sample data (SAMPLE - NOT REAL). Skipped without a database;
see ``conftest.py``.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

import pyotp
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from quote_engine.api.deps import CSRF_HEADER
from quote_engine.db.base import Base
from quote_engine.db.models import (
    WORKSHOP_SCOPED,
    AuditLog,
    Client,
    ConstructionType,
    LoginAttempt,
    PriceEntry,
    PriceListVersion,
    Profile,
    ProfileSystem,
    Quote,
    QuoteRevision,
    Supplier,
    User,
    Workshop,
)
from quote_engine.db.models import Session as SessionRow
from quote_engine.db.repository import NotFoundError, Scoped
from quote_engine.services import auth, calculation, demo, workshops
from quote_engine.services import quotes as svc
from tests.api.conftest import PASSWORD, SampleWorkshop, log_in

API = "/api/v1"


def today() -> date:
    return datetime.now(UTC).date()


def system_id(api: TestClient) -> str:
    systems = api.get(f"{API}/systems").json()
    return str(systems[0]["id"])


def revision_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "margin_bp": 2500,
        "valid_days": 15,
        "transport_km": 40,
        "positions": [
            {
                "ref": "P1",
                "construction_type": "single_sash_tilt_turn",
                "width_mm": 800,
                "height_mm": 1400,
                "qty": 2,
                "colour": "white",
                "glass_build": "4-16-4",
                "openings": ["tilt_turn_right"],
                "readings": {"widths": [830, 832, 831], "heights": [1430, 1431, 1430]},
            },
            {
                "ref": "P2",
                "construction_type": "two_field_t_mullion",
                "width_mm": 1400,
                "height_mm": 1400,
                "qty": 1,
                "colour": "foil_one_side",
                "glass_build": "4-16-4",
                "openings": ["tilt_turn_left", "turn_right"],
                "installation": {"install": True, "old_window_removal": True},
            },
        ],
        "extras": [
            {"kind": "sill", "ref": "demo-sill", "qty": 1, "colour": "white", "length_mm": 800}
        ],
    }
    return {**body, **changes}


def new_quote(api: TestClient) -> dict[str, Any]:
    client = api.post(f"{API}/clients", json={"name": "Sample client", "place": "Sample town"})
    assert client.status_code == 201, client.text
    quote = api.post(
        f"{API}/quotes",
        json={"client_id": client.json()["id"], "profile_system_id": system_id(api)},
    )
    assert quote.status_code == 201, quote.text
    body: dict[str, Any] = quote.json()
    return body


def reauth(api: TestClient) -> None:
    assert api.post(f"{API}/auth/reauth", json={"password": PASSWORD}).status_code == 200


def admin_login(api: TestClient, db: Session, shop: SampleWorkshop) -> None:
    """Add an admin to ``shop``, log in and pass the TOTP step."""
    created = workshops.create_user(
        db, shop.workshop.id, "admin@example.invalid", PASSWORD, auth.ROLE_ADMIN
    )
    db.commit()
    log_in(api, "admin@example.invalid")
    secret = created.user.totp_secret
    assert secret is not None
    response = api.post(f"{API}/auth/totp", json={"code": pyotp.TOTP(secret).now()})
    assert response.status_code == 200, response.text


# --- migrations ---------------------------------------------------------------------------------


def test_migrations_match_the_models(db: Session) -> None:
    """The baseline migration creates exactly what the models describe."""
    context = MigrationContext.configure(db.connection(), opts={"compare_type": True})

    assert compare_metadata(context, Base.metadata) == []


# --- login, cookies, CSRF -----------------------------------------------------------------------


def test_login_sets_host_only_secure_cookies(api: TestClient, shop_a: SampleWorkshop) -> None:
    response = api.post(f"{API}/auth/login", json={"email": shop_a.email, "password": PASSWORD})

    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("__Host-session="))
    csrf = next(c for c in cookies if c.startswith("__Host-csrf="))
    for attribute in ("Secure", "Path=/", "SameSite=lax"):
        assert attribute in session
        assert attribute in csrf
    assert "HttpOnly" in session
    assert "HttpOnly" not in csrf
    assert response.json()["email"] == shop_a.email


def test_the_session_token_is_stored_only_as_a_hash(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    api.post(f"{API}/auth/login", json={"email": shop_a.email, "password": PASSWORD})
    token = api.cookies.get("__Host-session")
    assert token

    hashes = db.scalars(select(SessionRow.token_hash)).all()
    assert auth.hash_token(token) in hashes
    assert token not in hashes


def test_wrong_password_is_401_and_recorded(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    response = api.post(f"{API}/auth/login", json={"email": shop_a.email, "password": "nope"})

    assert response.status_code == 401
    assert response.json()["detail"] == "wrong email or password"
    failures = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(LoginAttempt.success.is_(False))
    )
    assert failures == 1


def test_unknown_email_gets_the_same_answer(api: TestClient, shop_a: SampleWorkshop) -> None:
    response = api.post(
        f"{API}/auth/login", json={"email": "nobody@example.invalid", "password": "nope"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "wrong email or password"


def test_five_failures_lock_the_username_for_15_minutes(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    for _ in range(5):
        api.post(f"{API}/auth/login", json={"email": shop_a.email, "password": "nope"})

    response = api.post(f"{API}/auth/login", json={"email": shop_a.email, "password": PASSWORD})

    assert response.status_code == 429


def test_a_new_login_gets_a_new_token(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    first = api.cookies.get("__Host-session")
    log_in(api, shop_a.email)

    assert api.cookies.get("__Host-session") != first


def test_unsafe_requests_need_the_csrf_header(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    del api.headers[CSRF_HEADER]

    assert api.get(f"{API}/clients").status_code == 200
    assert api.post(f"{API}/clients", json={"name": "Sample"}).status_code == 403
    api.headers[CSRF_HEADER] = "wrong"
    assert api.post(f"{API}/clients", json={"name": "Sample"}).status_code == 403


def test_logout_ends_the_session(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    token = api.cookies.get("__Host-session")

    assert api.post(f"{API}/auth/logout").status_code == 204
    api.cookies.set("__Host-session", str(token))
    assert api.get(f"{API}/auth/me").status_code == 401


def test_a_disabled_user_is_logged_out(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    user = db.scalars(select(User).where(User.email == shop_a.email)).one()
    user.is_active = False
    db.commit()

    assert api.get(f"{API}/clients").status_code == 401


# --- roles, TOTP, step-up -----------------------------------------------------------------------


def test_the_admin_needs_a_totp_code(api: TestClient, db: Session, shop_a: SampleWorkshop) -> None:
    created = workshops.create_user(
        db, shop_a.workshop.id, "admin@example.invalid", PASSWORD, auth.ROLE_ADMIN
    )
    db.commit()
    log_in(api, "admin@example.invalid")

    assert api.get(f"{API}/clients").status_code == 401
    secret = created.user.totp_secret
    assert secret is not None
    assert api.post(f"{API}/auth/totp", json={"code": pyotp.TOTP(secret).now()}).status_code == 200
    assert api.get(f"{API}/clients").status_code == 200


def test_the_owner_cannot_use_admin_endpoints(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)

    assert api.get(f"{API}/users").status_code == 403
    assert api.get(f"{API}/sessions").status_code == 403
    body = {"key": "x", "brand": "x", "series": "x", "depth_mm": 70}
    assert api.post(f"{API}/systems", json=body).status_code == 403


def test_export_and_erase_right_after_login(api: TestClient, shop_a: SampleWorkshop) -> None:
    """The login itself is a password check, so the first 15 minutes need no extra step."""
    log_in(api, shop_a.email)
    client = api.post(f"{API}/clients", json={"name": "Sample client", "phone": "000"}).json()

    exported = api.get(f"{API}/clients/{client['id']}/export")
    assert exported.status_code == 200
    assert exported.json()["client"]["name"] == "Sample client"

    erased = api.post(f"{API}/clients/{client['id']}/erase")
    assert erased.status_code == 200
    assert erased.json()["name"] == "(erased)"
    assert erased.json()["phone"] == ""
    assert erased.json()["erased_at"] is not None


def test_step_up_expires(api: TestClient, db: Session, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    client = api.post(f"{API}/clients", json={"name": "Sample client"}).json()
    for row in db.scalars(select(SessionRow)):
        row.reauth_at = datetime(2020, 1, 1, tzinfo=UTC)
    db.commit()

    assert api.get(f"{API}/clients/{client['id']}/export").status_code == 403
    reauth(api)
    assert api.get(f"{API}/clients/{client['id']}/export").status_code == 200


def test_reauth_with_a_wrong_password_is_401(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)

    assert api.post(f"{API}/auth/reauth", json={"password": "nope"}).status_code == 401


def test_guessing_the_step_up_password_ends_the_session(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    answers = [
        api.post(f"{API}/auth/reauth", json={"password": "nope"}).status_code for _ in range(5)
    ]

    assert answers == [401, 401, 401, 401, 429]
    assert api.get(f"{API}/auth/me").status_code == 401
    login = api.post(f"{API}/auth/login", json={"email": shop_a.email, "password": PASSWORD})
    assert login.status_code == 429


def test_guessing_totp_codes_ends_the_session(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    created = workshops.create_user(
        db, shop_a.workshop.id, "admin@example.invalid", PASSWORD, auth.ROLE_ADMIN
    )
    db.commit()
    secret = created.user.totp_secret
    assert secret is not None
    log_in(api, "admin@example.invalid")
    current = pyotp.TOTP(secret)
    wrong = next(
        code for code in ("000000", "111111", "222222") if not current.verify(code, valid_window=1)
    )

    answers = [api.post(f"{API}/auth/totp", json={"code": wrong}).status_code for _ in range(5)]

    assert answers == [401, 401, 401, 401, 429]
    assert api.post(f"{API}/auth/totp", json={"code": current.now()}).status_code == 401


# --- tenancy ------------------------------------------------------------------------------------


def fill_every_table(db: Session, shop: SampleWorkshop, api: TestClient) -> None:
    """Give ``shop`` at least one row in every workshop table."""
    log_in(api, shop.email)
    quote = new_quote(api)
    assert (
        api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body()).status_code == 200
    )
    assert (
        api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "sent"}).status_code == 200
    )
    accepted = api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "accepted"})
    assert accepted.status_code == 200, accepted.text
    payment = {"kind": "advance", "amount_cents": 100, "received_on": str(today())}
    assert api.post(f"{API}/quotes/{quote['id']}/payments", json=payment).status_code == 201
    system = db.scalars(
        select(ProfileSystem).where(ProfileSystem.workshop_id == shop.workshop.id)
    ).first()
    assert system is not None
    db.add(
        Profile(
            workshop_id=shop.workshop.id,
            profile_system_id=system.id,
            role="frame",
            code="SAMPLE-1",
            g_per_m=1000,
        )
    )
    db.add(ConstructionType(workshop_id=shop.workshop.id, key="fixed", enabled=True))
    db.commit()
    api.cookies.clear()


@pytest.mark.parametrize("model", WORKSHOP_SCOPED, ids=lambda m: m.__tablename__)
def test_another_workshops_rows_are_not_found(
    model: type[Base],
    api: TestClient,
    db: Session,
    shop_a: SampleWorkshop,
    shop_b: SampleWorkshop,
) -> None:
    fill_every_table(db, shop_b, api)
    theirs = db.scalars(
        select(model).where(model.workshop_id == shop_b.workshop.id)  # type: ignore[attr-defined]
    ).first()
    assert theirs is not None, f"the fixture made no {model.__tablename__} row"
    mine = Scoped(db, shop_a.workshop.id)

    with pytest.raises(NotFoundError):
        mine.get(model, theirs.id)
    assert all(row.workshop_id == shop_a.workshop.id for row in mine.all(model))  # type: ignore[attr-defined]
    with pytest.raises(NotFoundError):
        mine.delete(theirs)


def test_the_api_answers_404_for_another_workshops_ids(
    api: TestClient, db: Session, shop_a: SampleWorkshop, shop_b: SampleWorkshop
) -> None:
    fill_every_table(db, shop_b, api)
    b = shop_b.workshop.id
    client = db.scalars(select(Client).where(Client.workshop_id == b)).first()
    quote = db.scalars(select(Quote).where(Quote.workshop_id == b)).first()
    supplier = db.scalars(select(Supplier).where(Supplier.workshop_id == b)).first()
    prices = db.scalars(select(PriceListVersion).where(PriceListVersion.workshop_id == b)).first()
    system = db.scalars(select(ProfileSystem).where(ProfileSystem.workshop_id == b)).first()
    assert client is not None
    assert quote is not None
    assert supplier is not None
    assert prices is not None
    assert system is not None

    log_in(api, shop_a.email)
    reauth(api)
    assert api.get(f"{API}/clients/{client.id}").status_code == 404
    assert api.get(f"{API}/clients/{client.id}/export").status_code == 404
    assert api.post(f"{API}/clients/{client.id}/erase").status_code == 404
    assert api.get(f"{API}/quotes/{quote.id}").status_code == 404
    assert api.post(f"{API}/quotes/{quote.id}/revisions/1/calculate").status_code == 404
    assert api.get(f"{API}/price-lists/{prices.id}").status_code == 404
    assert api.get(f"{API}/systems/{system.id}/sheets").status_code == 404
    patch = {"name": "x", "kind": "glass"}
    assert api.patch(f"{API}/suppliers/{supplier.id}", json=patch).status_code == 404
    body = {"client_id": str(client.id), "profile_system_id": str(system.id)}
    assert api.post(f"{API}/quotes", json=body).status_code == 404
    bump = {"supplier_id": str(supplier.id), "bp": 400, "valid_from": str(today())}
    own_prices = api.get(f"{API}/price-lists").json()[0]["id"]
    assert api.post(f"{API}/price-lists/{own_prices}/bump", json=bump).status_code == 404
    listed = api.get(f"{API}/quotes").json()
    assert all(q["id"] != str(quote.id) for q in listed)


# --- quotes, calculation, snapshot --------------------------------------------------------------


def test_a_quote_from_draft_to_accepted(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    quote = new_quote(api)
    assert quote["number"] == f"{today().year}-0001"
    assert quote["status"] == "draft"

    saved = api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())
    assert saved.status_code == 200, saved.text
    assert [p["ref"] for p in saved.json()["revision"]["positions"]] == ["P1", "P2"]

    result = api.post(f"{API}/quotes/{quote['id']}/revisions/1/calculate")
    assert result.status_code == 200, result.text
    calc = result.json()
    assert set(calc) == {"cut_lists", "plans", "price", "warnings", "versions"}
    assert calc["price"]["total_cents"] > 0
    piece = calc["cut_lists"]["P1"]["pieces"][0]
    assert piece["formula"].endswith(f"= {piece['length_mm']}")

    assert (
        api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "sent"}).status_code == 200
    )
    accepted = api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "accepted"})
    assert accepted.status_code == 200
    assert accepted.json()["total_cents"] == calc["price"]["total_cents"]

    again = api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body(margin_bp=1000))
    assert again.status_code == 409
    assert api.post(f"{API}/quotes/{quote['id']}/revisions").status_code == 409


def test_the_accepted_snapshot_is_reproduced_from_the_stored_versions(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    quote = new_quote(api)
    api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())
    api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "sent"})
    api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "accepted"})

    scoped = Scoped(db, shop_a.workshop.id)
    rev = scoped.first(QuoteRevision, QuoteRevision.quote_id == uuid.UUID(quote["id"]))
    assert rev is not None
    assert rev.calc_snapshot is not None
    assert rev.locked_at is not None
    assert scoped.get(PriceListVersion, rev.price_list_version_id).locked

    recalculated = calculation.calculate(rev, calculation.load_inputs(scoped, rev), today())
    assert recalculated == rev.calc_snapshot


def test_a_sent_quote_is_edited_through_a_new_revision(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    quote = new_quote(api)
    api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())
    api.post(f"{API}/quotes/{quote['id']}/status", json={"status": "sent"})

    assert (
        api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body()).status_code == 409
    )
    second = api.post(f"{API}/quotes/{quote['id']}/revisions")
    assert second.status_code == 201
    assert second.json()["revisions"] == [1, 2]
    assert second.json()["status"] == "draft"
    changed = api.put(f"{API}/quotes/{quote['id']}/revisions/2", json=revision_body(margin_bp=2000))
    assert changed.status_code == 200
    diff = api.get(f"{API}/quotes/{quote['id']}/revisions/1/diff/2").json()
    assert {"field": "margin_bp", "from": 2500, "to": 2000} in diff


def test_payments_only_on_accepted_quotes(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    quote = new_quote(api)
    payment = {"kind": "advance", "amount_cents": 5000, "received_on": str(today())}

    assert api.post(f"{API}/quotes/{quote['id']}/payments", json=payment).status_code == 409


def test_measure_returns_the_window_size_and_its_formula(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    readings = {"widths": [830, 832, 831], "heights": [1430, 1431, 1470]}

    response = api.post(f"{API}/engine/measure", json={"readings": readings, "colour": "white"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["opening_width_mm"], body["width_mm"]) == (830, 810)  # 830 - 2 x 10
    assert (body["opening_height_mm"], body["height_mm"]) == (1430, 1410)
    assert body["formula_width"].endswith("= 810")
    assert body["warnings"] == ["height"]  # 1430 to 1470 is more than 10 mm apart


def test_preview_cuts_one_position(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    position = revision_body()["positions"][0]
    response = api.post(
        f"{API}/engine/preview", json={"profile_system_id": system_id(api), "position": position}
    )

    assert response.status_code == 200, response.text
    assert response.json()["cut_list"]["pieces"]
    assert response.json()["warnings"] == []


def test_a_missing_deduction_is_a_422_naming_it(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    admin_login(api, db, shop_a)
    reauth(api)
    sheet = {**demo.DEMO_SHEET, "deductions": {"sash_width": 1}}
    created = api.post(f"{API}/systems/{system_id(api)}/sheets", json={"constants": sheet})
    assert created.status_code == 201
    assert created.json()["version"] == 2

    position = revision_body()["positions"][0]
    response = api.post(
        f"{API}/engine/preview", json={"profile_system_id": system_id(api), "position": position}
    )
    assert response.status_code == 422
    assert response.json()["title"] == "missing catalogue value"


def test_a_bad_system_sheet_is_refused(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    admin_login(api, db, shop_a)
    reauth(api)
    bad = {**demo.DEMO_SHEET, "kerf_mm": 2.5}

    response = api.post(f"{API}/systems/{system_id(api)}/sheets", json={"constants": bad})

    assert response.status_code == 422


# --- prices -------------------------------------------------------------------------------------


def test_a_supplier_bump_makes_a_new_version(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    reauth(api)
    source = api.get(f"{API}/price-lists").json()[0]
    supplier = next(s for s in api.get(f"{API}/suppliers").json() if s["kind"] == "glass")
    bump = {"supplier_id": supplier["id"], "bp": 400, "valid_from": str(today())}

    response = api.post(f"{API}/price-lists/{source['id']}/bump", json=bump)

    assert response.status_code == 201, response.text
    new = response.json()
    assert new["id"] != source["id"]
    assert "+4% from Sample glass supplier" in new["note"]
    before = {(e["item_kind"], e["item_ref"], e["colour"]): e for e in source["entries"]}
    for entry in new["entries"]:
        old = before[(entry["item_kind"], entry["item_ref"], entry["colour"])]
        if entry["supplier_id"] == supplier["id"]:
            assert entry["amount_cents"] == old["amount_cents"] * 104 // 100
        else:
            assert entry["amount_cents"] == old["amount_cents"]
    unchanged = db.scalars(
        select(PriceEntry).where(PriceEntry.price_list_version_id == uuid.UUID(source["id"]))
    ).all()
    assert sorted(e.amount_cents for e in unchanged) == sorted(
        e["amount_cents"] for e in source["entries"]
    )


def test_changing_prices_needs_a_recent_password_check(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    for row in db.scalars(select(SessionRow)):
        row.reauth_at = datetime(2020, 1, 1, tzinfo=UTC)
    db.commit()
    source = api.get(f"{API}/price-lists").json()[0]
    supplier = api.get(f"{API}/suppliers").json()[0]
    bump = {"supplier_id": supplier["id"], "bp": 400, "valid_from": str(today())}

    assert api.post(f"{API}/price-lists/{source['id']}/bump", json=bump).status_code == 403
    assert api.put(f"{API}/settings", json=api.get(f"{API}/settings").json()).status_code == 403


# --- admin --------------------------------------------------------------------------------------


def test_the_admin_manages_users_and_sessions(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    admin_login(api, db, shop_a)
    reauth(api)
    new = {"email": "second@example.invalid", "password": "another-long-password", "role": "owner"}

    created = api.post(f"{API}/users", json=new)
    assert created.status_code == 201
    assert created.json()["totp_uri"] is None
    sessions = api.get(f"{API}/sessions").json()
    assert sessions
    owner = next(u for u in api.get(f"{API}/users").json() if u["email"] == shop_a.email)
    assert api.patch(f"{API}/users/{owner['id']}", json={"is_active": False}).status_code == 200
    assert api.delete(f"{API}/sessions/{uuid.uuid4()}").status_code == 404


def test_compare_optimizer(api: TestClient, db: Session, shop_a: SampleWorkshop) -> None:
    admin_login(api, db, shop_a)
    quote = new_quote(api)
    api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())
    body = {"quote_id": quote["id"], "revision_no": 1, "group": "frame/white", "time_limit_s": 5}

    response = api.post(f"{API}/admin/compare-optimizer", json=body)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["exact_bars"] <= result["ffd_bars"]


def test_changes_are_audited_without_personal_data(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    api.post(f"{API}/clients", json={"name": "Sample Person", "phone": "+000 00 000"})

    entries = db.scalars(select(AuditLog).where(AuditLog.workshop_id == shop_a.workshop.id)).all()
    assert any(e.entity == "client" and e.action == "create" for e in entries)
    assert all("Sample Person" not in str(e.diff) for e in entries)


# --- demo workshop ------------------------------------------------------------------------------


def test_the_demo_is_seeded_and_wiped(db: Session) -> None:
    workshop, password = demo.seed_demo(db, today())
    assert workshop.is_demo
    assert len(password) >= 12

    assert demo.wipe_demo(db) == 1
    assert db.get(Workshop, workshop.id) is None
    for model in WORKSHOP_SCOPED:
        owner = model.workshop_id  # type: ignore[attr-defined]
        left = db.scalar(select(func.count()).select_from(model).where(owner == workshop.id))
        assert left == 0, model.__tablename__


def test_new_quotes_are_numbered_per_workshop(
    api: TestClient, db: Session, shop_a: SampleWorkshop, shop_b: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    new_quote(api)
    api.cookies.clear()
    log_in(api, shop_b.email)

    assert new_quote(api)["number"] == f"{today().year}-0001"
    assert svc.next_number(Scoped(db, shop_a.workshop.id), today().year).endswith("0002")
