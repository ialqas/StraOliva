"use client";

import type { WindInfo } from "@/lib/api";
import { useLang, type Lang } from "@/lib/i18n";

const COMPASS_DIRS: Record<Lang, string[]> = {
  de: ["N", "NO", "O", "SO", "S", "SW", "W", "NW"],
  en: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
};

function compassLabel(deg: number, lang: Lang): string {
  return COMPASS_DIRS[lang][Math.round(deg / 45) % 8];
}

export function WindCompass({ wind }: { wind: WindInfo }) {
  const { lang, t } = useLang();
  const fromDeg = wind.direction_from ?? 0;
  const toDeg = (fromDeg + 180) % 360;
  // SVG coordinate system: 0° = right (+x), so subtract 90° to make 0° = up
  const rad = (toDeg - 90) * (Math.PI / 180);

  const cx = 44;
  const cy = 44;
  const tipX = cx + 28 * Math.cos(rad);
  const tipY = cy + 28 * Math.sin(rad);
  const tailX = cx - 22 * Math.cos(rad);
  const tailY = cy - 22 * Math.sin(rad);
  const perpX = -Math.sin(rad) * 6;
  const perpY = Math.cos(rad) * 6;

  const speedKmh = wind.speed_kmh ?? 0;
  const gustKmh = wind.gust_speed_ms != null ? Math.round(wind.gust_speed_ms * 3.6) : null;

  const speedColor =
    speedKmh < 10 ? "#9CA3AF" : speedKmh < 20 ? "#22C55E" : speedKmh < 35 ? "#EAB308" : "#EF4444";

  const cardinals = [
    { deg: 0, label: "N" },
    { deg: 90, label: lang === "de" ? "O" : "E" },
    { deg: 180, label: "S" },
    { deg: 270, label: "W" },
  ];

  return (
    <div
      className="flex items-center gap-3 bg-white/95 backdrop-blur-sm rounded-2xl shadow-lg"
      style={{ padding: "10px 14px", minWidth: 200 }}
    >
      {/* Compass rose SVG */}
      <svg viewBox="0 0 88 88" width="80" height="80" style={{ flexShrink: 0 }}>
        <circle cx="44" cy="44" r="40" fill="#F9FAFB" stroke="#E5E7EB" strokeWidth="1.5" />

        {/* Tick marks every 45° */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => {
          const r = (deg - 90) * (Math.PI / 180);
          const isCardinal = deg % 90 === 0;
          const inner = isCardinal ? 30 : 34;
          return (
            <line
              key={deg}
              x1={44 + inner * Math.cos(r)} y1={44 + inner * Math.sin(r)}
              x2={44 + 39 * Math.cos(r)}    y2={44 + 39 * Math.sin(r)}
              stroke={isCardinal ? "#9CA3AF" : "#D1D5DB"}
              strokeWidth={isCardinal ? 1.5 : 1}
            />
          );
        })}

        {/* Cardinal labels — N in red */}
        {cardinals.map(({ deg, label }) => {
          const r = (deg - 90) * (Math.PI / 180);
          return (
            <text
              key={label}
              x={44 + 23 * Math.cos(r)}
              y={44 + 23 * Math.sin(r) + 3.5}
              textAnchor="middle"
              fontSize="9"
              fontWeight="700"
              fill={deg === 0 ? "#EF4444" : "#6B7280"}
            >
              {label}
            </text>
          );
        })}

        {/* Tail dot — where wind comes FROM */}
        <circle cx={tailX} cy={tailY} r="3.5" fill="#94A3B8" />

        {/* Arrow shaft */}
        <line
          x1={tailX} y1={tailY}
          x2={tipX}   y2={tipY}
          stroke="#FC4C02" strokeWidth="2.5" strokeLinecap="round"
        />

        {/* Arrowhead */}
        <polygon
          points={`${tipX},${tipY} ${tipX - Math.cos(rad) * 10 + perpX},${tipY - Math.sin(rad) * 10 + perpY} ${tipX - Math.cos(rad) * 10 - perpX},${tipY - Math.sin(rad) * 10 - perpY}`}
          fill="#FC4C02"
        />

        {/* Speed in center */}
        <text x="44" y="47" textAnchor="middle" fontSize="10" fontWeight="700" fill={speedColor}>
          {speedKmh}
        </text>
        <text x="44" y="56" textAnchor="middle" fontSize="6.5" fill="#9CA3AF">
          km/h
        </text>
      </svg>

      {/* Text block */}
      <div style={{ lineHeight: 1.45, fontSize: 12 }}>
        <div style={{ fontWeight: 700, color: "#111" }}>
          {t("Aus", "From")} {wind.direction_from != null ? `${wind.direction_from}°` : "—"}
          {wind.direction_from != null && (
            <span style={{ fontWeight: 400, color: "#6B7280", marginLeft: 4 }}>
              ({compassLabel(wind.direction_from, lang)})
            </span>
          )}
        </div>
        <div style={{ marginTop: 2 }}>
          <span style={{ color: speedColor, fontWeight: 600 }}>
            {wind.speed_kmh != null ? `${wind.speed_kmh} km/h` : "—"}
          </span>
          {gustKmh != null && (
            <span style={{ color: "#9CA3AF", fontSize: 11, marginLeft: 4 }}>
              {t("Böen", "Gusts")} {gustKmh}
            </span>
          )}
        </div>
        {wind.station_name && (
          <div style={{ fontSize: 10, color: "#9CA3AF", marginTop: 4 }}>
            DWD {wind.station_name}
            {wind.station_distance_km != null ? ` · ${wind.station_distance_km} km` : ""}
          </div>
        )}
        <div style={{ fontSize: 10, color: "#CBD5E1", marginTop: 2 }}>
          {t("Pfeil → Windrichtung", "Arrow → wind direction")}
        </div>
      </div>
    </div>
  );
}
