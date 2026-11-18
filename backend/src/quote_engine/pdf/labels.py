"""Words and number formats for the PDFs, in English and Bosnian.

This mirrors the frontend (``lib/format.ts`` and ``lib/labels.ts``) so a quote reads the same on
paper as on screen:
- money from whole minor units, with integer maths only;
- dates the way the trade writes them;
- the engine's English piece names in the workshop's words.

Unknown words pass through unchanged, so a new engine label still prints, just untranslated.
"""

import re
from datetime import date

LANGUAGES = ("en", "bs")
MINUS = chr(0x2212)  # minus sign
NBSP = chr(0xA0)  # no-break space
TIMES = chr(0xD7)  # multiplication sign
SYMBOLS = {"EUR": "€", "BAM": "KM", "RSD": "RSD", "ALL": "ALL", "MKD": "MKD"}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def language(code: str | None) -> str:
    """One of ``LANGUAGES``; anything else reads as English."""
    return "bs" if code == "bs" else "en"


def money(cents: int, lang: str, currency: str) -> str:
    """123456 -> "€1,234.56" (English euros), "1.234,56 €" (Bosnian), "1,234.56 KM" (others).

    The amount and its symbol are joined by a no-break space so a table cell never splits them.
    """
    sign = MINUS if cents < 0 else ""
    whole, rest = divmod(abs(cents), 100)
    english = lang == "en"
    groups = f"{whole:,}" if english else f"{whole:,}".replace(",", ".")
    amount = f"{groups}{'.' if english else ','}{rest:02d}"
    if currency == "EUR" and english:
        return f"{sign}€{amount}"
    return f"{sign}{amount}{NBSP}{SYMBOLS.get(currency, currency)}"


def percent(bp: int, lang: str) -> str:
    """Basis points without floats: 2500 -> "25 %", 1850 -> "18.5 %" or "18,5 %"."""
    whole, rest = divmod(bp, 100)
    decimals = ""
    if rest:
        decimals = ("." if lang == "en" else ",") + f"{rest:02d}".removesuffix("0")
    return f"{whole}{decimals}{NBSP}%"


def day(value: date, lang: str) -> str:
    """28 Nov 2026 (English) or 28.11.2026. (Bosnian)."""
    if lang == "en":
        return f"{value.day} {MONTHS[value.month - 1]} {value.year}"
    return f"{value.day}.{value.month}.{value.year}."


def size(width_mm: int, height_mm: int) -> str:
    """1368 x 1171, with a multiplication sign and no-break spaces."""
    return f"{width_mm}{NBSP}{TIMES}{NBSP}{height_mm}"


UNITS = {
    "en": {"m2": "m²", "piece": "pc"},
    "bs": {
        "bar": "šipka",
        "m": "m",
        "m2": "m²",
        "set": "komplet",
        "piece": "kom",
        "job": "posao",
        "km": "km",
    },
}


def unit(name: str, lang: str) -> str:
    return UNITS[language(lang)].get(name, name)


_PHRASES_BS = (
    (re.compile(r"\bfalse mullion\b"), "štulp"),
    (re.compile(r"\bdoor sash\b"), "krilo vrata"),
    (re.compile(r"\bprice risk\b"), "rizik cijene"),
    (re.compile(r"\bold window removal\b"), "skidanje starog prozora"),
    (re.compile(r"\bwall repair\b"), "popravka zida"),
)

