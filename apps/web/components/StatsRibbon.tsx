const stats = [
  { label: "Build stage", value: "Week 1 MVP" },
  { label: "Voices shipping", value: "4 archetypes" },
  { label: "Processing target", value: "<60s / chapter" },
  { label: "Languages roadmap", value: "EN → JP/KR" }
];

export default function StatsRibbon() {
  return (
    <div className="glass-panel relative mt-12 grid gap-6 p-6 text-sm text-white/70 sm:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label}>
          <p className="text-xs uppercase tracking-[0.35em] text-white/50">
            {stat.label}
          </p>
          <p className="mt-2 text-2xl font-semibold text-white">{stat.value}</p>
        </div>
      ))}
      <div className="pointer-events-none absolute inset-0 rounded-[32px] ring-1 ring-white/10" />
    </div>
  );
}

