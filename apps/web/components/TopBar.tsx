"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo } from "react";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Chapter Board", subtitle: "Home" },
  "/upload": { title: "New Intake", subtitle: "Upload" },
  "/reader": { title: "Immersive Mode", subtitle: "Reader" },
  "/chapters": { title: "Status Desk", subtitle: "Processing" },
  "/docs": { title: "Playbook", subtitle: "Docs" }
};

export default function TopBar() {
  const pathname = usePathname();
  const router = useRouter();

  const meta = useMemo(() => {
    if (!pathname) return titles["/"];
    const entry =
      titles[
        Object.keys(titles).find((key) =>
          pathname.startsWith(key === "/" ? key : `${key}`)
        ) ?? "/"
      ];
    return entry ?? titles["/"];
  }, [pathname]);

  const showBack = pathname !== "/";

  return (
    <header className="sticky top-4 z-30 mb-8">
      <div className="flex items-center justify-between rounded-[26px] border border-white/10 bg-black/30 px-4 py-3 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => (showBack ? router.back() : router.push("/"))}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/5 text-white/80 transition hover:border-white/40 hover:text-white"
            aria-label="Go back"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M8.5 3.5L5 7l3.5 3.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <div>
            <p className="text-[10px] uppercase tracking-[0.45em] text-white/50">
              {meta.subtitle}
            </p>
            <p className="text-lg font-semibold text-white">{meta.title}</p>
          </div>
        </div>
        <Link
          href="/upload"
          className="rounded-full border border-white/20 bg-gradient-to-r from-white/30 to-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-white/70 transition hover:border-white/40"
        >
          Inkami
        </Link>
      </div>
    </header>
  );
}

