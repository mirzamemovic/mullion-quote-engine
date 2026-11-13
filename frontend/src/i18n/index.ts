/** Bosnian by default, English one tap away (PLAN.md section 7). The choice is remembered. */
import i18next from "i18next";
import { initReactI18next } from "react-i18next";

import bs from "./bs.json";
import en from "./en.json";

export const LANGUAGES = ["bs", "en"] as const;
export type Language = (typeof LANGUAGES)[number];
const STORAGE_KEY = "mjera.language";

function storedLanguage(): Language {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "en" ? "en" : "bs";
  } catch {
    return "bs";
  }
}

export function setLanguage(language: Language): void {
  void i18next.changeLanguage(language);
  document.documentElement.lang = language;
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Private mode or blocked storage: the choice lasts for this visit only.
  }
}

void i18next.use(initReactI18next).init({
  resources: { bs: { translation: bs }, en: { translation: en } },
  lng: storedLanguage(),
  fallbackLng: "bs",
  interpolation: { escapeValue: false }, // React escapes everything it renders
  returnNull: false,
});
document.documentElement.lang = i18next.language;

export default i18next;
