"use client";

import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { cn } from "@/lib/utils";
import LoadingOrbit from "./LoadingOrbit";

interface ProcessingStatusProps {
  chapterId: string;
}

export default function ProcessingStatus({ chapterId }: ProcessingStatusProps) {
  const { data, error, isLoading } = useSWR(
    chapterId ? `/api/chapters/${chapterId}` : null,
    fetcher,
    {
      refreshInterval: 3000
    }
  );

  const status = data?.status ?? "processing";
  const progress = data?.progress ?? 0;

  if (error) {
    return (
      <section className="card space-y-4">
        <h1 className="text-2xl font-semibold text-white">Processing failed</h1>
        <p className="text-sm text-ink-100">
          {error instanceof Error ? error.message : "Unknown error."}
        </p>
        <Link
          href="/upload"
          className="inline-flex rounded-full bg-white px-4 py-2 text-sm font-semibold text-black"
        >
          Try again
        </Link>
      </section>
    );
  }

  const steps = [
    { title: "Upload", done: progress >= 10 },
    { title: "Layout + OCR", done: progress >= 40 },
    { title: "Voice casting", done: progress >= 70 },
    { title: "Karaoke sync", done: progress >= 90 }
  ];

  return (
    <section className="glass-panel space-y-6 p-6">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-200">
          Chapter
        </p>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-semibold">#{chapterId}</h1>
          <span
            className={cn(
              "rounded-full px-3 py-1 text-xs font-semibold capitalize",
              status === "ready"
                ? "bg-green-500/20 text-green-200"
                : status === "failed"
                  ? "bg-red-500/20 text-red-100"
                  : "bg-ink-500/20 text-ink-100"
            )}
          >
            {status}
          </span>
        </div>
        <p className="text-sm text-ink-100">
          {status === "ready"
            ? "Playback is ready. Launch the reader below."
            : "We are scanning panels, reading bubbles, and generating voices."}
        </p>
      </header>

      <div className="space-y-4">
        <div className="flex justify-between text-xs text-ink-100">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="relative h-3 w-full overflow-hidden rounded-full bg-white/5">
          <div
            className="absolute inset-0 rounded-full bg-gradient-to-r from-sky-400 via-indigo-500 to-purple-500 transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="grid gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm">
        {steps.map((step) => (
          <div
            key={step.title}
            className="flex items-center justify-between text-white/80"
          >
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "h-3.5 w-3.5 rounded-full",
                  step.done ? "bg-emerald-400" : "bg-white/30"
                )}
              />
              {step.title}
            </div>
            <span className="text-xs uppercase tracking-[0.2em] text-white/50">
              {step.done ? "done" : "pending"}
            </span>
          </div>
        ))}
      </div>

      {status !== "ready" && (
        <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-white/70">
          <LoadingOrbit size={48} />
          <div>
            <p className="text-base font-medium text-white">Processing</p>
            <p>Ultra HD panels, bubble clustering, TTS voice mix.</p>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <Link
          href="/upload"
          className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/80"
        >
          Upload more
        </Link>
        <Link
          href={`/reader?id=${chapterId}`}
          className={cn(
            "rounded-full px-4 py-2 text-sm font-semibold transition",
            status === "ready"
              ? "bg-white text-black hover:bg-ink-100"
              : "pointer-events-none bg-white/20 text-white/50"
          )}
        >
          Open Reader
        </Link>
      </div>

      {isLoading && (
        <p className="text-xs text-ink-200">Listening for updates...</p>
      )}
    </section>
  );
}

