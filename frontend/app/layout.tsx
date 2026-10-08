import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { NavBar } from "@/components/NavBar";

export const metadata: Metadata = {
  title: { default: "StraOliva", template: "%s · StraOliva" },
  description: "Persönliches Trainingsdashboard für deine Strava-Daten",
  applicationName: "StraOliva",
  // iOS home-screen app: launch standalone (no Safari chrome) with this label
  appleWebApp: { capable: true, title: "StraOliva", statusBarStyle: "default" },
};

// Browser/title-bar color — matches the NavBar background in light and dark mode
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Let the page extend under the iPhone notch/home indicator; safe-area insets pad the nav bars
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#111827" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" suppressHydrationWarning>
      <head>
        {/* Prevent flash of wrong theme — reads localStorage before first paint */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(t!=='light'&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          }}
        />
      </head>
      <body className="bg-white dark:bg-gray-900 min-h-screen overflow-x-clip">
        <Providers>
          <NavBar />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-4 sm:pt-6 pb-[calc(5rem+env(safe-area-inset-bottom))] md:pb-6">
            {children}
            {/* Strava API brand guidelines: attribution + no implied endorsement */}
            <p className="mt-10 text-center text-[11px] text-gray-400 dark:text-gray-500">
              Powered by Strava · StraOliva is not affiliated with or endorsed by Strava, Inc.
            </p>
          </main>
        </Providers>
      </body>
    </html>
  );
}
