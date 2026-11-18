/**
 * The engine names pieces and price lines in plain English words ("left sash bead horizontal",
 * "frame/white bars", "hardware tilt_turn_left"). This puts them into the workshop's words.
 * Unknown words pass through unchanged, so a new engine label still shows, just untranslated.
 */
const PHRASES_BS: [RegExp, string][] = [
  [/\bfalse mullion\b/g, "štulp"],
  [/\bdoor sash\b/g, "krilo vrata"],
  [/\bprice risk\b/g, "rizik cijene"],
  [/\bused length\b/g, "utrošena dužina"],
  [/\bold window removal\b/g, "skidanje starog prozora"],
  [/\bwall repair\b/g, "popravka zida"],
];

const UNITS_BS: Record<string, string> = {
  bar: "šipka",
  m: "m",
  m2: "m²",
  set: "komplet",
  piece: "kom",
  job: "posao",
  km: "km",
};
const UNITS_EN: Record<string, string> = { m2: "m²", piece: "pc" };

export function unitLabel(unit: string, language: string): string {
  return (language.startsWith("en") ? UNITS_EN : UNITS_BS)[unit] ?? unit;
}

const WORDS_BS: Record<string, string> = {
  profile: "profil",
  labour: "rad",
  transport: "prevoz",
  flat: "paušal",
  window: "prozor",
  frame: "štok",
  sash: "krilo",
  mullion: "stub",
  bead: "lajsna",
  steel: "armatura",
  threshold: "prag",
  top: "gore",
  bottom: "dolje",
  left: "lijevo",
  right: "desno",
  horizontal: "horizontalno",
  vertical: "vertikalno",
  bars: "šipke",
  gasket: "dihtung",
  hardware: "okov",
  glass: "staklo",
  consumables: "potrošni materijal",
  installation: "ugradnja",
  small: "mali",
  standard: "standardni",
  large: "veliki",
  ral: "RAL",
  sill: "klupčica",
  shutter: "roletna",
  screen: "komarnik",
  white: "bijela",
  foil_one_side: "folija spolja",
  foil_both_sides: "folija obostrano",
  fixed: "fiksno",
  tilt_turn_left: "okretno-nagibno lijevo",
  tilt_turn_right: "okretno-nagibno desno",
  turn_left: "okretno lijevo",
  turn_right: "okretno desno",
};

const WORDS_EN: Record<string, string> = {
  foil_one_side: "foil outside",
  foil_both_sides: "foil both sides",
  tilt_turn_left: "tilt-turn left",
  tilt_turn_right: "tilt-turn right",
  turn_left: "turn left",
  turn_right: "turn right",
};

export function workshopLabel(label: string, language: string): string {
  const english = language.startsWith("en");
  let text = label.replace(/\//g, " / ");
  if (!english) {
    for (const [pattern, replacement] of PHRASES_BS) text = text.replace(pattern, replacement);
  }
  const words = english ? WORDS_EN : WORDS_BS;
  return text
    .split(" ")
    .map((word) => words[word] ?? word)
    .join(" ")
    .replace(/ \/ /g, " · ");
}

/** A cut key "<position ref> <piece label>" as "Kuhinja · štok lijevo". */
export function cutLabel(key: string, positionRef: string | undefined, language: string): string {
  if (positionRef && key.startsWith(`${positionRef} `)) {
    return `${positionRef} · ${workshopLabel(key.slice(positionRef.length + 1), language)}`;
  }
  return workshopLabel(key, language);
}
