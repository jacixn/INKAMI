"use client";

import Image from "next/image";
import type { PlaybackController } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  controller: PlaybackController & { loading: boolean };
  variant?: "default" | "immersive";
}

export default function ReaderCanvas({ controller, variant = "default" }: Props) {
  const page = controller.pages[controller.currentPageIndex];
  const immersive = variant === "immersive";

  if (!page) {
    return (
      <section
        className={cn(
          "h-[600px] items-center justify-center text-center text-ink-100",
          immersive ? "rounded-[32px] border border-white/10 bg-black/30" : "card"
        )}
      >
        {controller.loading ? "Loading chapter..." : "No pages loaded yet."}
      </section>
    );
  }

  const viewWidth = page.width && page.width > 0 ? page.width : 1080;
  const viewHeight = page.height && page.height > 0 ? page.height : 1920;
  const aspectRatio = viewWidth / viewHeight;

  return (
    <section className={cn(immersive ? "" : "card")}>
      {!immersive && (
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
      )}
      <div
        className={cn(
          "relative mx-auto w-full overflow-hidden rounded-[28px] border border-white/10 bg-black/60",
          immersive ? "max-w-[720px]" : "max-w-[520px]"
        )}
        style={{ aspectRatio }}
      >
        <Image
          src={page.image_url}
          alt={`Page ${page.page_index + 1}`}
          fill
          sizes="(min-width: 768px) 520px, 90vw"
          className="object-contain"
        />
        <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 ${viewWidth} ${viewHeight}`}>
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
                  fill="transparent"
                  stroke="transparent"
                  strokeWidth={1}
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

