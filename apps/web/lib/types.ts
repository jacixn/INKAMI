export type BubbleType = "dialogue" | "narration" | "thought" | "sfx";

export interface WordTiming {
  word: string;
  start: number;
  end: number;
}

export interface BubbleItem {
  bubble_id: string;
  panel_box: [number, number, number, number];
  bubble_box: [number, number, number, number];
  type: BubbleType;
  speaker_id: string;
  speaker_name?: string;
  voice_id: string;
  text: string;
  audio_url: string;
  word_times: WordTiming[];
}

export interface PagePayload {
  page_index: number;
  image_url: string;
  width?: number | null;
  height?: number | null;
  items: BubbleItem[];
  reading_order: string[];
}

export interface ChapterPayload {
  chapter_id: string;
  status: "processing" | "ready" | "failed";
  progress: number;
  title?: string;
  pages: PagePayload[];
  processing_mode: "bring_to_life" | "narrate";
}

export interface PlaybackController {
  chapterId: string;
  pages: PagePayload[];
  currentPageIndex: number;
  currentBubbleId?: string;
  isPlaying: boolean;
  speed: number;
  errors: string[];
  selectPage: (index: number) => void;
  play: () => void;
  pause: () => void;
  nextBubble: () => void;
  prevBubble: () => void;
  setSpeed: (value: number) => void;
  setBubble: (bubbleId: string) => void;
  restart: () => void;
  loading?: boolean;
}

