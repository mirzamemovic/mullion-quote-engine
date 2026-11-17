"""API tests on a real PostgreSQL: auth, CSRF, roles, step-up, tenancy, quotes, snapshots.

All data is the demo's invented sample data (SAMPLE - NOT REAL). Skipped without a database;
see ``conftest.py``.
"""

import base64
import uuid
from datetime import UTC, date, datetime, timedelta
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
    Invite,
    LoginAttempt,
    PriceEntry,
    PriceListVersion,
    Profile,
    ProfileSystem,
    Quote,
    QuoteRevision,
    SandboxRequest,
    Supplier,
    User,
    Workshop,
)
from quote_engine.db.models import Session as SessionRow
from quote_engine.db.repository import NotFoundError, Scoped
from quote_engine.engine.rules.registry import TYPES
from quote_engine.services import (
    auth,
    calculation,
    demo,
    demo_catalogue,
    price_csv,
    sandbox,
    workshops,
)
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
            {"kind": "sill", "ref": "PVC 200 mm", "qty": 1, "colour": "white", "length_mm": 800}
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


def add_user(
    db: Session, shop: SampleWorkshop, email: str, role: str, *, two_step: bool = False
) -> User:
    """Another login in ``shop``; with ``two_step`` it has a TOTP secret already."""
    user = workshops.create_user(db, shop.workshop.id, email, PASSWORD, role)
    if two_step:
        user.totp_secret = auth.new_totp_secret()
    db.commit()
    return user


def staff_login(api: TestClient, db: Session, shop: SampleWorkshop) -> User:
    user = add_user(db, shop, "staff@example.invalid", auth.ROLE_STAFF)
    log_in(api, user.email)
    return user


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


def test_two_step_login_needs_a_code(api: TestClient, db: Session, shop_a: SampleWorkshop) -> None:
    user = add_user(db, shop_a, "second@example.invalid", auth.ROLE_OWNER, two_step=True)
    me = log_in(api, user.email)

    assert me["totp_enabled"] is True
    assert me["totp_ok"] is False
    assert api.get(f"{API}/clients").status_code == 401
    secret = user.totp_secret
    assert secret is not None
    assert api.post(f"{API}/auth/totp", json={"code": pyotp.TOTP(secret).now()}).status_code == 200
    assert api.get(f"{API}/clients").status_code == 200


def test_without_two_step_login_no_code_is_asked(api: TestClient, shop_a: SampleWorkshop) -> None:
    me = log_in(api, shop_a.email)

    assert me["totp_enabled"] is False
    assert api.get(f"{API}/clients").status_code == 200


def test_staff_make_quotes_but_cannot_change_the_workshop(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    staff_login(api, db, shop_a)
    reauth(api)

    assert api.get(f"{API}/systems").status_code == 200
    assert api.get(f"{API}/price-lists").status_code == 200
    quote = new_quote(api)
    put = api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())
    assert put.status_code == 200, put.text

    system = {"key": "x", "brand": "x", "series": "x", "depth_mm": 70}
    supplier = {"name": "x", "kind": "glass"}
    settings = api.get(f"{API}/settings").json()
    client_id = quote["client_id"]
    refused = [
        api.get(f"{API}/users"),
        api.get(f"{API}/sessions"),
        api.get(f"{API}/invites"),
        api.post(f"{API}/invites", json={"role": "staff"}),
        api.post(f"{API}/systems", json=system),
        api.post(f"{API}/suppliers", json=supplier),
        api.put(f"{API}/settings", json=settings),
        api.put(f"{API}/workshop", json=api.get(f"{API}/workshop").json()),
        api.get(f"{API}/clients/{client_id}/export"),
        api.post(f"{API}/price-lists/drafts", json={}),
        api.post(f"{API}/setup/starter-prices", json={}),
    ]
    assert [r.status_code for r in refused] == [403] * len(refused)


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
    user = add_user(db, shop_a, "second@example.invalid", auth.ROLE_OWNER, two_step=True)
    secret = user.totp_secret
    assert secret is not None
    log_in(api, user.email)
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
    workshops.create_invite(db, shop.workshop.id, auth.ROLE_STAFF, None)
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


def test_a_quote_from_draft_to_accepted(api: TestClient, shop_a: SampleWorkshop) -> None:
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


def system_with_key(api: TestClient, key: str) -> str:
    return str(next(s["id"] for s in api.get(f"{API}/systems").json() if s["key"] == key))


