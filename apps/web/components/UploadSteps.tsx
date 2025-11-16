const steps = [
  {
    title: "Drop your chapter",
    copy: "ZIP, PDF, or raw PNG/JPEG pages. We auto-split spreads.",
    accent: "bg-gradient-to-r from-pink-500 to-orange-400"
  },
  {
    title: "Vision + OCR",
    copy: "Panels, bubbles, box types, speaker cues in ~60s.",
    accent: "bg-gradient-to-r from-indigo-400 to-sky-400"
  },
  {
    title: "Voice cast",
    copy: "Character registry assigns ElevenLabs / Deepsick voices.",
    accent: "bg-gradient-to-r from-emerald-400 to-lime-300"
  },
  {
    title: "Karaoke playback",
    copy: "Word-level timing streams back to the reader UI.",
    accent: "bg-gradient-to-r from-fuchsia-400 to-purple-500"
  }
];

export default function UploadSteps() {
  return (
    <div className="glass-panel h-full space-y-6 p-6 sm:p-8">
      <header>
        <p className="text-xs uppercase tracking-[0.4em] text-white/60">
          Flow
        </p>
        <h2 className="mt-2 text-3xl font-semibold text-white">
          Drag. Wait. Listen.
        </h2>
      </header>
      <ol className="space-y-5">
        {steps.map((step, idx) => (
          <li key={step.title} className="flex gap-4">
            <span
              className={`mt-1 inline-flex h-10 w-10 items-center justify-center rounded-2xl ${step.accent} text-sm font-semibold text-white shadow-lg shadow-black/30`}
            >
              {idx + 1}
            </span>
            <div>
              <h3 className="text-lg font-semibold text-white">{step.title}</h3>
              <p className="mt-1 text-sm text-white/70">{step.copy}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

