"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { BubbleItem, ChapterPayload, PlaybackController } from "@/lib/types";

const NEXT_BUBBLE_DELAY_MS = 500;

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
  const readingOrder = currentPage?.reading_order ?? [];

  useEffect(() => {
    const page = pages[currentPageIndex];
    if (!page) return;
    const valid = page.items.some((item) => item.bubble_id === currentBubbleId);
    if (!valid) {
      const fallback = page.reading_order?.[0] ?? page.items[0]?.bubble_id;
      if (fallback) {
        setCurrentBubbleId(fallback);
      }
    }
  }, [pages, currentPageIndex, currentBubbleId]);

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

      const shouldUseSpeech =
        (!target.bubble.audio_url || target.bubble.audio_url.trim() === "") &&
        typeof window !== "undefined" &&
        "speechSynthesis" in window;

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

      if (shouldUseSpeech) {
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
        return;
      }

      const audio = new Audio(target.bubble.audio_url);
      audio.playbackRate = speed;
      audio.onended = () => {
        setIsPlaying(false);
        scheduleNext();
      };
      audio.onerror = () => {
        setErrors((prev) => [...prev, `Audio failed for ${bubbleId}`]);
        setIsPlaying(false);
      };

      audioRef.current = audio;
      try {
        await audio.play();
        setIsPlaying(true);
      } catch (err) {
        setErrors((prev) => [
          ...prev,
          err instanceof Error ? err.message : "Playback failed"
        ]);
        setIsPlaying(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [bubbleMap, speed]
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

  const play = useCallback(() => {
    if (!currentBubbleId) {
      const firstBubble = readingOrder[0];
      if (firstBubble) {
        setCurrentBubbleId(firstBubble);
        void loadAudio(firstBubble);
        return;
      }
    }
    void loadAudio(currentBubbleId);
  }, [currentBubbleId, loadAudio, readingOrder]);

  const pause = useCallback(() => {
    cancelSpeech();
    audioRef.current?.pause();
    audioRef.current = undefined;
    setIsPlaying(false);
  }, [cancelSpeech]);

  const advanceBubble = useCallback(
    (autoPlay: boolean) => {
      if (!readingOrder.length) return;
      const index = readingOrder.findIndex((id) => id === currentBubbleId);
      const nextId =
        index >= 0 && index + 1 < readingOrder.length
          ? readingOrder[index + 1]
          : index < 0
            ? readingOrder[0]
            : undefined;
      if (nextId) {
        setCurrentBubbleId(nextId);
        if (autoPlay || isPlaying) {
          void loadAudio(nextId);
        }
      } else if (autoPlay) {
        setIsPlaying(false);
      }
    },
    [currentBubbleId, isPlaying, loadAudio, readingOrder]
  );

  const nextBubble = useCallback(() => advanceBubble(false), [advanceBubble]);

  const prevBubble = useCallback(() => {
    if (!readingOrder.length) return;
    const index = readingOrder.findIndex((id) => id === currentBubbleId);
    const prevId =
      index > 0 ? readingOrder[index - 1] : readingOrder[readingOrder.length - 1];
    if (prevId) {
      setCurrentBubbleId(prevId);
      if (isPlaying) {
        void loadAudio(prevId);
      }
    }
  }, [currentBubbleId, isPlaying, loadAudio, readingOrder]);

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
    const firstPage = pages[0];
    const firstBubbleId =
      firstPage.reading_order?.[0] ?? firstPage.items[0]?.bubble_id;
    if (!firstBubbleId) return;
    setCurrentPageIndex(0);
    setCurrentBubbleId(firstBubbleId);
    cancelSpeech();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = undefined;
    }
    void loadAudio(firstBubbleId);
  }, [cancelSpeech, loadAudio, pages]);

  const combinedErrors = networkError ? [networkError, ...errors] : errors;

  return {
    chapterId,
    pages,
    currentPageIndex,
    currentBubbleId,
    isPlaying,
    speed,
    errors: combinedErrors,
    selectPage: setCurrentPageIndex,
    play,
    pause,
    nextBubble,
    prevBubble,
    setSpeed,
    setBubble,
    restart,
    loading,
    chapter: data
  };
}

