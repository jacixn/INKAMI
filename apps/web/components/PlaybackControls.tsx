"use client";

import type { PlaybackController } from "@/lib/types";

interface Props {
  controller: PlaybackController;
}

export default function PlaybackControls({ controller }: Props) {
  return (
    <section className="card flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={controller.prevBubble}
          className="rounded-full border border-white/20 px-3 py-2 text-xs uppercase tracking-[0.2em]"
        >
          Prev
        </button>
        <button
          type="button"
          onClick={controller.isPlaying ? controller.pause : controller.play}
          className="rounded-full bg-white px-6 py-2 text-sm font-semibold text-black"
        >
          {controller.isPlaying ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          onClick={controller.nextBubble}
          className="rounded-full border border-white/20 px-3 py-2 text-xs uppercase tracking-[0.2em]"
        >
          Next
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-2">
        <label className="text-xs uppercase text-ink-200">Speed</label>
        <input
          type="range"
          min="0.8"
          max="1.4"
          step="0.1"
          value={controller.speed}
          onChange={(event) => controller.setSpeed(Number(event.target.value))}
        />
      </div>
    </section>
  );
}

