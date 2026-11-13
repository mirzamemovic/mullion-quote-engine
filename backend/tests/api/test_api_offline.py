"""API behaviour that needs no database: error format, validation, auth helpers, demo prices.

The database-backed tests are in ``test_api_db.py``.
"""

import uuid
from datetime import date

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from quote_engine.api import problems
from quote_engine.api.schemas import PositionIn, RevisionIn, UserIn
from quote_engine.db.models import Client, Session
from quote_engine.db.repository import NotFoundError
from quote_engine.engine.errors import InvalidInput, MissingConstant, MissingPrice
from quote_engine.engine.model import Colour, Opening, PositionSpec
from quote_engine.engine.optimizer.ffd import ffd
from quote_engine.engine.optimizer.groups import group_pieces
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import (
    Discount,
    Extra,
    ExtraKind,
    Installation,
    PricingSettings,
    QuoteJob,
    SizeThresholds,
    price_job,
)
from quote_engine.engine.rules.registry import TYPES, cut_position, merge
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Bp, Cents, Mm, Mm2
from quote_engine.export_openapi import schema_text
from quote_engine.main import create_app
from quote_engine.services import auth, demo
from quote_engine.services.quotes import QuoteError

# --- problem details ----------------------------------------------------------------------------


def app_raising(error: Exception) -> TestClient:
    app = FastAPI()
    problems.install(app)

    @app.get("/boom")
    def boom() -> None:
        raise error

    return TestClient(app)


@pytest.mark.parametrize(
    ("error", "status", "title"),
    [
        (NotFoundError(Client, uuid.uuid4()), 404, "not found"),
        (MissingConstant("sample", "deductions.sash_width"), 422, "missing catalogue value"),
        (MissingPrice("glass", "4-16-4"), 422, "missing price"),
        (InvalidInput("size must be positive"), 422, "invalid input"),
        (QuoteError("an accepted quote cannot change"), 409, "not allowed now"),
        (auth.RateLimitedError("too many"), 429, "too many attempts"),
        (auth.AuthError("wrong email or password"), 401, "login failed"),
    ],
)
def test_errors_are_problem_json(error: Exception, status: int, title: str) -> None:
    response = app_raising(error).get("/boom")

    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == title
    assert response.json()["status"] == status


def test_not_found_does_not_echo_the_id() -> None:
    row_id = uuid.uuid4()
    body = app_raising(NotFoundError(Client, row_id)).get("/boom").json()

    assert str(row_id) not in str(body)


def test_validation_errors_name_the_field_but_never_echo_the_input() -> None:
    client = TestClient(create_app())
    secret = "never-echo-me-" + "x" * 200
    response = client.post("/api/v1/auth/login", json={"email": "x", "password": secret})

    assert response.status_code == 422
    body = response.json()
    assert {e["field"] for e in body["errors"]} == {"email", "password"}
    assert "never-echo-me" not in response.text
    assert all(set(e) == {"field", "message"} for e in body["errors"])


