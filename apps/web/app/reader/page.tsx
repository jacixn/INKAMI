"use client";

import VoiceInspector from "@/components/VoiceInspector";
import { usePlaybackController } from "@/hooks/usePlaybackController";
import ImmersiveReader from "@/components/ImmersiveReader";

const FALLBACK_CHAPTER_ID = "demo";

function getChapterId(value?: string | string[]): string {
  if (!value) return FALLBACK_CHAPTER_ID;
  const normalized = Array.isArray(value) ? value[0] : value;
  const trimmed = normalized?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : FALLBACK_CHAPTER_ID;
}

interface ReaderPageProps {
  searchParams?: {
    id?: string | string[];
  };
}

export default function ReaderPage({ searchParams }: ReaderPageProps) {
  const chapterId = getChapterId(searchParams?.id);
  const controller = usePlaybackController(chapterId);

  return (
    <div className="space-y-6">
      <ImmersiveReader controller={controller} />
      <VoiceInspector controller={controller} />
    </div>
  );
}
