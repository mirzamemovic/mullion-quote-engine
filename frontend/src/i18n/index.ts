/**
 * English by default, Bosnian one tap away. A person's own choice is remembered on the device;
 * until they choose, the app follows their workshop's language once they are logged in.
 */
import i18next from "i18next";
import { initReactI18next } from "react-i18next";

import bs from "./bs.json";
import en from "./en.json";

export const LANGUAGES = ["en", "bs"] as const;
export type Language = (typeof LANGUAGES)[number];
const STORAGE_KEY = "mullion.language";

function storedLanguage(): Language | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "en" || value === "bs" ? value : null;
  } catch {
    return null;
  }
}

/** The person picked a language on this device (it then wins over the workshop's default). */
export function hasChosenLanguage(): boolean {
  return storedLanguage() !== null;
}

function apply(language: Language): void {
  void i18next.changeLanguage(language);
  document.documentElement.lang = language;
}

/** The person's own choice, remembered on this device. */
export function setLanguage(language: Language): void {
  apply(language);
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Private mode or blocked storage: the choice lasts for this visit only.
  }
}

/** The workshop's language, used only while the person has not chosen one. */
export function followWorkshopLanguage(language: string): void {
  if (!hasChosenLanguage() && (language === "en" || language === "bs") && i18next.language !== language) {
    apply(language);
  }
}

void i18next.use(initReactI18next).init({
  resources: { en: { translation: en }, bs: { translation: bs } },
  lng: storedLanguage() ?? "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false }, // React escapes everything it renders
  returnNull: false,
});
document.documentElement.lang = i18next.language;

export default i18next;
