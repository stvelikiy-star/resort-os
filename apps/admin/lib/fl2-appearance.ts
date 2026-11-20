/** MARINA SMART Future Luxury appearance ONLY; no server/session/business data. */
export type Fl2Theme = "dark" | "light";
const STORAGE_KEY = "marina-fl2-theme";

export function readFl2Theme(): Fl2Theme {
  if (typeof window === "undefined") return "dark";
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function writeFl2Theme(theme: Fl2Theme): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Appearance remains available during this session even if storage is denied.
  }
}
