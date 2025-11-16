"use client";

import UploadWizard from "@/components/UploadWizard";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <header className="glass-panel space-y-3 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-white/60">
          Upload
        </p>
        <h1 className="text-3xl font-semibold text-white">Chapter Intake</h1>
        <p className="text-white/70">
          Drop a ZIP/PDF of a manga or manhwa chapter. We split pages, detect panels,
          read text, assign speakers, and render adaptive voices automatically.
        </p>
      </header>
      <UploadWizard />
    </div>
  );
}

