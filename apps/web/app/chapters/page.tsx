"use client";

import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import ProcessingStatus from "@/components/ProcessingStatus";

const FALLBACK_CHAPTER_ID = "demo";

function getChapterId(value?: string | null): string {
  if (!value) return FALLBACK_CHAPTER_ID;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : FALLBACK_CHAPTER_ID;
}

function ChapterStatusContent() {
  const searchParams = useSearchParams();

  const chapterId = useMemo(() => {
    return getChapterId(searchParams?.get("id"));
  }, [searchParams]);

  return (
    <div className="space-y-6">
      <ProcessingStatus chapterId={chapterId} />
    </div>
  );
}

export default function ChapterStatusPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <ProcessingStatus chapterId={FALLBACK_CHAPTER_ID} />
        </div>
      }
    >
      <ChapterStatusContent />
    </Suspense>
  );
}