_WORDS = {
    "en": {
        "foil_one_side": "foil outside",
        "foil_both_sides": "foil both sides",
        "tilt_turn_left": "tilt-turn left",
        "tilt_turn_right": "tilt-turn right",
        "turn_left": "turn left",
        "turn_right": "turn right",
    },
    "bs": {
        "profile": "profil",
        "labour": "rad",
        "transport": "prevoz",
        "flat": "paušal",
        "window": "prozor",
        "frame": "štok",
        "sash": "krilo",
        "mullion": "stub",
        "bead": "lajsna",
        "steel": "armatura",
        "threshold": "prag",
        "top": "gore",
        "bottom": "dolje",
        "left": "lijevo",
        "right": "desno",
        "horizontal": "horizontalno",
        "vertical": "vertikalno",
        "bars": "šipke",
        "gasket": "dihtung",
        "hardware": "okov",
        "glass": "staklo",
        "consumables": "potrošni materijal",
        "installation": "ugradnja",
        "small": "mali",
        "standard": "standardni",
        "large": "veliki",
        "ral": "RAL",
        "sill": "klupčica",
        "shutter": "roletna",
        "screen": "komarnik",
        "white": "bijela",
        "foil_one_side": "folija spolja",
        "foil_both_sides": "folija obostrano",
        "fixed": "fiksno",
        "tilt_turn_left": "okretno-nagibno lijevo",
        "tilt_turn_right": "okretno-nagibno desno",
        "turn_left": "okretno lijevo",
        "turn_right": "okretno desno",
    },
}


def workshop_label(label: str, lang: str) -> str:
    """An engine name ("left sash bead horizontal", "frame/white") in the workshop's words."""
    lang = language(lang)
    text = label.replace("/", " / ")
    if lang == "bs":
        for pattern, replacement in _PHRASES_BS:
            text = pattern.sub(replacement, text)
    words = _WORDS[lang]
    return " ".join(words.get(word, word) for word in text.split(" ")).replace(" / ", " · ")


def cut_label(key: str, position_ref: str, lang: str) -> str:
    """A cut key "<position ref> <piece label>" as "Kitchen · frame top"."""
    if key.startswith(f"{position_ref} "):
        return f"{position_ref} · {workshop_label(key[len(position_ref) + 1 :], lang)}"
    return workshop_label(key, lang)


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "quote": "Quote",
        "version": "version {n}",
        "date": "Date",
        "valid_until": "Valid until",
        "client": "Client",
        "phone": "Phone",
        "email": "Email",
        "vat_number": "VAT no.",
        "position": "Position",
        "size": "Size (mm)",
        "description": "Description",
        "qty": "Qty",
        "unit_price": "Unit price",
        "line_total": "Amount",
        "windows": "Windows and doors",
        "extras": "Extras",
        "transport": "Transport",
        "subtotal": "Subtotal",
        "discount": "Discount",
        "net": "Before VAT",
        "vat": "VAT {rate}",
        "total": "Total",
        "payment": "Payment",
        "advance": "Advance on order",
        "balance": "Balance",
        "accepted_by": "Accepted by the client",
        "for_workshop": "For the workshop",
        "signature": "Name, date and signature",
        "sample": "Sample workshop with invented data. This is not a real quote.",
        "page": "Page",
        "of": "of",
        "glass": "Glass",
        "installation": "installation",
        "ral": "RAL installation",
        "old_window_removal": "old window removed",
        "wall_repair": "wall repair",
        "no_installation": "supply only",
        "workshop_sheet": "Workshop sheet",
        "system": "Profile system",
        "cutting_plan": "Cutting plan",
        "bars": "{count} {x} {length} mm",
        "offcut": "offcut",
        "keep": "keep",
        "waste": "Waste {rate}",
        "cut_list": "Cut list",
        "piece": "Piece",
        "length": "mm",
        "angles": "Angles",
        "formula": "Formula",
        "glass_order": "Glass order",
        "build": "Build",
        "positions": "Positions",
        "hardware": "Hardware",
        "opening": "Opening",
        "to_buy": "To buy",
        "item": "Item",
        "supplier": "Supplier",
        "steel": "Steel",
        "internal": "For the workshop only. Prices are not shown.",
    },
    "bs": {
        "quote": "Ponuda",
        "version": "verzija {n}",
        "date": "Datum",
        "valid_until": "Važi do",
        "client": "Klijent",
        "phone": "Telefon",
        "email": "E-mail",
        "vat_number": "PDV broj",
        "position": "Pozicija",
        "size": "Mjere (mm)",
        "description": "Opis",
        "qty": "Kol.",
        "unit_price": "Jed. cijena",
        "line_total": "Iznos",
        "windows": "Prozori i vrata",
        "extras": "Dodaci",
        "transport": "Prevoz",
        "subtotal": "Zbir",
        "discount": "Popust",
        "net": "Bez PDV-a",
        "vat": "PDV {rate}",
        "total": "Ukupno",
        "payment": "Plaćanje",
        "advance": "Avans pri narudžbi",
        "balance": "Ostatak",
        "accepted_by": "Prihvata klijent",
        "for_workshop": "Za radionicu",
        "signature": "Ime, datum i potpis",
        "sample": "Primjer radionice s izmišljenim podacima. Ovo nije prava ponuda.",
        "page": "Strana",
        "of": "od",
        "glass": "Staklo",
        "installation": "ugradnja",
        "ral": "RAL ugradnja",
        "old_window_removal": "skidanje starog prozora",
        "wall_repair": "popravka zida",
        "no_installation": "bez ugradnje",
        "workshop_sheet": "Radni nalog",
        "system": "Profilni sistem",
        "cutting_plan": "Plan sječenja",
        "bars": "{count} {x} {length} mm",
        "offcut": "ostatak",
        "keep": "čuvaj",
        "waste": "Otpad {rate}",
        "cut_list": "Krojna lista",
        "piece": "Komad",
        "length": "mm",
        "angles": "Uglovi",
        "formula": "Formula",
        "glass_order": "Narudžba stakla",
        "build": "Sastav",
        "positions": "Pozicije",
        "hardware": "Okov",
        "opening": "Otvaranje",
        "to_buy": "Za nabavku",
        "item": "Artikal",
        "supplier": "Dobavljač",
        "steel": "Armatura",
        "internal": "Samo za radionicu. Cijene nisu prikazane.",
    },
}

