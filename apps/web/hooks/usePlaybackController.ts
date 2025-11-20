"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import { apiBase, fetcher } from "@/lib/api";
import type { BubbleItem, ChapterPayload, PlaybackController } from "@/lib/types";

const NEXT_BUBBLE_DELAY_MS = 500;

function resolveAudioUrl(raw?: string): string | undefined {
  if (!raw) {
    return undefined;
  }
  if (raw.startsWith("data:")) {
    return raw;
  }

  try {
    const parsed = new URL(raw);
    if (
      parsed.protocol === "http:" &&
      parsed.hostname !== "localhost" &&
      parsed.hostname !== "127.0.0.1"
    ) {
      parsed.protocol = "https:";
      return parsed.toString();
    }
    return parsed.toString();
  } catch {
    const normalizedBase = apiBase.endsWith("/")
      ? apiBase.slice(0, -1)
      : apiBase;
    const suffix = raw.startsWith("/") ? raw : `/${raw}`;
    return `${normalizedBase}${suffix}`;
  }
}

interface ControllerState extends PlaybackController {
  loading: boolean;
  chapter?: ChapterPayload;
}

export function usePlaybackController(chapterId: string): ControllerState {
  const swrKey = chapterId ? `/api/chapters/${chapterId}` : null;
  const { data, isLoading, error } = useSWR<ChapterPayload>(swrKey, fetcher, {
    refreshInterval: 5000
  });

  const loading = chapterId ? isLoading : false;
  const networkError = error ? error.message : null;

  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [currentBubbleId, setCurrentBubbleId] = useState<string>();
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [errors, setErrors] = useState<string[]>([]);
  const audioRef = useRef<HTMLAudioElement>();
  const speechRef = useRef<SpeechSynthesisUtterance | null>(null);
  const nextBubbleRef = useRef<() => void>(() => {});

  const pages = data?.pages ?? [];
  const chapterReadingOrder = useMemo(() => {
    return pages.flatMap((page) => {
      if (page.reading_order?.length) {
        return page.reading_order;
      }
      return page.items.map((item) => item.bubble_id);
    });
  }, [pages]);

  useEffect(() => {
    if (!pages.length) return;
    if (currentPageIndex >= pages.length) {
      setCurrentPageIndex(0);
    }
  }, [pages.length, currentPageIndex]);

  const bubbleMap = useMemo(() => {
    const map = new Map<string, { pageIndex: number; bubble: BubbleItem }>();
    pages.forEach((page, idx) => {
      page.items.forEach((item) =>
        map.set(item.bubble_id, { pageIndex: idx, bubble: item })
      );
    });
    return map;
  }, [pages]);

  const currentPage = pages[currentPageIndex];
  useEffect(() => {
    if (currentBubbleId) return;
    const page = pages[currentPageIndex];
    if (!page) return;
    const fallback = page.reading_order?.[0] ?? page.items[0]?.bubble_id;
    if (fallback) {
      setCurrentBubbleId(fallback);
    }
  }, [pages, currentPageIndex, currentBubbleId]);

  useEffect(() => {
    if (!currentBubbleId) return;
    const target = bubbleMap.get(currentBubbleId);
    if (!target) {
      if (chapterReadingOrder.length) {
        setCurrentBubbleId(chapterReadingOrder[0]);
        setCurrentPageIndex(0);
      }
      return;
    }
    if (target.pageIndex !== currentPageIndex) {
      setCurrentPageIndex(target.pageIndex);
    }
  }, [bubbleMap, chapterReadingOrder, currentBubbleId, currentPageIndex]);

  useEffect(() => {
    setCurrentPageIndex(0);
    setCurrentBubbleId(undefined);
    setIsPlaying(false);
  }, [chapterId]);

  const cancelSpeech = useCallback(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    speechRef.current = null;
  }, []);

  const loadAudio = useCallback(
    async (bubbleId?: string) => {
      if (!bubbleId) return;
      const target = bubbleMap.get(bubbleId);
      if (!target) return;

      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = undefined;
      }
      cancelSpeech();

      const scheduleNext = () => {
        const gap = Math.max(
          250,
          Math.round(NEXT_BUBBLE_DELAY_MS / Math.max(speed, 0.5))
        );
        if (typeof window === "undefined") {
          nextBubbleRef.current();
          return;
        }
        window.setTimeout(() => nextBubbleRef.current(), gap);
      };

      const startSpeechPlayback = () => {
        if (
          typeof window === "undefined" ||
          !("speechSynthesis" in window) ||
          !target.bubble.text.trim()
        ) {
          return false;
        }
        const utterance = new SpeechSynthesisUtterance(target.bubble.text);
        utterance.rate = speed;
        utterance.onend = () => {
          speechRef.current = null;
          setIsPlaying(false);
          scheduleNext();
        };
        utterance.onerror = (event) => {
          speechRef.current = null;
          setErrors((prev) => [
            ...prev,
            event.error ?? `Speech playback failed for ${bubbleId}`
          ]);
          setIsPlaying(false);
        };
        speechRef.current = utterance;
        window.speechSynthesis.speak(utterance);
        setIsPlaying(true);
        return true;
      };

      const resolvedUrl = resolveAudioUrl(target.bubble.audio_url);

      if (!resolvedUrl) {
        if (!startSpeechPlayback()) {
          setErrors((prev) => [...prev, `Missing audio for ${bubbleId}`]);
          setIsPlaying(false);
        }
        return;
      }

      const audio = new Audio(resolvedUrl);
      audio.crossOrigin = "anonymous";
      audio.playbackRate = speed;
      audio.onended = () => {
        setIsPlaying(false);
        scheduleNext();
      };
      audio.onerror = () => {
        audioRef.current = undefined;
        const fallbackWorked = startSpeechPlayback();
        setErrors((prev) => [
          ...prev,
          `Audio failed for ${bubbleId}${fallbackWorked ? ", using device voice." : ""}`
        ]);
        if (!fallbackWorked) {
          setIsPlaying(false);
        }
      };

      audioRef.current = audio;
      try {
        await audio.play();
        setIsPlaying(true);
      } catch (err) {
        audioRef.current = undefined;
        const fallbackWorked = startSpeechPlayback();
        setErrors((prev) => [
          ...prev,
          err instanceof Error ? err.message : "Playback failed"
        ]);
        if (!fallbackWorked) {
          setIsPlaying(false);
        }
      }
    },
    [bubbleMap, speed, cancelSpeech]
  );

  const setBubble = useCallback(
    (bubbleId: string) => {
      const target = bubbleMap.get(bubbleId);
      if (!target) return;
      setCurrentPageIndex(target.pageIndex);
      setCurrentBubbleId(bubbleId);
      if (isPlaying) {
        loadAudio(bubbleId);
      }
    },
    [bubbleMap, isPlaying, loadAudio]
  );

  const selectPage = useCallback(
    (index: number) => {
      setCurrentPageIndex(index);
      const page = pages[index];
      if (!page) return;
      const fallback = page.reading_order?.[0] ?? page.items[0]?.bubble_id;
      if (!fallback) return;
      setCurrentBubbleId(fallback);
      cancelSpeech();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = undefined;
      }
      if (isPlaying) {
        void loadAudio(fallback);
      } else {
        setIsPlaying(false);
      }
    },
    [cancelSpeech, isPlaying, loadAudio, pages]
  );

  const play = useCallback(() => {
    if (!currentBubbleId) {
      const firstBubble = chapterReadingOrder[0];
      if (firstBubble) {
        setCurrentBubbleId(firstBubble);
        void loadAudio(firstBubble);
        return;
      }
    }
    if (currentBubbleId) {
      void loadAudio(currentBubbleId);
    }
  }, [chapterReadingOrder, currentBubbleId, loadAudio]);

  const pause = useCallback(() => {
    cancelSpeech();
    audioRef.current?.pause();
    audioRef.current = undefined;
    setIsPlaying(false);
  }, [cancelSpeech]);

  const advanceBubble = useCallback(
    (autoPlay: boolean) => {
      if (!chapterReadingOrder.length) return;
      const index = chapterReadingOrder.findIndex((id) => id === currentBubbleId);
      let nextId: string | undefined;
      if (index >= 0 && index + 1 < chapterReadingOrder.length) {
        nextId = chapterReadingOrder[index + 1];
      } else if (index < 0) {
        nextId = chapterReadingOrder[0];
      } else if (!autoPlay) {
        nextId = chapterReadingOrder[0];
      }
      if (nextId) {
        setCurrentBubbleId(nextId);
        if (autoPlay || isPlaying) {
          void loadAudio(nextId);
        }
      } else if (autoPlay) {
        setIsPlaying(false);
      }
    },
    [chapterReadingOrder, currentBubbleId, isPlaying, loadAudio]
  );

  const nextBubble = useCallback(() => advanceBubble(false), [advanceBubble]);

  const prevBubble = useCallback(() => {
    if (!chapterReadingOrder.length) return;
    const index = chapterReadingOrder.findIndex((id) => id === currentBubbleId);
    let prevId: string | undefined;
    if (index > 0) {
      prevId = chapterReadingOrder[index - 1];
    } else if (index === 0) {
      prevId = chapterReadingOrder[chapterReadingOrder.length - 1];
    } else {
      prevId = chapterReadingOrder[0];
    }
    if (prevId) {
      setCurrentBubbleId(prevId);
      if (isPlaying) {
        void loadAudio(prevId);
      }
    }
  }, [chapterReadingOrder, currentBubbleId, isPlaying, loadAudio]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  }, [speed]);

  useEffect(() => {
    nextBubbleRef.current = () => advanceBubble(true);
  }, [advanceBubble]);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      cancelSpeech();
    };
  }, [cancelSpeech]);

  const restart = useCallback(() => {
    if (!pages.length) return;
    const firstBubbleId = chapterReadingOrder[0];
    if (!firstBubbleId) return;
    const target = bubbleMap.get(firstBubbleId);
    if (target) {
      setCurrentPageIndex(target.pageIndex);
    } else {
      setCurrentPageIndex(0);
    }
    setCurrentBubbleId(firstBubbleId);
    cancelSpeech();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = undefined;
    }
    void loadAudio(firstBubbleId);
  }, [bubbleMap, cancelSpeech, chapterReadingOrder, loadAudio, pages]);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  const combinedErrors = networkError ? [networkError, ...errors] : errors;

  return {
    chapterId,
    pages,
    currentPageIndex,
    currentBubbleId,
    isPlaying,
    speed,
    errors: combinedErrors,
    selectPage,
    play,
    pause,
    nextBubble,
    prevBubble,
    setSpeed,
    setBubble,
    restart,
    clearErrors,
    loading,
    chapter: data
  };
}

