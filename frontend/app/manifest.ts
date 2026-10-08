import type { MetadataRoute } from "next";

// Served at /manifest.webmanifest — makes the dashboard installable as a PWA.
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "StraOliva",
    short_name: "StraOliva",
    description: "Persönliches Trainingsdashboard für deine Strava-Daten",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#ffffff",
    lang: "de",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
