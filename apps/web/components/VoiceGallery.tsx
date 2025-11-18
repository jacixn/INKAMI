const voices = [
  {
    id: "voice_child_f",
    name: "Young Girl",
    tone: "Child character",
    traits: "Bright, innocent, energetic"
  },
  {
    id: "voice_young_f",
    name: "Young Woman",
    tone: "Heroine lead",
    traits: "Warm, expressive, clear"
  },
  {
    id: "voice_adult_f",
    name: "Mature Woman",
    tone: "Wise character",
    traits: "Calm, sophisticated, rich"
  },
  {
    id: "voice_child_m",
    name: "Young Boy",
    tone: "Child character",
    traits: "Natural middle-school tone, gentle energy"
  },
  {
    id: "voice_young_m",
    name: "Young Man",
    tone: "Hero/Rival",
    traits: "Heroic, grounded, cinematic"
  },
  {
    id: "voice_adult_m",
    name: "Mature Man",
    tone: "Mentor/Warrior",
    traits: "Deep, stoic, authoritative"
  },
  {
    id: "voice_narrator",
    name: "Narrator",
    tone: "Story voice",
    traits: "Clear, neutral, professional"
  },
  {
    id: "voice_system",
    name: "System Voice",
    tone: "UI/System",
    traits: "Neutral, precise, informative"
  },
  {
    id: "voice_sfx",
    name: "FX Voice",
    tone: "Sound Effects",
    traits: "Impact hits, stylized cues"
  }
];

export default function VoiceGallery() {
  return (
    <section className="mt-16 space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-white/60">
            Voice bank
          </p>
          <h2 className="text-3xl font-semibold text-white">
            Archetypes you can remap instantly
          </h2>
        </div>
        <p className="max-w-sm text-sm text-white/70">
          ElevenLabs + Deepsick neural voices with personality tags. Pick a new
          voice in the reader and the backend regenerates audio on the fly.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        {voices.map((voice) => (
          <div
            key={voice.id}
            className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-lg shadow-black/30"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">{voice.name}</h3>
              <span className="rounded-full border border-white/20 px-3 py-1 text-xs text-white/60">
                {voice.tone}
              </span>
            </div>
            <p className="mt-2 text-sm text-white/70">{voice.traits}</p>
            <div className="mt-4 h-10 rounded-full border border-white/10 bg-gradient-to-r from-white/10 via-white/40 to-white/10 text-center text-xs uppercase tracking-[0.4em] text-white/70">
              <span className="inline-flex h-full w-full items-center justify-center">
                Preview soon
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

