"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import VoiceInspector from "@/components/VoiceInspector";
import { usePlaybackController } from "@/hooks/usePlaybackController";
import ImmersiveReader from "@/components/ImmersiveReader";

const FALLBACK_CHAPTER_ID = "demo";

function getChapterId(value?: string | null): string {
  if (!value) return FALLBACK_CHAPTER_ID;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : FALLBACK_CHAPTER_ID;
}

function ReaderPageContent() {
  const searchParams = useSearchParams();

  const chapterId = useMemo(() => {
    return getChapterId(searchParams?.get("id"));
  }, [searchParams]);

  const controller = usePlaybackController(chapterId);

  return (
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
