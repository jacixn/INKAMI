"use client";

import { cn } from "@/lib/utils";
import type { PlaybackController } from "@/lib/types";

interface Props {
  controller: PlaybackController;
  variant?: "card" | "overlay";
  onToggleFullscreen?: () => void;
  isFullscreen?: boolean;
}

export default function PlaybackControls({
  controller,
  variant = "card",
  onToggleFullscreen,
  isFullscreen
}: Props) {
  const wrapperClass =
    variant === "overlay"
      ? "rounded-[32px] border border-white/10 bg-black/70 px-5 py-4 flex flex-col gap-4 backdrop-blur-xl"
      : "card flex flex-col gap-4 md:flex-row md:items-center md:justify-between";

  const buttonClass = cn(
    "flex h-12 w-12 items-center justify-center rounded-full border border-white/20 text-white transition hover:border-white/50",
    variant === "overlay" && "bg-white/5"
  );

  return (
    <section className={wrapperClass}>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={controller.prevBubble}
          className={buttonClass}
          aria-label="Previous bubble"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              d="M10.8 5.25 7.2 9l3.6 3.75"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        <button
          type="button"
          onClick={controller.isPlaying ? controller.pause : controller.play}
          className={cn(
            "rounded-full px-6 py-3 text-sm font-semibold transition",
            controller.isPlaying
              ? "bg-white/80 text-black"
              : "bg-white text-black hover:bg-ink-100"
          )}
        >
          {controller.isPlaying ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          onClick={controller.nextBubble}
          className={buttonClass}
          aria-label="Next bubble"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              d="M7.2 12.75 10.8 9 7.2 5.25"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        {onToggleFullscreen && (
          <button
            type="button"
            onClick={onToggleFullscreen}
            className={cn(
              "ml-auto inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/60",
              variant === "overlay" && "bg-white/10 backdrop-blur"
            )}
          >
            {isFullscreen ? "Exit full screen" : "Full screen"}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M5.5 3H3v2.5M10.5 3H13v2.5M5.5 13H3v-2.5M10.5 13H13v-2.5"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
            </svg>
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2">
        <label className="text-xs uppercase tracking-[0.4em] text-white/60">
          Speed
        </label>
        <input
          type="range"
          min="0.8"
          max="1.4"
          step="0.1"
          value={controller.speed}
          onChange={(event) => controller.setSpeed(Number(event.target.value))}
          className="accent-white"
        />
      </div>
    </section>
  );
}