def test_a_sheet_must_hold_every_deduction_its_types_need(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    """Publishing checks the enabled types; a type switched on later still stops a quote."""
    log_in(api, shop_a.email)
    reauth(api)
    pvc = demo_catalogue.SYSTEMS[0]
    target = system_with_key(api, pvc.key)
    fixed_only = {
        k: v for k, v in pvc.sheet()["deductions"].items() if k.startswith(("fixed", "frame"))
    }
    sheet = {**pvc.sheet(), "deductions": fixed_only}

    refused = api.post(f"{API}/systems/{target}/sheets", json={"constants": sheet})
    assert refused.status_code == 422
    assert refused.json()["title"] == "missing catalogue value"
    for key in TYPES:
        api.put(f"{API}/construction-types", json={"key": key, "enabled": key == "fixed"})
    created = api.post(f"{API}/systems/{target}/sheets", json={"constants": sheet})
    assert created.status_code == 201, created.text
    assert created.json()["version"] == 2

    api.put(f"{API}/construction-types", json={"key": "single_sash_tilt_turn", "enabled": True})
    position = revision_body()["positions"][0]
    response = api.post(
        f"{API}/engine/preview", json={"profile_system_id": target, "position": position}
    )
    assert response.status_code == 422
    assert response.json()["title"] == "missing catalogue value"


def test_a_bad_system_sheet_is_refused(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    reauth(api)
    bad = {**demo_catalogue.SYSTEMS[0].sheet(), "kerf_mm": 2.5}

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
    assert "+4% · Probni dobavljač stakla" in new["note"]
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


# --- the team: invites, roles, sessions ---------------------------------------------------------


def invite_token(api: TestClient, role: str = "staff") -> str:
    created = api.post(f"{API}/invites", json={"role": role})
    assert created.status_code == 201, created.text
    return str(created.json()["token"])


def test_an_invite_link_lets_one_person_join(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    token = invite_token(api)
    api.cookies.clear()

    info = api.post(f"{API}/join/info", json={"token": token})
    assert info.status_code == 200
    assert info.json()["role"] == "staff"
    join = {"email": "new-staff@example.invalid", "password": "a-long-enough-password"}
    joined = api.post(f"{API}/join", json={**join, "token": token})
    assert joined.status_code == 201, joined.text
    assert joined.json()["role"] == "staff"
    assert joined.json()["workshop_id"] == str(shop_a.workshop.id)
    api.headers[CSRF_HEADER] = joined.json()["csrf_token"]
    assert api.get(f"{API}/clients").status_code == 200

    api.cookies.clear()
    again = {"email": "someone-else@example.invalid", "password": "a-long-enough-password"}
    assert api.post(f"{API}/join", json={**again, "token": token}).status_code == 404
    assert api.post(f"{API}/join/info", json={"token": token}).status_code == 404


def test_an_expired_or_unknown_invite_is_refused(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    created = workshops.create_invite(
        db, shop_a.workshop.id, "staff", None, at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    db.commit()
    join = {"email": "late@example.invalid", "password": "a-long-enough-password"}

    assert api.post(f"{API}/join", json={**join, "token": created.token}).status_code == 404
    assert api.post(f"{API}/join", json={**join, "token": "x" * 43}).status_code == 404
    short = {"email": "late@example.invalid", "password": "short"}
    assert api.post(f"{API}/join", json={**short, "token": created.token}).status_code == 422


def test_only_the_invite_hash_is_stored(
    api: TestClient, db: Session, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    token = invite_token(api)

    stored = db.scalars(select(Invite.token_hash)).all()
    assert token not in stored
    assert auth.hash_token(token) in stored


def test_the_owner_manages_the_team(api: TestClient, db: Session, shop_a: SampleWorkshop) -> None:
    staff = add_user(db, shop_a, "staff@example.invalid", auth.ROLE_STAFF)
    owner = log_in(api, shop_a.email)
    reauth(api)

    users = {u["email"]: u for u in api.get(f"{API}/users").json()}
    assert set(users) == {shop_a.email, staff.email}
    promoted = api.patch(f"{API}/users/{staff.id}", json={"role": "owner"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "owner"
    off = api.patch(f"{API}/users/{staff.id}", json={"is_active": False})
    assert off.status_code == 200
    assert (
        api.patch(f"{API}/users/{owner['user_id']}", json={"is_active": False}).status_code == 409
    )
    assert api.get(f"{API}/sessions").json()
    assert api.delete(f"{API}/sessions/{uuid.uuid4()}").status_code == 404
    pending = invite_token(api)
    listed = api.get(f"{API}/invites").json()
    assert len(listed) == 1
    assert "token" not in listed[0]
    assert api.delete(f"{API}/invites/{listed[0]['id']}").status_code == 204
    assert api.post(f"{API}/join/info", json={"token": pending}).status_code == 404


def test_a_workshop_keeps_one_active_owner(db: Session, shop_a: SampleWorkshop) -> None:
    owner = db.scalars(select(User).where(User.email == shop_a.email)).one()

    with pytest.raises(workshops.SetupError, match="one active owner"):
        workshops.change_user(db, owner, role=auth.ROLE_STAFF)
    with pytest.raises(workshops.SetupError, match="one active owner"):
        workshops.change_user(db, owner, is_active=False)
    second = add_user(db, shop_a, "second@example.invalid", auth.ROLE_OWNER)
    assert workshops.change_user(db, owner, role=auth.ROLE_STAFF).role == auth.ROLE_STAFF
    assert second.role == auth.ROLE_OWNER


# --- the person's own login ---------------------------------------------------------------------


def test_changing_the_password_ends_the_other_sessions(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    other = TestClient(api.app, base_url="https://testserver")
    log_in(other, shop_a.email)
    log_in(api, shop_a.email)
    change = {"current_password": PASSWORD, "new_password": "a-brand-new-long-password"}

    assert api.post(f"{API}/me/password", json=change).status_code == 204
    assert api.get(f"{API}/auth/me").status_code == 200
    assert other.get(f"{API}/auth/me").status_code == 401
    wrong = {"current_password": "nope", "new_password": "another-long-password"}
    assert api.post(f"{API}/me/password", json=wrong).status_code == 401


def test_turning_two_step_login_on_and_off(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    setup = api.post(f"{API}/me/totp/setup")
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")

    wrong = next(
        c for c in ("000000", "111111") if not pyotp.TOTP(secret).verify(c, valid_window=1)
    )
    assert (
        api.post(f"{API}/me/totp/enable", json={"secret": secret, "code": wrong}).status_code == 401
    )
    code = pyotp.TOTP(secret).now()
    enabled = api.post(f"{API}/me/totp/enable", json={"secret": secret, "code": code})
    assert enabled.status_code == 200
    assert enabled.json()["totp_enabled"] is True

    api.cookies.clear()
    assert log_in(api, shop_a.email)["totp_ok"] is False
    assert api.post(f"{API}/auth/totp", json={"code": pyotp.TOTP(secret).now()}).status_code == 200
    assert api.post(f"{API}/me/totp/disable").json()["totp_enabled"] is False


# --- the workshop profile and currency ----------------------------------------------------------


def test_the_currency_is_locked_after_the_first_quote(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    profile = api.get(f"{API}/workshop").json()
    assert profile["currency"] == "EUR"

    changed = api.put(f"{API}/workshop", json={**profile, "currency": "BAM", "phone": "000"})
    assert changed.status_code == 200
    assert changed.json()["currency"] == "BAM"
    assert api.get(f"{API}/auth/me").json()["currency"] == "BAM"
    new_quote(api)
    locked = api.put(f"{API}/workshop", json={**profile, "currency": "EUR"})
    assert locked.status_code == 409
    assert api.put(f"{API}/workshop", json={**profile, "currency": "USD"}).status_code == 422


# --- "Try it" sandboxes -------------------------------------------------------------------------


def test_a_sandbox_opens_logged_in_with_sample_data(api: TestClient) -> None:
    opened = api.post(f"{API}/sandbox", json={"language": "bs"})

    assert opened.status_code == 201, opened.text
    me = opened.json()
    assert me["is_demo"] is True
    assert me["sandbox_expires_at"] is not None
    assert me["language"] == "bs"
    assert me["role"] == "owner"
    api.headers[CSRF_HEADER] = me["csrf_token"]
    assert len(api.get(f"{API}/systems").json()) == len(demo_catalogue.SYSTEMS)
    assert api.post(f"{API}/invites", json={"role": "staff"}).status_code == 409
    assert api.post(f"{API}/sandbox", data="language=en").status_code == 422


def test_sandboxes_are_limited_per_address_and_purged(db: Session) -> None:
    at = datetime(2026, 11, 17, 12, tzinfo=UTC)
    for _ in range(sandbox.MAX_PER_ADDRESS_PER_DAY):
        sandbox.create_sandbox(db, "198.51.100.7", "test", at)
    with pytest.raises(sandbox.SandboxLimitError):
        sandbox.create_sandbox(db, "198.51.100.7", "test", at)
    sandbox.create_sandbox(db, "198.51.100.8", "test", at)

    later = at + timedelta(hours=sandbox.SANDBOX_HOURS, minutes=1)
    assert sandbox.purge_expired(db, later) == sandbox.MAX_PER_ADDRESS_PER_DAY + 1
    assert db.scalar(select(func.count()).select_from(Workshop).where(Workshop.is_demo)) == 0
    assert db.scalar(select(func.count()).select_from(SandboxRequest)) == 0
    sandbox.create_sandbox(db, "198.51.100.7", "test", later)


def test_a_real_workshop_is_never_purged(db: Session, shop_a: SampleWorkshop) -> None:
    far = datetime(2100, 1, 1, tzinfo=UTC)

    assert sandbox.purge_expired(db, far) == 0
    assert db.get(Workshop, shop_a.workshop.id) is not None


# --- admin tools --------------------------------------------------------------------------------


def test_compare_optimizer(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
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


# --- setup: checklist, starter prices, drafts, CSV, sheet editor --------------------------------


def test_the_sample_workshop_is_ready_and_counts_its_estimates(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    report = api.get(f"{API}/setup/status").json()

    assert report["ready"] is True
    assert report["percent"] == 100
    assert report["prices_missing"] == []
    assert report["estimates"] > 0
    assert all(s["done"] for s in report["systems"])


def test_a_quote_warns_when_it_uses_estimated_prices(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    quote = new_quote(api)
    api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())

    calc = api.post(f"{API}/quotes/{quote['id']}/revisions/1/calculate").json()
    assert any(w["code"] == "prices_estimated" for w in calc["warnings"])


def new_owner(db: Session, currency: str = "EUR") -> str:
    workshop = workshops.create_workshop(
        db, "Sample new workshop", 1_000_000, 2_500_000, currency=currency
    )
    user = workshops.create_user(
        db, workshop.id, f"owner-{currency.lower()}@example.invalid", PASSWORD, auth.ROLE_OWNER
    )
    db.commit()
    return user.email


def test_a_new_workshop_sees_what_it_lacks_and_starter_prices_fill_the_prices(
    api: TestClient, db: Session
) -> None:
    log_in(api, new_owner(db))
    empty = api.get(f"{API}/setup/status").json()
    assert empty["ready"] is False
    assert empty["systems"] == []
    assert empty["price_list_id"] is None

    started = api.post(f"{API}/setup/starter-prices", json={"with_systems": True})
    assert started.status_code == 201, started.text
    draft = started.json()
    assert draft["status"] == "draft"
    assert draft["entries"]
    assert all(e["is_estimate"] for e in draft["entries"])

    report = api.get(f"{API}/setup/status", params={"price_list_id": draft["id"]}).json()
    assert len(report["systems"]) == len(demo_catalogue.SYSTEMS)
    for system in report["systems"]:
        assert system["sheet"] == "missing"
        assert "deductions.sash_width" in system["missing"]
    assert report["prices_missing"] == []  # the starter list holds every white price needed
    assert report["ready"] is False  # the sheets must still come from the catalogues


def test_starter_prices_only_fit_a_euro_workshop(api: TestClient, db: Session) -> None:
    log_in(api, new_owner(db, "BAM"))

    assert api.post(f"{API}/setup/starter-prices", json={}).status_code == 409


def strip_ids(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in e.items() if k != "id"} for e in entries]


def test_a_draft_price_list_is_never_used_until_it_is_published(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    published = api.get(f"{API}/price-lists").json()[0]
    copied = api.post(
        f"{API}/price-lists/drafts", json={"copy_from": published["id"], "note": "next month"}
    )
    assert copied.status_code == 201, copied.text
    draft = copied.json()
    assert draft["status"] == "draft"
    assert len(draft["entries"]) == len(published["entries"])

    cheaper = [{**e, "amount_cents": 1} for e in strip_ids(draft["entries"])]
    put = api.put(f"{API}/price-lists/{draft['id']}/entries", json={"entries": cheaper})
    assert put.status_code == 200, put.text
    quote = new_quote(api)
    api.put(f"{API}/quotes/{quote['id']}/revisions/1", json=revision_body())
    calc = api.post(f"{API}/quotes/{quote['id']}/revisions/1/calculate").json()
    assert calc["versions"]["price_list"] == published["id"]

    publish = {"valid_from": str(today())}
    assert api.post(f"{API}/price-lists/{draft['id']}/publish", json=publish).status_code == 200
    again = api.put(f"{API}/price-lists/{draft['id']}/entries", json={"entries": []})
    assert again.status_code == 409
    assert api.delete(f"{API}/price-lists/{draft['id']}").status_code == 409
    empty = api.post(f"{API}/price-lists/drafts", json={}).json()
    assert api.post(f"{API}/price-lists/{empty['id']}/publish", json=publish).status_code == 409
    assert api.delete(f"{API}/price-lists/{empty['id']}").status_code == 204


def test_a_price_list_goes_out_and_back_in_as_csv(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    published = api.get(f"{API}/price-lists").json()[0]
    exported = api.get(f"{API}/price-lists/{published['id']}/csv")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    draft = api.post(f"{API}/price-lists/drafts", json={}).json()

    data = base64.b64encode(exported.content).decode()
    imported = api.post(f"{API}/price-lists/{draft['id']}/csv", json={"content_base64": data})
    assert imported.status_code == 200, imported.text

    def keys(entries: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
        fields = ("item_kind", "item_ref", "colour", "unit", "amount_cents", "is_estimate")
        return sorted(tuple(e[f] for f in fields) for e in entries)

    assert keys(imported.json()["entries"]) == keys(published["entries"])

    bad = base64.b64encode(b"kind,ref,unit,amount,supplier\nglass,4-16-4,m2,abc,Nobody\n")
    body = {"content_base64": bad.decode()}
    refused = api.post(f"{API}/price-lists/{draft['id']}/csv", json=body)
    assert refused.status_code == 422
    assert {p["column"] for p in refused.json()["problems"]} == {"amount", "supplier"}
    unchanged = api.get(f"{API}/price-lists/{draft['id']}").json()["entries"]
    assert len(unchanged) == len(published["entries"])


def test_the_template_lists_every_missing_price(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    draft = api.post(f"{API}/price-lists/drafts", json={}).json()

    template = api.get(f"{API}/setup/price-template.csv", params={"price_list_id": draft["id"]})
    lines = template.text.lstrip("﻿").splitlines()
    assert lines[0] == ",".join(price_csv.COLUMNS)
    assert any(line.startswith("labour,") for line in lines)
    assert any(line.startswith("glass,4-16-4") for line in lines)


def test_a_sheet_is_drafted_checked_and_published(api: TestClient, shop_a: SampleWorkshop) -> None:
    log_in(api, shop_a.email)
    system = api.get(f"{API}/systems").json()[0]
    full = next(s for s in demo_catalogue.SYSTEMS if s.key == system["key"]).sheet()
    partial = {**full, "deductions": {"sash_width": 44}}
    drafts = f"{API}/systems/{system['id']}/sheets/draft"

    saved = api.post(drafts, json={"constants": partial, "source_pages": {"sash_width": "p. 12"}})
    assert saved.status_code == 201, saved.text
    assert saved.json()["status"] == "draft"
    assert (
        api.post(drafts, json={"constants": partial}).json()["version"] == saved.json()["version"]
    )
    preview = {"construction_type": "single_sash_tilt_turn", "width_mm": 800, "height_mm": 1400}
    missing = api.post(f"{API}/engine/cut-preview", json={**preview, "constants": partial})
    assert missing.status_code == 422
    assert missing.json()["constant"] == "deductions.sash_height"
    publish = f"{API}/systems/{system['id']}/sheets/{saved.json()['version']}/publish"
    assert api.post(publish).status_code == 422

    api.post(drafts, json={"constants": full})
    cut = api.post(f"{API}/engine/cut-preview", json={**preview, "constants": full})
    assert cut.status_code == 200
    assert cut.json()["cut_list"]["pieces"]
    assert api.post(publish).json()["status"] == "published"
    assert api.post(publish).status_code == 409
    assert api.post(drafts, json={"constants": {"colour_of_the_sky": 1}}).status_code == 422


def test_the_sheet_editor_is_told_which_values_to_ask_for(
    api: TestClient, shop_a: SampleWorkshop
) -> None:
    log_in(api, shop_a.email)
    pvc = system_with_key(api, demo_catalogue.SYSTEMS[0].key)
    alu = next(s for s in api.get(f"{API}/systems").json() if s["material"] == "aluminium")

    fields = api.get(f"{API}/systems/{pvc}/sheet-fields").json()
    assert "kerf_mm" in fields["lengths"]
    assert "frame" in fields["bar_roles"]
    assert {"sash_width", "frame_steel", "fixed_glass"} <= set(fields["deductions"])
    unreinforced = api.get(f"{API}/systems/{alu['id']}/sheet-fields?reinforced=false").json()
    assert not [d for d in unreinforced["deductions"] if "steel" in d]
