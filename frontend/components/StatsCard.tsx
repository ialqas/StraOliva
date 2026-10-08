interface StatsCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
  color?: string;
}

export function StatsCard({ label, value, sub, accent, color }: StatsCardProps) {
  return (
    <div className="bg-white border border-border rounded-xl p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p
        className={`text-2xl font-bold mt-1 tabular-nums ${accent ? "text-strava" : ""}`}
        style={color ? { color } : undefined}
      >
        {value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function FormBadge({ tsb }: { tsb: number }) {
  let label: string;
  let cls: string;

  if (tsb > 10) { label = "Fresh"; cls = "bg-emerald-50 text-emerald-700 border-emerald-200"; }
  else if (tsb > -10) { label = "Neutral"; cls = "bg-gray-50 text-gray-600 border-gray-200"; }
  else if (tsb > -20) { label = "Tired"; cls = "bg-amber-50 text-amber-700 border-amber-200"; }
  else { label = "Very Tired"; cls = "bg-red-50 text-red-700 border-red-200"; }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {label}
    </span>
  );
}
