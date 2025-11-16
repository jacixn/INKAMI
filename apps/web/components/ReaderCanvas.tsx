"use client";

import Image from "next/image";
import type { PlaybackController } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  controller: PlaybackController & { loading: boolean };
}

export default function ReaderCanvas({ controller }: Props) {
  const page = controller.pages[controller.currentPageIndex];

  if (!page) {
    return (
      <section className="card h-[600px] items-center justify-center text-center text-ink-100">
        {controller.loading ? "Loading chapter..." : "No pages loaded yet."}
      </section>
    );
  }

  return (
    <section className="card">
      <header className="mb-4 flex items-center gap-4 text-sm text-ink-100">
        <span>Page {page.page_index + 1}</span>
        <div className="flex gap-2">
          {controller.pages.map((_, index) => (
            <button
              key={index}
              className={cn(
                "h-2 w-6 rounded-full bg-white/10 transition",
                index === controller.currentPageIndex && "bg-white"
              )}
              onClick={() => controller.selectPage(index)}
              aria-label={`Go to page ${index + 1}`}
            />
          ))}
        </div>
      </header>
      <div className="relative mx-auto aspect-[9/16] w-full max-w-[520px] overflow-hidden rounded-xl bg-black/60">
        <Image
          src={page.image_url}
          alt={`Page ${page.page_index + 1}`}
          fill
          sizes="520px"
          className="object-contain"
        />
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1080 1920">
          {page.items.map((item) => {
            const [x1, y1, x2, y2] = item.bubble_box;
            const width = x2 - x1;
            const height = y2 - y1;
            const active = item.bubble_id === controller.currentBubbleId;

            return (
              <g
                key={item.bubble_id}
                onClick={() => controller.setBubble(item.bubble_id)}
                className="cursor-pointer"
              >
                <rect
                  x={x1}
                  y={y1}
                  width={width}
                  height={height}
                  fill={active ? "rgba(255,255,255,0.08)" : "transparent"}
                  stroke={active ? "#8b9bff" : "rgba(255,255,255,0.35)"}
                  strokeWidth={active ? 3 : 1}
                  rx={8}
                />
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}

