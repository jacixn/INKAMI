import { z } from "zod";

export const wordTimingSchema = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number()
});

export const bubbleSchema = z.object({
  bubble_id: z.string(),
  panel_box: z.array(z.number()).length(4),
  bubble_box: z.array(z.number()).length(4),
  type: z.enum(["dialogue", "narration", "thought", "sfx"]),
  speaker_id: z.string(),
  speaker_name: z.string().optional(),
  voice_id: z.string(),
  text: z.string(),
  audio_url: z.string().url(),
  word_times: z.array(wordTimingSchema)
});

export const pageSchema = z.object({
  page_index: z.number(),
  image_url: z.string().url(),
  items: z.array(bubbleSchema),
  reading_order: z.array(z.string())
});

export const chapterSchema = z.object({
  chapter_id: z.string(),
  status: z.enum(["processing", "ready", "failed"]),
  progress: z.number().min(0).max(100),
  pages: z.array(pageSchema),
  title: z.string().optional()
});

export type WordTiming = z.infer<typeof wordTimingSchema>;
export type Bubble = z.infer<typeof bubbleSchema>;
export type Page = z.infer<typeof pageSchema>;
export type Chapter = z.infer<typeof chapterSchema>;

