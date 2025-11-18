"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import VoiceInspector from "@/components/VoiceInspector";
import { usePlaybackController } from "@/hooks/usePlaybackController";
import ImmersiveReader from "@/components/ImmersiveReader";

function getChapterId(value?: string | null): string {
  if (!value) return "";
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : "";
}

function ReaderPageContent() {
  const searchParams = useSearchParams();

  const chapterId = useMemo(() => {
    return getChapterId(searchParams?.get("id"));
  }, [searchParams]);

  const controller = usePlaybackController(chapterId);

  const missingChapterId = chapterId.length === 0;

  return missingChapterId ? (
    <div className="space-y-6">
      <section className="card space-y-3 text-center text-sm text-ink-100">
        <p className="text-base font-semibold text-white">No chapter selected</p>
        <p>
          Upload a chapter or open one from the Status page to preview voices in the
          reader.
        </p>
      </section>
    </div>
  ) : (
    <div className="space-y-6">
      <ImmersiveReader controller={controller} />
      <VoiceInspector controller={controller} />
    </div>
  );
}

export default function ReaderPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <p className="text-center text-sm text-white/60">Loading reader…</p>
        </div>
      }
    >
      <ReaderPageContent />
    </Suspense>
  );
}
