"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { BubbleItem, ChapterPayload, PlaybackController } from "@/lib/types";

const demoChapter: ChapterPayload = {
  chapter_id: "demo",
  title: "Demo Chapter",
  status: "ready",
  progress: 100,
  pages: [
    {
      page_index: 0,
      image_url:
        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80",
      items: [
        {
          bubble_id: "demo-bubble-1",
          panel_box: [60, 80, 1020, 1820],
          bubble_box: [140, 260, 640, 560],
          type: "dialogue",
          speaker_id: "heroine",
          speaker_name: "Lumen",
          voice_id: "voice_friendly_f",
          text: "We turned this entire chapter into audio in under one minute.",
          audio_url:
            "https://cdn.pixabay.com/download/audio/2022/03/12/audio_263318cc46.mp3?filename=glow-ambient-11046.mp3",
          word_times: [
            { word: "We", start: 0, end: 0.35 },
            { word: "turned", start: 0.35, end: 0.75 },
            { word: "this", start: 0.75, end: 1.0 },
            { word: "entire", start: 1.0, end: 1.4 },
            { word: "chapter", start: 1.4, end: 1.9 },
            { word: "into", start: 1.9, end: 2.2 },
            { word: "audio", start: 2.2, end: 2.6 },
            { word: "in", start: 2.6, end: 2.7 },
            { word: "under", start: 2.7, end: 3.0 },
            { word: "one", start: 3.0, end: 3.2 },
            { word: "minute.", start: 3.2, end: 3.7 }
          ]
        },
        {
          bubble_id: "demo-bubble-2",
          panel_box: [60, 80, 1020, 1820],
          bubble_box: [420, 780, 920, 1040],
          type: "narration",
          speaker_id: "narrator",
          speaker_name: "Oracle",
          voice_id: "voice_narrator",
          text: "Inkami understands panels, characters, and emotion to pick the right voice.",
          audio_url:
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_7a93ce2c98.mp3?filename=mysterious-cinematic-11097.mp3",
          word_times: [
            { word: "Inkami", start: 0, end: 0.6 },
            { word: "understands", start: 0.6, end: 1.2 },
            { word: "panels,", start: 1.2, end: 1.5 },
            { word: "characters,", start: 1.5, end: 2.0 },
            { word: "and", start: 2.0, end: 2.2 },
            { word: "emotion", start: 2.2, end: 2.7 },
            { word: "to", start: 2.7, end: 2.9 },
            { word: "pick", start: 2.9, end: 3.1 },
            { word: "the", start: 3.1, end: 3.25 },
            { word: "right", start: 3.25, end: 3.45 },
            { word: "voice.", start: 3.45, end: 3.9 }
          ]
        }
      ],
      reading_order: ["demo-bubble-1", "demo-bubble-2"]
    },
    {
      page_index: 1,
      image_url:
        "https://images.unsplash.com/photo-1472457897821-70d3819a0e24?auto=format&fit=crop&w=900&q=80",
      items: [
        {
          bubble_id: "demo-bubble-3",
          panel_box: [40, 120, 1030, 1850],
          bubble_box: [160, 360, 620, 580],
          type: "dialogue",
          speaker_id: "rival",
          speaker_name: "Kaze",
          voice_id: "voice_brash_m",
          text: "Tap any bubble and I will replay it instantly.",
          audio_url:
            "https://cdn.pixabay.com/download/audio/2021/08/08/audio_64cc85ee06.mp3?filename=futuristic-beat-9736.mp3",
          word_times: [
            { word: "Tap", start: 0, end: 0.35 },
            { word: "any", start: 0.35, end: 0.55 },
            { word: "bubble", start: 0.55, end: 0.9 },
            { word: "and", start: 0.9, end: 1.1 },
            { word: "I", start: 1.1, end: 1.2 },
            { word: "will", start: 1.2, end: 1.35 },
            { word: "replay", start: 1.35, end: 1.7 },
            { word: "it", start: 1.7, end: 1.85 },
            { word: "instantly.", start: 1.85, end: 2.4 }
          ]
        },
        {
          bubble_id: "demo-bubble-4",
          panel_box: [40, 120, 1030, 1850],
          bubble_box: [440, 880, 900, 1140],
          type: "narration",
          speaker_id: "narrator",
          speaker_name: "Oracle",
          voice_id: "voice_narrator",
          text: "Karaoke-style highlights stay synced with the audio stream.",
          audio_url:
            "https://cdn.pixabay.com/download/audio/2022/01/11/audio_1e0bd678ac.mp3?filename=deep-ambient-ambient-9947.mp3",
          word_times: [
            { word: "Karaoke-style", start: 0, end: 0.8 },
            { word: "highlights", start: 0.8, end: 1.3 },
            { word: "stay", start: 1.3, end: 1.55 },
            { word: "synced", start: 1.55, end: 1.9 },
            { word: "with", start: 1.9, end: 2.05 },
            { word: "the", start: 2.05, end: 2.15 },
            { word: "audio", start: 2.15, end: 2.45 },
            { word: "stream.", start: 2.45, end: 2.9 }
          ]
        }
      ],
      reading_order: ["demo-bubble-3", "demo-bubble-4"]
    }
  ]
};

interface ControllerState extends PlaybackController {
  loading: boolean;
  chapter?: ChapterPayload;
}

export function usePlaybackController(chapterId: string): ControllerState {
  const isDemo = chapterId === "demo";
  const swrKey = !isDemo && chapterId ? `/api/chapters/${chapterId}` : null;
  const { data, isLoading, error } = useSWR<ChapterPayload>(swrKey, fetcher, {
    refreshInterval: 5000
  });

  const chapterData = isDemo ? demoChapter : data;
  const loading = isDemo ? false : isLoading;
  const networkError = !isDemo && error ? error.message : null;

  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [currentBubbleId, setCurrentBubbleId] = useState<string>();
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [errors, setErrors] = useState<string[]>([]);
  const audioRef = useRef<HTMLAudioElement>();
  const speechRef = useRef<SpeechSynthesisUtterance | null>(null);
  const nextBubbleRef = useRef<() => void>(() => {});

  const pages = chapterData?.pages ?? [];

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

  const cancelSpeech = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    speechRef.current = null;
  };

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

      if (shouldUseSpeech) {
        const utterance = new SpeechSynthesisUtterance(target.bubble.text);
        utterance.rate = speed;
        utterance.onend = () => {
          speechRef.current = null;
          setIsPlaying(false);
          nextBubbleRef.current();
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
        nextBubbleRef.current();
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
  }, []);

  const nextBubble = useCallback(() => {
    if (!readingOrder.length) return;
    const index = readingOrder.findIndex((id) => id === currentBubbleId);
    const nextId = index >= 0 ? readingOrder[index + 1] : readingOrder[0];
    if (nextId) {
      setCurrentBubbleId(nextId);
      if (isPlaying) {
        void loadAudio(nextId);
      }
    }
  }, [currentBubbleId, isPlaying, loadAudio, readingOrder]);

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
    nextBubbleRef.current = () => nextBubble();
  }, [nextBubble]);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      cancelSpeech();
    };
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
    selectPage: setCurrentPageIndex,
    play,
    pause,
    nextBubble,
    prevBubble,
    setSpeed,
    setBubble,
    loading,
    chapter: chapterData
  };
}

