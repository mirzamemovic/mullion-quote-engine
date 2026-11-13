/**
 * A window drawn from inside, the way the workshop draws it: frame and sash corners as 45°
 * mitres, a fixed mullion butting at 90°, and nothing else. Opening symbols follow the European
 * convention: the triangle's point is on the hinge side, dashed lines show tilt, and the handle
 * sits on the other side. ``*_left`` means hinges on the left, seen from inside.
 */
import type { Colour, Opening } from "../api/types";

const FIELDS: Record<string, number> = {
  single_sash_tilt_turn: 1,
  two_field_t_mullion: 2,
  two_sash_false_mullion: 2,
  fixed: 1,
  balcony_door_tilt_turn: 1,
};

export function fieldCount(type: string): number {
  return FIELDS[type] ?? 1;
}

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** A ring of profile ``t`` wide inside ``box``, its four corners mitred at 45°. */
function Ring({ box, t, fill }: { box: Box; t: number; fill: string }) {
  const { x, y, w, h } = box;
  const outer = `M${x},${y}h${w}v${h}h${-w}z`;
  const inner = `M${x + t},${y + t}v${h - 2 * t}h${w - 2 * t}v${-(h - 2 * t)}z`;
  const mitres = [
    `M${x},${y}L${x + t},${y + t}`,
    `M${x + w},${y}L${x + w - t},${y + t}`,
    `M${x},${y + h}L${x + t},${y + h - t}`,
    `M${x + w},${y + h}L${x + w - t},${y + h - t}`,
  ].join("");
  return (
    <g>
      <path d={`${outer}${inner}`} fill={fill} fillRule="evenodd" className="stroke-graphite" />
      <path d={mitres} className="stroke-graphite" />
    </g>
  );
}

function OpeningMarks({ box, opening }: { box: Box; opening: Opening }) {
  if (opening === "fixed") return null;
  const { x, y, w, h } = box;
  const hingeLeft = opening.endsWith("_left");
  const hingeX = hingeLeft ? x : x + w;
  const handleX = hingeLeft ? x + w : x;
  const turn = `M${handleX},${y}L${hingeX},${y + h / 2}L${handleX},${y + h}`;
  const tilt = `M${x},${y}L${x + w / 2},${y + h}L${x + w},${y}`;
  const handleW = Math.max(2, w * 0.035);
  const handleH = Math.max(6, h * 0.12);
  return (
    <g>
      <path d={turn} fill="none" className="stroke-graphite" />
      {opening.startsWith("tilt_turn") && (
        <path d={tilt} fill="none" className="stroke-graphite" strokeDasharray="4 3" />
      )}
      <rect
        x={hingeLeft ? handleX - handleW * 2.2 : handleX + handleW * 1.2}
        y={y + h / 2 - handleH / 2}
        width={handleW}
        height={handleH}
        rx={handleW / 2}
        className="fill-graphite"
        data-handle={hingeLeft ? "right" : "left"}
      />
    </g>
  );
}

export interface WindowDrawingProps {
  type: string;
  width: number;
  height: number;
  openings: Opening[];
  colour?: Colour;
  className?: string;
  title?: string;
  /** Line weight in screen pixels: 2 for pickers, about 1.25 for small thumbnails. */
  stroke?: number;
}

export function WindowDrawing({
  type,
  width,
  height,
  openings,
  colour = "white",
  className = "",
  title,
  stroke = 2,
}: WindowDrawingProps) {
  // Draw in a 1000-unit box on the longer side so line weights stay even at any size.
  const scale = 1000 / Math.max(width, height, 1);
  const W = Math.max(width * scale, 200);
  const H = Math.max(height * scale, 200);
  const pad = 14;
  const t = Math.min(W, H) * 0.075;
  const frameFill = colour === "foil_both_sides" ? "url(#foil)" : "var(--color-board)";
  const frame: Box = { x: pad, y: pad, w: W, h: H };
  const inner: Box = { x: pad + t, y: pad + t, w: W - 2 * t, h: H - 2 * t };
  const count = fieldCount(type);
  const mullion = type === "two_field_t_mullion" ? t * 0.9 : 0;
  const fieldW = (inner.w - mullion) / count;
  const fields: Box[] = Array.from({ length: count }, (_, i) => ({
    x: inner.x + i * (fieldW + mullion),
    y: inner.y,
    w: fieldW,
    h: inner.h,
  }));

  return (
    <svg
      viewBox={`0 0 ${W + 2 * pad} ${H + 2 * pad}`}
      className={`window-drawing ${className}`}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      strokeWidth={stroke}
    >
      <defs>
        <pattern id="foil" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="12" height="12" fill="var(--color-plaster-deep)" />
          <line x1="0" y1="0" x2="0" y2="12" stroke="var(--color-graphite-line)" strokeWidth="3" />
        </pattern>
      </defs>
      <Ring box={frame} t={t} fill={frameFill} />
      {mullion > 0 && (
        <rect
          x={inner.x + fieldW}
          y={inner.y}
          width={mullion}
          height={inner.h}
          fill={frameFill}
          className="stroke-graphite"
        />
      )}
      {fields.map((field, i) => {
        const opening = openings[i] ?? "fixed";
        const glass = opening === "fixed" ? field : {
          x: field.x + t * 0.8,
          y: field.y + t * 0.8,
          w: field.w - 1.6 * t,
          h: field.h - 1.6 * t,
        };
        return (
          <g key={i}>
            <rect
              x={glass.x}
              y={glass.y}
              width={glass.w}
              height={glass.h}
              className="fill-chalk-tint stroke-graphite"
            />
            {opening !== "fixed" && <Ring box={field} t={t * 0.8} fill={frameFill} />}
            <OpeningMarks box={glass} opening={opening} />
          </g>
        );
      })}
    </svg>
  );
}
