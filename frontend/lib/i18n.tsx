"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Lang = "de" | "en";

const STORAGE_KEY = "lang";
const DEFAULT_LANG: Lang = "de";

interface LangContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  /** Pick the string for the active language: t("Deutsch", "English") */
  t: (de: string, en: string) => string;
  /** BCP-47 locale for toLocaleDateString / Intl */
  locale: string;
}

const LangContext = createContext<LangContextValue | null>(null);

export function localeFor(lang: Lang): string {
  return lang === "de" ? "de-DE" : "en-GB";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  // Server render + first client render always use the default so hydration matches;
  // the stored preference is applied right after mount.
  const [lang, setLangState] = useState<Lang>(DEFAULT_LANG);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "de" || stored === "en") setLangState(stored);
    } catch {}
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch {}
  }, []);

  const t = useCallback((de: string, en: string) => (lang === "de" ? de : en), [lang]);

  return (
    <LangContext.Provider value={{ lang, setLang, t, locale: localeFor(lang) }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside <LanguageProvider>");
  return ctx;
}
