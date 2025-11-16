"use client";

import { useEffect, useMemo, useState } from "react";

const mockBubbles = [
  {
    id: "bubble_a",
    label: "Heroine",
    tone: "Warm soprano",
    text: "Hold on, I'm reading the flow of mana around us...",
    color: "from-pink-500/70 via-purple-400/60 to-blue-500/50",
    duration: 3200
  },
  {
    id: "bubble_b",
    label: "Narrator",
    tone: "Cinematic bass",
    text: "A hush fell across the citadel as the guardian awoke.",
    color: "from-indigo-400/60 via-blue-500/60 to-cyan-400/40",
    duration: 3600
  },
  {
    id: "bubble_c",
    label: "Rival",
    tone: "Confident tenor",
    text: "If you stumble, I'll finish the chapter for you.",
    color: "from-amber-400/70 via-orange-500/60 to-red-500/40",
    duration: 2800
  }
];

export default function LiveNarrationMock() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const active = mockBubbles[index];
    const timeout = setTimeout(() => {
      setIndex((idx) => (idx + 1) % mockBubbles.length);
    }, active.duration);
    return () => clearTimeout(timeout);
  }, [index]);

  const waveformBars = useMemo(
    () =>
      Array.from({ length: 24 }).map((_, idx) => ({
        height: 20 + Math.abs(Math.sin((idx + index) / 4)) * 60
      })),
    [index]
  );

  return (
    <div className="glass-panel relative overflow-hidden p-6 sm:p-8">
      <div className="absolute inset-0 bg-gradient-to-b from-white/10 via-transparent to-transparent" />
      <header className="relative mb-6 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-white/60">
            Live Preview
          </p>
          <h2 className="text-2xl font-semibold text-white md:text-3xl">
            Adaptive voice acting
          </h2>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-1 text-xs">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
          Demo feed
        </div>
      </header>

      <div className="relative rounded-3xl border border-white/10 bg-black/40 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.45)]">
        {mockBubbles.map((bubble, bubbleIndex) => {
          const isActive = bubbleIndex === index;

          return (
            <div
              key={bubble.id}
              className={`mb-3 rounded-2xl border border-white/10 bg-white/5 p-4 transition-all duration-500 last:mb-0 ${
                isActive ? "backdrop-blur-xl ring-2 ring-white/40" : "opacity-60"
              }`}
            >
              <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-white/60">
                <span>{bubble.label}</span>
                <span>{bubble.tone}</span>
              </div>
              <p className="mt-3 text-base text-white/90">{bubble.text}</p>
              {isActive && (
                <div className="mt-4 flex items-center gap-3">
                  <div className="h-10 flex-1 overflow-hidden rounded-full bg-black/60">
                    <div
                      className={`h-full w-full animate-[shimmer_4s_linear_infinite] bg-gradient-to-r ${bubble.color}`}
                    />
                  </div>
                  <span className="rounded-full border border-white/20 px-3 py-1 text-xs text-white/70">
                    AI Voice
                  </span>
                </div>
              )}
            </div>
          );
        })}

        <div className="mt-6 rounded-2xl border border-white/10 bg-gradient-to-br from-black/60 to-black/30 p-4">
          <div className="flex items-center justify-between text-xs text-white/70">
            <span>Wave sync</span>
            <span>word-level timing</span>
          </div>
          <div className="mt-3 flex items-end gap-1">
            {waveformBars.map((bar, idx) => (
              <span
                // eslint-disable-next-line react/no-array-index-key
                key={`${index}-${idx}`}
                className="w-2 rounded-full bg-white/40"
                style={{
                  height: `${bar.height}px`,
                  opacity: 0.5 + (idx % 3) * 0.15
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

