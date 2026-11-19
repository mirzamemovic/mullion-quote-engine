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
from quote_engine.api.schemas import InviteAcceptIn, PositionIn, RevisionIn, WorkshopIO
from quote_engine.db.models import Client, Session
from quote_engine.db.repository import NotFoundError
from quote_engine.engine.errors import InvalidInput, MissingConstant, MissingPrice
from quote_engine.engine.measuring import Measurement, measure_opening
from quote_engine.engine.model import Colour
from quote_engine.engine.rules.registry import TYPES
from quote_engine.engine.units import Mm
from quote_engine.export_openapi import schema_text
from quote_engine.main import create_app
from quote_engine.services import auth, demo, demo_catalogue, sandbox, workshops
from quote_engine.services.quotes import QuoteError, stored_size

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
        (workshops.SetupError("a workshop needs an owner"), 409, "not allowed now"),
        (sandbox.SandboxLimitError("too many"), 429, "too many sandboxes"),
        (sandbox.SandboxFullError("full"), 503, "no sandbox now"),
    ],
)
def test_errors_are_problem_json(error: Exception, status: int, title: str) -> None:
    response = app_raising(error).get("/boom")

    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == title
    assert response.json()["status"] == status


def test_an_unexpected_error_is_problem_json_and_says_nothing_about_its_cause() -> None:
    cause = "sample internal detail: column quotes.number"
    client = TestClient(app_raising(RuntimeError(cause)).app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "unexpected error"
    assert "column" not in response.text


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


def _measured_800_by_1400() -> Measurement:
    """Readings that give an 800 x 1400 white window: 820 - 2 x 10 and 1420 - 2 x 10."""
    return measure_opening(
        [Mm(820), Mm(822), Mm(821)], [Mm(1420), Mm(1421), Mm(1420)], Colour.WHITE
    )


def test_a_size_that_agrees_with_the_readings_is_kept() -> None:
    assert stored_size("P1", (800, 1400), _measured_800_by_1400()) == (800, 1400)


@pytest.mark.xfail(reason="waits for Mirza: stored_size in services/quotes.py", strict=False)
@pytest.mark.parametrize("sent", [(790, 1400), (800, 1410), (1200, 1200)])
def test_a_size_the_readings_contradict_is_never_kept(sent: tuple[int, int]) -> None:
    outcome: object
    try:
        outcome = stored_size("P7", sent, _measured_800_by_1400())
    except InvalidInput as error:
        outcome = str(error)
    # Either way is right: keep the measured size, or refuse and name the window.
    assert outcome == (800, 1400) or (isinstance(outcome, str) and "P7" in outcome)


def test_revision_refs_must_be_unique_and_a_discount_is_one_kind() -> None:
    base = {"margin_bp": 2500, "valid_days": 15}
    with pytest.raises(ValidationError, match="unique"):
        RevisionIn.model_validate({**base, "positions": [position(), position()]})
    with pytest.raises(ValidationError, match="either"):
        RevisionIn.model_validate(
            {**base, "positions": [], "discount_cents": 100, "discount_bp": 100}
        )


def test_a_new_person_needs_a_long_password_and_a_real_email() -> None:
    token = "t" * 43
    with pytest.raises(ValidationError):
        InviteAcceptIn.model_validate(
            {"token": token, "email": "a@example.invalid", "password": "short"}
        )
    with pytest.raises(ValidationError):
        InviteAcceptIn.model_validate(
            {"token": token, "email": "not-an-email", "password": "x" * 12}
        )
    with pytest.raises(ValidationError):
        InviteAcceptIn.model_validate(
            {"token": "a/b", "email": "a@example.invalid", "password": "x" * 12}
        )
    ok = {"token": token, "email": "a@example.invalid", "password": "x" * 12}
    assert InviteAcceptIn.model_validate(ok)


def test_invite_links_keep_the_token_out_of_the_url_path() -> None:
    link = workshops.invite_link("https://mullion.example/", "abc_DEF-123")

    assert link == "https://mullion.example/join#abc_DEF-123"


def test_a_workshop_picks_a_supported_currency_and_language() -> None:
    base = {"name": "Sample workshop"}
    assert WorkshopIO.model_validate({**base, "currency": "BAM"}).currency == "BAM"
    for bad in ({"currency": "USD"}, {"language": "fr"}, {"unexpected": 1}):
        with pytest.raises(ValidationError):
            WorkshopIO.model_validate({**base, **bad})
    assert set(workshops.CURRENCIES) == {"EUR", "BAM", "RSD", "ALL", "MKD"}


def test_invites_never_come_from_a_sandbox_and_roles_are_checked() -> None:
    """The service refuses before touching the database when the role is wrong."""
    with pytest.raises(workshops.SetupError, match="role"):
        workshops.create_invite(None, uuid.uuid4(), "admin", None)  # type: ignore[arg-type]


def test_a_sandbox_request_must_be_json() -> None:
    client = TestClient(create_app(), base_url="https://testserver")

    assert client.post("/api/v1/sandbox", data={"language": "en"}).status_code == 422


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


@pytest.mark.parametrize("system", demo_catalogue.SYSTEMS, ids=lambda s: s.key)
@pytest.mark.parametrize("key", TYPES)
@pytest.mark.parametrize("colour", list(Colour))
def test_the_demo_catalogue_prices_every_system_type_and_colour(
    system: demo_catalogue.DemoSystem, key: str, colour: Colour
) -> None:
    """Every demo system prices every type in every colour with no missing price or value."""
    openings = {
        "fixed": ["fixed"],
        "two_field_t_mullion": ["tilt_turn_left", "turn_right"],
        "two_sash_false_mullion": ["turn_left", "tilt_turn_right"],
    }.get(key, ["tilt_turn_right"])
    position = {
        "ref": "P1",
        "construction_type": key,
        "width_mm": 1200,
        "height_mm": 1400 if key != "balcony_door_tilt_turn" else 2200,
        "qty": 2,
        "colour": colour.value,
        "glass_build": "4-16-4",
        "openings": openings,
        "readings": None,
        "installation": {
            "install": True,
            "ral": True,
            "old_window_removal": True,
            "wall_repair": True,
        },
    }
    extras = [
        {"kind": "sill", "ref": "PVC 200 mm", "qty": 1, "colour": "white", "length_mm": 1200},
        {"kind": "shutter", "ref": "PVC", "qty": 1, "area_mm2": 1_680_000},
        {"kind": "screen", "ref": "rolo", "qty": 1, "area_mm2": 1_680_000},
    ]

    result = demo_catalogue.calculate(
        system.key,
        {"positions": [position], "extras": extras, "transport_km": 40},
        date(2026, 11, 14),
    )

    assert result["price"]["total_cents"] > 0
    if system.material.value == "aluminium":
        assert result["cut_lists"]["P1"]["steel"] == []


def test_aluminium_costs_more_than_pvc_and_premium_more_than_budget() -> None:
    """A sanity check against the market research: thermal-break aluminium is about twice PVC."""
    position = {
        "ref": "P1",
        "construction_type": "two_field_t_mullion",
        "width_mm": 1400,
        "height_mm": 1400,
        "qty": 4,
        "colour": "white",
        "glass_build": "4-16-4",
        "openings": ["turn_left", "tilt_turn_right"],
        "readings": None,
        "installation": {
            "install": True,
            "ral": False,
            "old_window_removal": False,
            "wall_repair": False,
        },
    }
    totals = {
        s.key: demo_catalogue.calculate(s.key, {"positions": [position]}, date(2026, 11, 14))[
            "price"
        ]["total_cents"]
        for s in demo_catalogue.SYSTEMS
    }

    assert totals["rehau-euro-design-70"] < totals["salamander-greenevolution-76"]
    assert totals["salamander-greenevolution-76"] < totals["rehau-synego-80"]
    assert totals["alumil-m9400"] < totals["alumil-smartia-s67"] < totals["alumil-smartia-m11000"]
    assert 1.6 < totals["alumil-smartia-s67"] / totals["rehau-euro-design-70"] < 2.4


def test_demo_data_is_marked_as_sample() -> None:
    assert "invented" in demo.DEMO_NAME
    assert demo.DEMO_EMAIL.endswith(".invalid")
    assert "not a workshop's own prices" in demo_catalogue.PRICE_NOTE


# --- development demo endpoints -----------------------------------------------------------------


def dev_app(monkeypatch: pytest.MonkeyPatch, environment: str, flag: str | None) -> TestClient:
    from quote_engine.settings import get_settings

    monkeypatch.setenv("QUOTE_ENGINE_ENVIRONMENT", environment)
    if environment == "production":
        monkeypatch.setenv("QUOTE_ENGINE_DATABASE_URL", "postgresql+psycopg://x:y@localhost/z")
    if flag is None:
        monkeypatch.delenv("QUOTE_ENGINE_DEV_DEMO", raising=False)
    else:
        monkeypatch.setenv("QUOTE_ENGINE_DEV_DEMO", flag)
    get_settings.cache_clear()
    try:
        return TestClient(create_app())
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    ("environment", "flag"), [("development", None), ("development", "0"), ("production", "1")]
)
def test_dev_endpoints_are_off_unless_asked_and_never_in_production(
    monkeypatch: pytest.MonkeyPatch, environment: str, flag: str | None
) -> None:
    client = dev_app(monkeypatch, environment, flag)

    assert client.get("/api/v1/dev/catalogue").status_code == 404


def test_dev_endpoints_price_with_the_real_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    client = dev_app(monkeypatch, "development", "1")
    systems = client.get("/api/v1/dev/catalogue").json()["systems"]
    body = {
        "system_key": systems[0]["key"],
        "revision": {"margin_bp": 2500, "valid_days": 15, "positions": [position()]},
    }

    one = client.post("/api/v1/dev/calculate", json=body).json()["price"]["total_cents"]
    body["revision"]["positions"] = [position(qty=3)]
    three = client.post("/api/v1/dev/calculate", json=body).json()["price"]["total_cents"]

    assert {s["material"] for s in systems} == {"pvc", "aluminium"}
    assert 0 < one < three  # the price follows what was entered
    measured = client.post(
        "/api/v1/dev/measure",
        json={
            "readings": {"widths": [830, 832, 831], "heights": [1430, 1431, 1430]},
            "colour": "white",
        },
    ).json()
    assert (measured["width_mm"], measured["height_mm"]) == (810, 1410)
