"use client";

import ProcessingStatus from "@/components/ProcessingStatus";
import { useParams } from "next/navigation";

export default function ChapterStatusPage() {
  const params = useParams<{ chapterId: string }>();

  return (
    <div className="space-y-6">
      <ProcessingStatus chapterId={params.chapterId} />
    </div>
  );
}

