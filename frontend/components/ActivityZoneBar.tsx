"use client";

const ZONE_COLORS: Record<string, string> = {
  Z1: "#9CA3AF",
  Z2: "#60A5FA",
  Z3: "#34D399",
  Z4: "#FBBF24",
  Z5: "#F87171",
  Z6: "#A78BFA",
  Z7: "#F43F5E",
};

interface Props {
  zones: Record<string, number>;
  label: string;
}

function fmtTime(secs: number): string {
  if (secs < 60) return `${Math.round(secs)}s`;
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  if (m < 60) return `${m}:${String(s).padStart(2, "0")}`;
  const h = Math.floor(m / 60);
  return `${h}:${String(m % 60).padStart(2, "0")}h`;
}

export function ActivityZoneBar({ zones, label }: Props) {
  const entries = Object.entries(zones).filter(([, v]) => v > 0);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  if (total === 0) return null;

  return (
    <div>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">{label}</p>
      {/* Stacked bar */}
      <div className="flex h-5 rounded-full overflow-hidden w-full gap-px">
        {entries.map(([zone, secs]) => (
          <div
            key={zone}
            style={{ width: `${(secs / total) * 100}%`, background: ZONE_COLORS[zone] ?? "#ccc" }}
            title={`${zone}: ${fmtTime(secs)} (${Math.round((secs / total) * 100)}%)`}
          />
        ))}
      </div>
      {/* Zone pills */}
      <div className="flex flex-wrap gap-2 mt-2">
        {entries.map(([zone, secs]) => (
          <span key={zone} className="flex items-center gap-1 text-[11px] text-gray-500">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: ZONE_COLORS[zone] ?? "#ccc" }} />
            {zone} {fmtTime(secs)} · {Math.round((secs / total) * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}
