/** A small authored icon set: 24 px grid, one 2.25 px round stroke, drawn like pencil marks. */
const PATHS = {
  back: "M15 5l-7 7 7 7",
  forward: "M9 5l7 7-7 7",
  plus: "M12 5v14M5 12h14",
  check: "M5 12.5l4.5 4.5L19 7.5",
  close: "M6 6l12 12M18 6L6 18",
  search: "M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13zM15.5 15.5L20 20",
  copy: "M8 8h11v11H8zM5 16V5h11",
  share: "M12 4v11M7.5 8.5L12 4l4.5 4.5M5 14v5h14v-5",
  download: "M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19h14",
  logout: "M14 4h5v16h-5M10 8l-4 4 4 4M6 12h9",
  sliders: "M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4",
  edit: "M5 19l1-4 10-10 3 3-10 10-4 1zM14 7l3 3",
  trash: "M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13",
  alert: "M12 4l9 16H3zM12 10v4M12 17v.5",
  minus: "M5 12h14",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "size-6" }: { name: IconName; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={2.25}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
