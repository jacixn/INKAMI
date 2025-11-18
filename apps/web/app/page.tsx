import Link from "next/link";

import FeatureMarquee from "@/components/FeatureMarquee";
import LiveNarrationMock from "@/components/LiveNarrationMock";
import StatsRibbon from "@/components/StatsRibbon";
import UploadSteps from "@/components/UploadSteps";
import VoiceGallery from "@/components/VoiceGallery";

const heroHighlights = [
  "Panel → bubble → speaker pipeline",
  "Word-level highlighting",
  "Realtime voice swaps"
];

export default function Home() {
  return (
    <div className="space-y-12">
      <section className="glass-panel relative overflow-hidden p-8">
        <div className="absolute inset-0 bg-gradient-to-tr from-fuchsia-500/10 via-transparent to-sky-500/10" />
        <div className="relative z-10 space-y-6">
          <p className="text-xs uppercase tracking-[0.5em] text-white/60">
            Inkami
          </p>
          <h1 className="text-4xl font-semibold text-white md:text-6xl">
            Manga that{" "}
            <span className="bg-gradient-to-r from-sky-300 via-purple-300 to-rose-200 bg-clip-text text-transparent">
              reads itself aloud
            </span>{" "}
            while you watch.
          </h1>
          <p className="max-w-3xl text-lg text-white/70">
            Upload a chapter, wait about a minute, then hit play. Panels, speech bubbles,
            narrators and characters get assigned cinematic voices automatically. The reader
            highlights each bubble karaoke-style while realistic AI voices perform the script.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link
              href="/upload"
              className="rounded-full bg-white px-6 py-3 text-sm font-semibold text-black shadow-lg shadow-purple-500/40 transition hover:translate-y-0.5"
            >
              Upload a chapter
            </Link>
            <Link
              href="/chapters"
              className="rounded-full border border-white/30 px-6 py-3 text-sm font-semibold text-white/80"
            >
              View chapter status
            </Link>
          </div>
          <div className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.3em] text-white/50">
            {heroHighlights.map((highlight) => (
              <span
                key={highlight}
                className="rounded-full border border-white/10 px-4 py-1 text-white/70"
              >
                {highlight}
              </span>
            ))}
          </div>
        </div>
      </section>

      <StatsRibbon />

      <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <LiveNarrationMock />
        <UploadSteps />
      </div>

      <FeatureMarquee />
      <VoiceGallery />
    </div>
  );
}

