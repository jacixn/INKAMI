const features = [
  "YOLOv8 layout brain",
  "PaddleOCR cleanups",
  "Voice archetype memory",
  "Realtime karaoke highlights",
  "Narration <-> dialogue swaps",
  "Offline caching",
  "Correction UI",
  "ElevenLabs + Deepsick",
  "Supabase metadata",
  "S3 audio cache"
];

export default function FeatureMarquee() {
  return (
    <div className="relative mt-16 overflow-hidden rounded-3xl border border-white/10 bg-black/30 py-4">
      <div className="flex animate-[marqueeScroll_30s_linear_infinite] gap-12 whitespace-nowrap text-lg font-medium text-white/70">
        {features.concat(features).map((feature, idx) => (
          <span
            // eslint-disable-next-line react/no-array-index-key
            key={`${feature}-${idx}`}
            className="tracking-wide"
          >
            {feature}
          </span>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-black via-black/80 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-black via-black/80 to-transparent" />
    </div>
  );
}

