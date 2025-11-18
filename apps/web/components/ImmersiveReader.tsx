"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import type { PlaybackController } from "@/lib/types";
import ReaderCanvas from "./ReaderCanvas";
import PlaybackControls from "./PlaybackControls";

interface ImmersiveReaderProps {
  controller: PlaybackController & { loading: boolean };
}

const BASE_CANVAS_HEIGHT = 1920;
const AUTO_HIDE_DELAY_MS = 5000;

export default function ImmersiveReader({ controller }: ImmersiveReaderProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const fullscreenRef = useRef<HTMLDivElement>(null);
  const hideTimerRef = useRef<number | null>(null);

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);

  const page = controller.pages[controller.currentPageIndex];

  const activeBubble = useMemo(() => {
    if (!page) return undefined;
    return page.items.find((item) => item.bubble_id === controller.currentBubbleId);
  }, [page, controller.currentBubbleId]);

  useEffect(() => {
    if (!scrollRef.current || !activeBubble || !page) return;
    const container = scrollRef.current;
    const baseHeight =
      page && page.height && page.height > 0 ? page.height : BASE_CANVAS_HEIGHT;
    const scale = container.scrollHeight / baseHeight;
    
    // Calculate bubble center position
    const bubbleTop = activeBubble.bubble_box[1] * scale;
    const bubbleBottom = activeBubble.bubble_box[3] * scale;
    const bubbleCenter = (bubbleTop + bubbleBottom) / 2;
    
    // Center the bubble in the viewport
    const viewportCenter = container.clientHeight / 2;
    const target = Math.max(
      bubbleCenter - viewportCenter,
      0
    );
    
    // Custom smooth scroll with longer duration for a more relaxed, enjoyable experience
    const smoothScrollTo = (element: HTMLElement, target: number, duration: number = 1200) => {
      const start = element.scrollTop;
      const distance = target - start;
      const startTime = performance.now();
      
      // Easing function for smooth deceleration (ease-out)
      const easeOutCubic = (t: number): number => {
        return 1 - Math.pow(1 - t, 3);
      };
      
      const animateScroll = (currentTime: number) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = easeOutCubic(progress);
        
        element.scrollTop = start + distance * eased;
        
        if (progress < 1) {
          requestAnimationFrame(animateScroll);
        }
      };
      
      requestAnimationFrame(animateScroll);
    };
    
    // Small delay to let current bubble finish before scrolling
    const timeoutId = setTimeout(() => {
      smoothScrollTo(container, target, 1200); // 1.2 second smooth scroll
    }, 150);
    
    return () => {
      clearTimeout(timeoutId);
    };
  }, [activeBubble, controller.currentPageIndex, page]);

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current) {
      window.clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const scheduleHideControls = useCallback(() => {
    clearHideTimer();
    if (!isFullscreen) return;
    hideTimerRef.current = window.setTimeout(() => {
      setControlsVisible(false);
    }, AUTO_HIDE_DELAY_MS);
  }, [clearHideTimer, isFullscreen]);

  const showControls = useCallback(() => {
    setControlsVisible(true);
    if (isFullscreen) {
      scheduleHideControls();
    }
  }, [isFullscreen, scheduleHideControls]);

  const handleUserActivity = useCallback(() => {
    if (!isFullscreen) return;
    showControls();
  }, [isFullscreen, showControls]);

  const toggleFullscreen = useCallback(async () => {
    if (typeof document === "undefined") return;
    const element = fullscreenRef.current;
    if (!element) return;
    try {
      if (document.fullscreenElement === element) {
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        }
      } else {
        await element.requestFullscreen();
      }
    } catch (error) {
      console.error("Failed to toggle fullscreen", error);
    }
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const onChange = () => {
      const active = document.fullscreenElement === fullscreenRef.current;
      setIsFullscreen(active);
      setControlsVisible(true);
      if (active) {
        scheduleHideControls();
      } else {
        clearHideTimer();
      }
    };
    document.addEventListener("fullscreenchange", onChange);
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
    };
  }, [clearHideTimer, scheduleHideControls]);

  useEffect(() => {
    return () => {
      clearHideTimer();
    };
  }, [clearHideTimer]);

  const controlsHidden = isFullscreen && !controlsVisible;
  const scrollClasses = cn(
    "w-full overflow-y-auto scroll-smooth px-4 py-6 sm:px-8",
    isFullscreen ? "h-screen" : "h-[calc(100vh-320px)]",
    "[scroll-behavior:smooth]"
  );
  const containerClasses = cn(
    "relative rounded-[36px] border border-white/10 bg-white/[0.04] shadow-[0_40px_120px_rgba(0,0,0,0.65)]",
    isFullscreen && "z-50 h-screen w-full rounded-none border-none bg-black"
  );

  return (
    <div className="space-y-4">
      <div
        ref={fullscreenRef}
        className={containerClasses}
        onPointerMove={handleUserActivity}
        onClick={handleUserActivity}
      >
        <div ref={scrollRef} className={scrollClasses}>
          <ReaderCanvas
            controller={controller}
            variant="immersive"
            isFullscreen={isFullscreen}
          />
        </div>
        <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black via-black/20 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-black via-black/40 to-transparent" />
        <div
          className={cn(
            "absolute left-6 top-6 rounded-full border border-white/20 bg-black/60 px-4 py-1 text-xs uppercase tracking-[0.4em] text-white/70 transition-opacity",
            controlsHidden ? "opacity-0" : "opacity-100"
          )}
        >
          Page {page ? page.page_index + 1 : "-"} / {controller.pages.length || 1}
        </div>
        <div
          className={cn(
            "absolute inset-x-0 bottom-4 px-4 transition-opacity duration-300 sm:px-8",
            controlsHidden ? "pointer-events-none opacity-0" : "opacity-100"
          )}
        >
          <PlaybackControls
            controller={controller}
            variant="overlay"
            onToggleFullscreen={toggleFullscreen}
            isFullscreen={isFullscreen}
            onRestart={controller.restart}
          />
        </div>
      </div>
    </div>
  );
}

