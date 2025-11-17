"use client";

import { useEffect, useMemo, useRef } from "react";

import type { PlaybackController } from "@/lib/types";
import ReaderCanvas from "./ReaderCanvas";
import PlaybackControls from "./PlaybackControls";

interface ImmersiveReaderProps {
  controller: PlaybackController & { loading: boolean };
}

const BASE_CANVAS_HEIGHT = 1920;

export default function ImmersiveReader({ controller }: ImmersiveReaderProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const page = controller.pages[controller.currentPageIndex];

  const activeBubble = useMemo(() => {
    if (!page) return undefined;
    return page.items.find((item) => item.bubble_id === controller.currentBubbleId);
  }, [page, controller.currentBubbleId]);

  useEffect(() => {
    if (!scrollRef.current || !activeBubble) return;
    const container = scrollRef.current;
    const scale = container.scrollHeight / BASE_CANVAS_HEIGHT;
    const target = Math.max(activeBubble.bubble_box[1] * scale - container.clientHeight / 3, 0);
    container.scrollTo({ top: target, behavior: "smooth" });
  }, [activeBubble, controller.currentPageIndex]);

  return (
    <div className="space-y-4">
      <div className="relative rounded-[36px] border border-white/10 bg-white/[0.04] shadow-[0_40px_120px_rgba(0,0,0,0.65)]">
        <div
          ref={scrollRef}
          className="h-[calc(100vh-320px)] w-full overflow-y-auto scroll-smooth px-4 py-6 sm:px-8"
        >
          <ReaderCanvas controller={controller} variant="immersive" />
        </div>
        <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black via-black/20 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-black via-black/40 to-transparent" />
        <div className="absolute left-6 top-6 rounded-full border border-white/20 bg-black/60 px-4 py-1 text-xs uppercase tracking-[0.4em] text-white/70">
          Page {page ? page.page_index + 1 : "-"} / {controller.pages.length || 1}
        </div>
        <div className="absolute inset-x-0 bottom-4 px-4 sm:px-8">
          <PlaybackControls controller={controller} variant="overlay" />
        </div>
      </div>
    </div>
  );
}

