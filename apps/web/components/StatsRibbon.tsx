const stats = [
  { label: "Panels parsed", value: "4.8M+" },
  { label: "Voices blended", value: "320+" },
  { label: "Avg. process time", value: "58s" },
  { label: "Languages planned", value: "3" }
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

