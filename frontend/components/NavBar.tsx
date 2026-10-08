"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useLang, type Lang } from "@/lib/i18n";

// `short` labels are used in the mobile bottom tab bar, where space is tight
const links = [
  { href: "/",              de: "Dashboard",     en: "Dashboard",     shortDe: "Home",     shortEn: "Home",     icon: "M3 12l9-9 9 9M5 10v10h5v-6h4v6h5V10" },
  { href: "/activities",    de: "Aktivitäten",   en: "Activities",    shortDe: "Aktiv.",   shortEn: "Activities", icon: "M13 10V3L4 14h7v7l9-11h-7z" },
  { href: "/analytics",     de: "Analyse",       en: "Analytics",     shortDe: "Analyse",  shortEn: "Analytics", icon: "M4 20V10m6 10V4m6 16v-7m4 7H3" },
  { href: "/trainingsplan", de: "Trainingsplan", en: "Training Plan", shortDe: "Plan",     shortEn: "Plan",     icon: "M8 7V3m8 4V3M4 11h16M5 5h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z" },
  { href: "/heatmap",       de: "Heatmap",       en: "Heatmap",       shortDe: "Heatmap",  shortEn: "Heatmap",  icon: "M9 20l-5-2V4l5 2m0 14l6-2m-6 2V6m6 12l5 2V6l-5-2m0 14V4m0 0L9 6" },
  { href: "/wind",          de: "Wind",          en: "Wind",          shortDe: "Wind",     shortEn: "Wind",     icon: "M3 8h11a3 3 0 10-3-3M3 12h15a3 3 0 11-3 3M3 16h7" },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
}

function LanguageToggle() {
  const { lang, setLang, t } = useLang();
  const options: Lang[] = ["de", "en"];

  return (
    <div
      className="flex rounded-lg border border-border dark:border-gray-700 overflow-hidden text-xs font-medium shrink-0"
      role="group"
      aria-label={t("Sprache", "Language")}
    >
      {options.map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`px-2 py-1 transition-colors ${
            lang === l
              ? "bg-strava text-white"
              : "text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function ThemeToggle() {
  const { t } = useLang();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("theme", next ? "dark" : "light"); } catch {}
  }

  return (
    <button
      onClick={toggle}
      className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      title={dark ? t("Helles Design", "Light mode") : t("Dunkles Design", "Dark mode")}
      aria-label={t("Dunkelmodus umschalten", "Toggle dark mode")}
    >
      {dark ? (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364-.707.707M6.343 17.657l-.707.707m12.728 0-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
      )}
    </button>
  );
}

export function NavBar() {
  const pathname = usePathname();
  const { t } = useLang();

  return (
    <>
      {/* Top bar — full nav on desktop, logo + toggles on mobile */}
      <nav className="sticky top-0 z-40 bg-white dark:bg-gray-900 border-b border-border dark:border-gray-700 pt-[env(safe-area-inset-top)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center h-14 gap-4 md:gap-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="w-7 h-7 rounded-full bg-strava flex items-center justify-center">
              <span className="text-white font-bold text-xs">S</span>
            </div>
            <span className="font-bold text-[15px] tracking-tight dark:text-white">StraOliva</span>
          </Link>

          {/* Nav links (desktop) */}
          <div className="hidden md:flex items-center gap-1 flex-1">
            {links.map((link) => {
              const active = isActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-strava/10 text-strava"
                      : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  {t(link.de, link.en)}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 shrink-0 ml-auto md:ml-0">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>
      </nav>

      {/* Bottom tab bar (mobile / PWA) */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 dark:bg-gray-900/95 backdrop-blur border-t border-border dark:border-gray-700 pb-[env(safe-area-inset-bottom)]"
        aria-label={t("Hauptnavigation", "Main navigation")}
      >
        <div className="grid grid-cols-6">
          {links.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center justify-center gap-0.5 h-14 text-[10px] font-medium transition-colors ${
                  active ? "text-strava" : "text-gray-500 dark:text-gray-400 active:bg-gray-100 dark:active:bg-gray-800"
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={active ? 2.2 : 1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={link.icon} />
                </svg>
                <span className="truncate max-w-full px-0.5">{t(link.shortDe, link.shortEn)}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
