import "@/styles/globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

import Aurora from "@/components/Aurora";
import AppShell from "@/components/AppShell";
import { cn } from "@/lib/utils";
import { bodyFont, headingFont } from "./fonts";

export const metadata: Metadata = {
  title: "INKAMI | AI Manga Narrator",
  description:
    "Upload manga or manhwa chapters and listen with adaptive AI voices."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        className={cn(
          bodyFont.variable,
          headingFont.variable,
          "relative min-h-screen bg-[#03030a] text-white antialiased"
        )}
      >
        <Aurora />
        <div className="relative mx-auto max-w-6xl">
          <AppShell>{children}</AppShell>
        </div>
      </body>
    </html>
  );
}
