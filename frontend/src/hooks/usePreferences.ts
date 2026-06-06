import { useState, useEffect, useCallback } from "react";

export interface UserPreferences {
  defaultChartType?: "bar" | "line" | "pie" | "table" | "auto";
  tablePageSize?: number;
  darkMode?: boolean;
}

const STORAGE_KEY = "chatbi_prefs";
const DEFAULTS: UserPreferences = {
  defaultChartType: "auto",
  tablePageSize: 10,
  darkMode: false,
};

export function usePreferences() {
  const [prefs, setPrefsState] = useState<UserPreferences>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
    } catch {
      return DEFAULTS;
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    // toggle dark mode class on body
    if (prefs.darkMode) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  }, [prefs]);

  const setPrefs = useCallback((partial: Partial<UserPreferences>) => {
    setPrefsState((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetPrefs = useCallback(() => {
    setPrefsState(DEFAULTS);
  }, []);

  return { prefs, setPrefs, resetPrefs };
}
