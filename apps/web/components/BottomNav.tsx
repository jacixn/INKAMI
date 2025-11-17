"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";

type AppRoute = Route<
  | "/"
  | "/upload"
  | "/reader"
  | "/chapters"
  | "/docs"
>;

type NavHref = AppRoute | { pathname: AppRoute; query?: Record<string, string> };

interface NavItem {
  label: string;
  href: NavHref;
  icon: (active: boolean) => JSX.Element;
}

const navItems: NavItem[] = [
  {
    label: "Listen",
    href: { pathname: "/reader", query: { id: "demo" } },
    icon: (active: boolean) => (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={active ? "text-white" : "text-white/60"}
      >
        <path
          d="M6.5 5v10l7-5-7-5Z"
          fill="currentColor"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinejoin="round"
        />
      </svg>
    )
  },
  {
    label: "Upload",
    href: "/upload",
    icon: (active: boolean) => (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={active ? "text-white" : "text-white/60"}
      >
        <path
          d="M10 4v12M4 10h12"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    )
  },
  {
    label: "Status",
    href: { pathname: "/chapters", query: { id: "demo" } },
    icon: (active: boolean) => (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={active ? "text-white" : "text-white/60"}
      >
        <path
          d="M5 12.5 8 9l3 3 4-5"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  },
  {
    label: "Home",
    href: "/",
    icon: (active: boolean) => (
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={active ? "text-white" : "text-white/60"}
      >
        <path
          d="M4 9.5 10 4l6 5.5V16a1 1 0 0 1-1 1h-4v-4H9v4H5a1 1 0 0 1-1-1V9.5Z"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinejoin="round"
        />
      </svg>
    )
  }
];

export default function BottomNav() {
  const pathname = usePathname() || "/";

  return (
    <nav className="pointer-events-none fixed inset-x-0 bottom-4 z-30 flex justify-center px-4">
      <div className="pointer-events-auto flex w-full max-w-md items-center justify-between rounded-[32px] border border-white/10 bg-black/60 px-4 py-3 shadow-[0_25px_60px_rgba(0,0,0,0.55)] backdrop-blur-xl">
        {navItems.map((item) => {
          const hrefPath =
            typeof item.href === "string"
              ? item.href.split("?")[0]
              : item.href.pathname ?? "/";
          const active =
            pathname === hrefPath ||
            (hrefPath !== "/" && pathname.startsWith(hrefPath));
          return (
            <Link
              key={item.label}
              href={item.href}
              className="flex flex-1 flex-col items-center gap-1 text-center text-[11px]"
            >
              {item.icon(active)}
              <span
                className={active ? "text-white font-semibold" : "text-white/60"}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

