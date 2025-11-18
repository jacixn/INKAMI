"use client";

import { useMemo, useState } from "react";
import { useSWRConfig } from "swr";
import type { PlaybackController } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  controller: PlaybackController;
}

const voiceOptions = [
  { id: "voice_child_f", label: "Young Girl • Child" },
  { id: "voice_young_f", label: "Young Woman • Heroine" },
  { id: "voice_adult_f", label: "Mature Woman • Wise" },
  { id: "voice_child_m", label: "Young Boy • Child" },
  { id: "voice_young_m", label: "Young Man • Hero" },
  { id: "voice_adult_m", label: "Mature Man • Warrior" },
  { id: "voice_narrator", label: "Narrator • Story" },
  { id: "voice_system", label: "System Voice • UI" }
];

export default function VoiceInspector({ controller }: Props) {
  const [message, setMessage] = useState<string | null>(null);
  const { mutate } = useSWRConfig();

  const roster = useMemo(() => {
    const entries = new Map<
      string,
      { speaker_id: string; speaker_name?: string; voice_id: string; type: string }
    >();
    controller.pages.forEach((page) => {
      page.items.forEach((item) => {
        if (!entries.has(item.speaker_id)) {
          entries.set(item.speaker_id, {
            speaker_id: item.speaker_id,
            speaker_name: item.speaker_name,
            voice_id: item.voice_id,
            type: item.type
          });
        }
      });
    });
    return Array.from(entries.values());
  }, [controller.pages]);

  async function handleUpdate(
    speakerId: string,
    currentVoice: string,
    newVoice: string
  ) {
    if (currentVoice === newVoice) return;

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      await fetch(`${apiBase}/api/speakers/${speakerId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_id: newVoice })
      });
      if (controller.chapterId && controller.chapterId !== "demo") {
        await mutate(`/api/chapters/${controller.chapterId}`);
      }
      setMessage("Voice updated.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Voice update failed."
      );
    }
  }

  return (
    <aside className="card space-y-4">
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-ink-200">
          Voices
        </p>
        <h3 className="text-xl font-semibold text-white">
          Character Registry
        </h3>
      </header>

      {roster.length === 0 && (
        <p className="text-sm text-ink-100">
          Upload a chapter and start playback to see detected speakers.
        </p>
      )}

      <div className="space-y-3">
        {roster.map((entry) => (
          <div
            key={entry.speaker_id}
            className="rounded-xl bg-white/5 p-4 text-sm text-white/90"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base font-semibold">
                  {entry.speaker_name ?? entry.speaker_id}
                </p>
                <p className="text-xs uppercase tracking-[0.3em] text-ink-200">
                  {entry.type}
                </p>
              </div>
              <span
                className={cn(
                  "rounded-full px-3 py-1 text-xs",
                  entry.voice_id === "voice_narrator"
                    ? "bg-blue-500/20 text-blue-100"
                    : "bg-purple-500/20 text-purple-100"
                )}
              >
                {entry.voice_id}
              </span>
            </div>
            <label className="mt-3 block text-xs text-ink-200">
              Assign voice
            </label>
            <select
              className="mt-1 w-full rounded-lg bg-black/40 px-3 py-2 text-white"
              value={entry.voice_id}
              onChange={(event) =>
                handleUpdate(entry.speaker_id, entry.voice_id, event.target.value)
              }
            >
              {voiceOptions.map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {message && (
        <p className="text-xs text-ink-100" role="status">
          {message}
        </p>
      )}
    </aside>
  );
}