def test_unsafe_requests_without_a_session_are_401() -> None:
    client = TestClient(create_app(), base_url="https://testserver")

    assert client.get("/api/v1/quotes").status_code == 401
    assert client.post("/api/v1/clients", json={"name": "Sample"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


# --- request schemas ----------------------------------------------------------------------------


def position(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "ref": "P1",
        "construction_type": "single_sash_tilt_turn",
        "width_mm": 800,
        "height_mm": 1400,
        "qty": 1,
        "colour": "white",
        "glass_build": "4-16-4",
        "openings": ["tilt_turn_right"],
    }
    return {**body, **changes}


@pytest.mark.parametrize(
    "changes",
    [
        {"width_mm": 299},
        {"height_mm": 3501},
        {"qty": 0},
        {"qty": 100},
        {"construction_type": "bay_window"},
        {"ref": "x" * 51},
        {"unexpected": True},
        {"readings": {"widths": [800, 801], "heights": [1400, 1400, 1400]}},
    ],
)
def test_position_limits(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PositionIn.model_validate(position(**changes))


def test_a_valid_position_passes() -> None:
    assert PositionIn.model_validate(position()).width_mm == 800


def test_revision_refs_must_be_unique_and_a_discount_is_one_kind() -> None:
    base = {"margin_bp": 2500, "valid_days": 15}
    with pytest.raises(ValidationError, match="unique"):
        RevisionIn.model_validate({**base, "positions": [position(), position()]})
    with pytest.raises(ValidationError, match="either"):
        RevisionIn.model_validate(
            {**base, "positions": [], "discount_cents": 100, "discount_bp": 100}
        )


def test_a_new_user_needs_a_long_password() -> None:
    with pytest.raises(ValidationError):
        UserIn.model_validate({"email": "a@example.invalid", "password": "short", "role": "owner"})


# --- auth helpers -------------------------------------------------------------------------------


def test_passwords_are_argon2id_and_verify() -> None:
    hashed = auth.hash_password("correct horse battery")

    assert hashed.startswith("$argon2id$")
    assert auth.verify_password(hashed, "correct horse battery")
    assert not auth.verify_password(hashed, "wrong")
    assert not auth.verify_password("not-a-hash", "anything")


def test_only_the_token_hash_is_stored() -> None:
    assert auth.hash_token("abc") != "abc"
    assert len(auth.hash_token("abc")) == 64


def test_totp_accepts_the_current_code_only() -> None:
    secret = auth.new_totp_secret()

    assert auth.totp_ok(secret, pyotp.TOTP(secret).now())
    assert not auth.totp_ok(secret, "000000") or pyotp.TOTP(secret).now() == "000000"


def test_csrf_must_match_exactly() -> None:
    row = Session(csrf_token="token-value")

    assert auth.csrf_matches(row, "token-value")
    assert not auth.csrf_matches(row, "token-valuE")
    assert not auth.csrf_matches(row, None)


# --- OpenAPI export -----------------------------------------------------------------------------


def test_openapi_file_is_current() -> None:
    from quote_engine.export_openapi import DEFAULT_TARGET

    assert DEFAULT_TARGET.read_text(encoding="utf-8") == schema_text(), (
        "frontend/openapi.json is stale: run uv run python -m quote_engine.export_openapi"
    )


# --- demo data ----------------------------------------------------------------------------------


@pytest.mark.parametrize("key", TYPES)
@pytest.mark.parametrize("colour", list(Colour))
def test_demo_prices_cover_every_type_and_colour(key: str, colour: Colour) -> None:
    """The demo price list prices a job of every type without a ``MissingPrice``."""
    today = date(2026, 1, 1)
    constants = system_constants_from_mapping(demo.DEMO_SHEET)
    openings = {
        "fixed": (Opening.FIXED,),
        "two_field_t_mullion": (Opening.TILT_TURN_LEFT, Opening.TURN_RIGHT),
        "two_sash_false_mullion": (Opening.TURN_LEFT, Opening.TILT_TURN_RIGHT),
    }.get(key, (Opening.TILT_TURN_RIGHT,))
    pos = PositionSpec("P1", key, Mm(1200), Mm(1400), 2, colour, "4-16-4", openings)
    cut_lists = {"P1": cut_position(pos, constants)}
    groups = group_pieces(merge(cut_lists.values()), [pos], constants)
    plans = {
        g.name: ffd(g.demands, g.bar_length_mm, constants.kerf_mm, constants.bar_end_trim_mm)
        for g in groups
    }
    book = PriceBook.of(
        today,
        (
            Price(
                PriceKey(
                    str(r["item_kind"]),
                    str(r["item_ref"]),
                    Colour(str(r["colour"])) if r["colour"] else None,
                ),
                Cents(int(str(r["amount_cents"]))),
                PriceUnit(str(r["unit"])),
                "Sample supplier",
                today,
            )
            for r in demo.demo_prices("p", "g", "o")
        ),
    )
    job = QuoteJob(
        positions=(pos,),
        cut_lists=cut_lists,
        groups=groups,
        plans=plans,
        kerf_mm=constants.kerf_mm,
        installation={"P1": Installation(ral=True, old_window_removal=True, wall_repair=True)},
        extras=(
            Extra(ExtraKind.SILL, "demo-sill", 1, length_mm=Mm(1200), colour=Colour.WHITE),
            Extra(ExtraKind.SHUTTER, "demo-shutter", 1, area_mm2=Mm2(1_680_000)),
            Extra(ExtraKind.SCREEN, "demo-screen", 1, area_mm2=Mm2(1_680_000)),
        ),
        transport_km=40,
        discount=Discount(Cents(0), Bp(0)),
    )
    settings = PricingSettings(
        margin_bp=Bp(2500),
        vat_registered=True,
        vat_bp=Bp(1800),
        advance_bp=Bp(5000),
        glass_min_area_mm2=Mm2(300_000),
        gasket_extra_bp=Bp(500),
        size_thresholds=SizeThresholds(
            Mm2(demo.DEMO_SMALL_MAX_MM2), Mm2(demo.DEMO_STANDARD_MAX_MM2)
        ),
    )

    assert price_job(job, book, settings).total_cents > 0


def test_demo_data_is_marked_as_sample() -> None:
    assert "sample" in demo.DEMO_NAME.lower()
    assert demo.DEMO_EMAIL.endswith(".invalid")
    assert demo.DEMO_SHEET["system_id"] == "sample-not-real"
