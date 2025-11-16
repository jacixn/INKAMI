"use client";

import ReaderCanvas from "@/components/ReaderCanvas";
import VoiceInspector from "@/components/VoiceInspector";
import { usePlaybackController } from "@/hooks/usePlaybackController";
import PlaybackControls from "@/components/PlaybackControls";
import { useParams } from "next/navigation";

export default function ReaderPage() {
  const params = useParams<{ chapterId: string }>();
  const controller = usePlaybackController(params.chapterId);

  return (
    <div className="grid gap-6 md:grid-cols-[2fr,1fr]">
      <div className="space-y-4">
        <ReaderCanvas controller={controller} />
        <PlaybackControls controller={controller} />
      </div>
      <VoiceInspector controller={controller} />
    </div>
  );
}

