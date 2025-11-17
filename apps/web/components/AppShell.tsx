"use client";

import { ReactNode } from "react";

import BottomNav from "./BottomNav";
import TopBar from "./TopBar";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col px-4 pb-32 pt-6 md:px-6 lg:px-8">
      <TopBar />
      <main className="flex-1 pb-8">{children}</main>
      <BottomNav />
    </div>
  );
}

