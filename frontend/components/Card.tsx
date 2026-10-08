import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  /** Remove default padding (e.g. when card contains a table with its own padding) */
  noPad?: boolean;
}

export function Card({ children, className = "", noPad = false }: CardProps) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 border border-border dark:border-gray-700 rounded-xl ${noPad ? "" : "p-5"} ${className}`}
    >
      {children}
    </div>
  );
}

interface TitleProps {
  children: ReactNode;
  className?: string;
}

/** Standardized card section title: 11px · uppercase · tracking-wide · muted */
export function CardTitle({ children, className = "" }: TitleProps) {
  return (
    <p className={`text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide ${className}`}>
      {children}
    </p>
  );
}

/** Big metric value — 28-32px, weight 500 */
export function MetricValue({
  children,
  color,
  className = "",
}: {
  children: ReactNode;
  color?: string;
  className?: string;
}) {
  return (
    <p
      className={`text-[30px] font-medium tabular-nums leading-tight ${className}`}
      style={color ? { color } : undefined}
    >
      {children}
    </p>
  );
}

/** Small interpretation / sub-text line */
export function MetricSub({ children, className = "" }: TitleProps) {
  return (
    <p className={`text-[13px] text-gray-500 dark:text-gray-400 leading-snug ${className}`}>
      {children}
    </p>
  );
}
