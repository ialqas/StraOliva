"use client";

interface Props {
  text: string;
  children?: React.ReactNode;
}

/**
 * Wraps any text/content with a hover tooltip showing an explanation.
 * Usage: <InfoTooltip text="Explanation here">Label</InfoTooltip>
 */
export function InfoTooltip({ text, children }: Props) {
  return (
    // tabIndex makes it focusable, so a tap on touch devices opens it (focus-within) — hover only works with a mouse
    <span tabIndex={0} className="group relative inline-flex items-center gap-1 cursor-default outline-none">
      {children}
      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-300 text-[9px] font-bold leading-none select-none">
        ?
      </span>
      {/* Tooltip bubble — left-anchored on phones so it can't overflow the left screen edge */}
      <span
        className="
          pointer-events-none absolute bottom-full left-0 sm:left-1/2 sm:-translate-x-1/2 mb-2
          w-56 max-w-[calc(100vw-2rem)] rounded-lg bg-gray-900 dark:bg-gray-700 text-white text-[11px]
          normal-case tracking-normal font-normal leading-relaxed px-3 py-2 shadow-lg
          opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity duration-150 z-50
        "
        role="tooltip"
      >
        {text}
        {/* Arrow */}
        <span className="absolute top-full left-3 sm:left-1/2 sm:-translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
      </span>
    </span>
  );
}
