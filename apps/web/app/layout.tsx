import "@/styles/globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

import Aurora from "@/components/Aurora";
import { bodyFont, headingFont } from "./fonts";
import { cn } from "@/lib/utils";

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
        <div className="relative mx-auto max-w-6xl px-4 pb-20 pt-10 md:px-6 lg:px-8">
          {children}
        </div>
      </body>
    </html>
  );
}

