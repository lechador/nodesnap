import type { CSSProperties } from "react";
export type IconName =
  | "cube"
  | "plan"
  | "layers"
  | "arrow"
  | "mic"
  | "stop"
  | "download"
  | "undo"
  | "redo"
  | "chevron"
  | "close"
  | "plus"
  | "minus"
  | "fit"
  | "spark"
  | "check"
  | "clock"
  | "info"
  | "file"
  | "grid"
  | "eye"
  | "settings"
  | "history"
  | "chat"
  | "sun"
  | "rotate"
  | "move"
  | "link"
  | "menu";
const paths: Record<IconName, React.ReactNode> = {
  cube: (
    <>
      <path d="m12 3 9 5v8l-9 5-9-5V8Z" />
      <path d="m3 8 9 5 9-5M12 13v8m-4.5-15.5 9 5" />
    </>
  ),
  plan: (
    <>
      <path d="M3 3h18v18H3ZM3 12h8V3m0 9v9m0-7h6m4 0h-2" />
      <path d="M17 14v4h4" />
    </>
  ),
  layers: (
    <>
      <path d="m12 3 10 5-10 5L2 8Zm-9 10 9 5 9-5M3 18l9 4 9-4" />
    </>
  ),
  arrow: (
    <>
      <path d="M12 20V4m-6 6 6-6 6 6" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="2" width="6" height="13" rx="3" />
      <path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8" />
    </>
  ),
  stop: <rect x="5" y="5" width="14" height="14" rx="2" />,
  download: (
    <>
      <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />
    </>
  ),
  undo: <path d="m8 4-5 5 5 5M3 9h11a6 6 0 0 1 0 12h-3" />,
  redo: <path d="m16 4 5 5-5 5m5-5H10a6 6 0 0 0 0 12h3" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  fit: (
    <>
      <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />
      <rect x="8" y="8" width="8" height="8" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6m0-10v.1" />
    </>
  ),
  file: (
    <>
      <path d="M14 2H5v20h14V7Zm0 0v5h5M8 12h8m-8 4h6" />
    </>
  ),
  grid: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="1" />
      <path d="M9 3v18m6-18v18M3 9h18M3 15h18" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  settings: (
    <>
      <path d="M4 7h16M4 17h16" />
      <circle cx="9" cy="7" r="3" />
      <circle cx="15" cy="17" r="3" />
    </>
  ),
  history: (
    <>
      <path d="M3 10a9 9 0 1 1 0 5M3 3v7h7M12 7v6l3 2" />
    </>
  ),
  chat: (
    <path d="M21 15a3 3 0 0 1-3 3H8l-5 4V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3Z" />
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 1v2m0 18v2M1 12h2m18 0h2M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2" />
    </>
  ),
  rotate: (
    <>
      <path d="M3 10a9 9 0 1 1 2 8M3 3v7h7" />
    </>
  ),
  move: (
    <>
      <path d="M12 2v20M2 12h20m-13-7 3-3 3 3M9 19l3 3 3-3M5 9l-3 3 3 3m14-6 3 3-3 3" />
    </>
  ),
  link: (
    <>
      <path d="m10 13 4-4m-7 6-2 2a4 4 0 0 0 6 6l3-3m-4-10 3-3a4 4 0 0 1 6 6l-2 2" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
};
export default function Icon({
  name,
  size = 18,
  style,
}: {
  name: IconName;
  size?: number;
  style?: CSSProperties;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={style}
    >
      {paths[name]}
    </svg>
  );
}
