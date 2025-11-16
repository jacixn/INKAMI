"use client";

import ProcessingStatus from "@/components/ProcessingStatus";

const FALLBACK_CHAPTER_ID = "demo";

function getChapterId(value?: string | string[]): string {
  if (!value) return FALLBACK_CHAPTER_ID;
  const normalized = Array.isArray(value) ? value[0] : value;
  const trimmed = normalized?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : FALLBACK_CHAPTER_ID;
}

interface ChapterStatusPageProps {
  searchParams?: {
    id?: string | string[];
  };
}

export default function ChapterStatusPage({
  searchParams
}: ChapterStatusPageProps) {
  const chapterId = getChapterId(searchParams?.id);

  return (
    <div className="space-y-6">
      <ProcessingStatus chapterId={chapterId} />
    </div>
  );
}
