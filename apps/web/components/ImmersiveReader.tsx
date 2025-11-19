"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";

import { cn } from "@/lib/utils";
import type { PlaybackController } from "@/lib/types";

import ReaderCanvas from "./ReaderCanvas";
import PlaybackControls from "./PlaybackControls";

interface ImmersiveReaderProps {
  controller: PlaybackController;
}

const BASE_CANVAS_HEIGHT = 1920;
const AUTO_HIDE_DELAY_MS = 5000;

// Custom smooth scroll helper
function smoothScrollTo(element: HTMLElement, target: number, duration: number) {
  const start = element.scrollTop;
  const distance = target - start;
  const startTime = performance.now();

  function step(currentTime: number) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // EaseInOutQuad
    const ease = progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;

    element.scrollTop = start + distance * ease;

    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);
}

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
    if (!scrollRef.current || !activeBubble || !page || !page.height) return;
    const container = scrollRef.current;
    const scale = container.scrollHeight / page.height;
    const target = Math.max(
      activeBubble.bubble_box[1] * scale - container.clientHeight / 3,
      0
    );
    
    // Use custom smooth scroll with 1000ms duration
    smoothScrollTo(container, target, 1000);
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
        } else {
           setIsFullscreen(false); // Fallback exit
        }
      } else {
        if (element.requestFullscreen) {
           await element.requestFullscreen();
        } else {
           // Fallback enter (iOS Safari)
           setIsFullscreen(true);
           setControlsVisible(true);
           scheduleHideControls();
        }
      }
    } catch (error) {
      console.warn("Fullscreen API failed, using CSS fallback", error);
      // Fallback if API throws (e.g. user denied, unsupported)
      setIsFullscreen((prev) => !prev);
      setControlsVisible(true);
      scheduleHideControls();
    }
  }, [scheduleHideControls]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const onChange = () => {
      const active = document.fullscreenElement === fullscreenRef.current;
      // Only update if the API actually changed state (to avoid overriding fallback)
      // But if API is used, we want to sync. 
      // If we used fallback, document.fullscreenElement is null, so this might force it to false.
      // We need to be careful.
      if (document.fullscreenElement) {
         setIsFullscreen(true);
         setControlsVisible(true);
         scheduleHideControls();
      } else {
         // Only force false if we are NOT in fallback mode? 
         // Actually, relying on the event is tricky if we mix modes.
         // Let's assume if the event fires, we trust it. 
         // But for iOS, this event won't fire.
         // For desktop "Esc", it will fire.
         if (active) {
             setIsFullscreen(true);
             setControlsVisible(true);
             scheduleHideControls();
         } else {
             // If we exited standard fullscreen, turn off state
             // But what if we are in fallback mode and nothing changed?
             // The event only fires on change.
             setIsFullscreen(false);
             clearHideTimer();
         }
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
    "w-full overflow-y-auto px-4 py-6 sm:px-8 no-scrollbar", // removed scroll-smooth to rely on JS
    isFullscreen ? "h-screen" : "h-[calc(100vh-320px)]"
  );
  const containerClasses = cn(
    "relative rounded-[36px] border border-white/10 bg-white/[0.04] shadow-[0_40px_120px_rgba(0,0,0,0.65)]",
    isFullscreen && "fixed inset-0 z-50 h-screen w-full rounded-none border-none bg-black"
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
        <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black/80 to-transparent opacity-60" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/90 to-transparent opacity-80" />
        
        {!isFullscreen && page && (
          <div className="absolute right-6 top-6 rounded-full border border-white/10 bg-black/40 px-3 py-1 text-xs font-medium text-white/60 backdrop-blur">
            {controller.currentPageIndex + 1} / {controller.pages.length}
          </div>
        )}

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
