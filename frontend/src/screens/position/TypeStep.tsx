/** The five construction types as drawings at the measured proportions: the drawing is the button. */
import { useTranslation } from "react-i18next";

import type { Opening } from "../../api/types";
import { WindowDrawing } from "../../components/WindowDrawing";

export const TYPE_ORDER = [
  "single_sash_tilt_turn",
  "two_field_t_mullion",
  "two_sash_false_mullion",
  "fixed",
  "balcony_door_tilt_turn",
] as const;

export const DEFAULT_OPENINGS: Record<string, Opening[]> = {
  single_sash_tilt_turn: ["tilt_turn_left"],
  two_field_t_mullion: ["turn_left", "tilt_turn_right"],
  two_sash_false_mullion: ["turn_left", "tilt_turn_right"],
  fixed: ["fixed"],
  balcony_door_tilt_turn: ["tilt_turn_left"],
};

export function TypeStep({
  width,
  height,
  value,
  onPick,
}: {
  width: number;
  height: number;
  value: string | null;
  onPick: (type: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="px-4 pt-4 pb-8">
      <h2 className="text-2xl font-extrabold">{t("position.stepType")}</h2>
      <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {TYPE_ORDER.map((type) => {
          const door = type === "balcony_door_tilt_turn";
          const chosen = value === type;
          return (
            <li key={type}>
              <button
                type="button"
                aria-pressed={chosen}
                onClick={() => onPick(type)}
                className={`flex w-full flex-col items-center gap-2 rounded-slot p-3 text-center transition-colors duration-150 ${chosen ? "bg-chalk-tint outline-3 outline-chalk" : "bg-board hover:bg-chalk-tint/60"}`}
              >
                <WindowDrawing
                  type={type}
                  width={door ? Math.min(width, 900) : width}
                  height={door ? Math.max(height, 2100) : height}
                  openings={DEFAULT_OPENINGS[type] ?? ["fixed"]}
                  className="h-32 w-full"
                />
                <span className="text-base leading-tight font-bold">{t(`types.${type}`)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