TYPES = {
    "en": {
        "single_sash_tilt_turn": "Single sash",
        "two_field_t_mullion": "Two fields, fixed mullion",
        "two_sash_false_mullion": "Two sashes, false mullion",
        "fixed": "Fixed",
        "balcony_door_tilt_turn": "Balcony door",
    },
    "bs": {
        "single_sash_tilt_turn": "Jedno krilo",
        "two_field_t_mullion": "Dva polja sa stubom",
        "two_sash_false_mullion": "Dva krila sa štulpom",
        "fixed": "Fiksni",
        "balcony_door_tilt_turn": "Balkonska vrata",
    },
}

OPENINGS = {
    "en": {
        "fixed": "fixed",
        "tilt_turn_left": "tilt and turn, left",
        "tilt_turn_right": "tilt and turn, right",
        "turn_left": "turn, left",
        "turn_right": "turn, right",
    },
    "bs": {
        "fixed": "fiksno",
        "tilt_turn_left": "okretno-nagibno, lijevo",
        "tilt_turn_right": "okretno-nagibno, desno",
        "turn_left": "okretno, lijevo",
        "turn_right": "okretno, desno",
    },
}

COLOURS = {
    "en": {"white": "white", "foil_one_side": "foil outside", "foil_both_sides": "foil both sides"},
    "bs": {
        "white": "bijela",
        "foil_one_side": "folija spolja",
        "foil_both_sides": "folija obostrano",
    },
}

EXTRA_KINDS = {
    "en": {"sill": "Sill", "shutter": "Roller shutter", "screen": "Insect screen", "other": ""},
    "bs": {"sill": "Klupčica", "shutter": "Roletna", "screen": "Komarnik", "other": ""},
}


def text(lang: str, key: str, **values: object) -> str:
    """A sentence from ``TEXT``, with ``{name}`` placeholders filled in."""
    return TEXT[language(lang)][key].format(**{"x": TIMES, **values})


def type_name(construction_type: str, lang: str) -> str:
    return TYPES[language(lang)].get(construction_type, construction_type)


def opening_name(opening: str, lang: str) -> str:
    return OPENINGS[language(lang)].get(opening, opening)


def colour_name(colour: str, lang: str) -> str:
    return COLOURS[language(lang)].get(colour, colour)


def extra_kind(kind: str, lang: str) -> str:
    return EXTRA_KINDS[language(lang)].get(kind, kind)
