const layers = [
  "from-cyan-500/30 via-transparent to-purple-500/10",
  "from-indigo-500/20 via-transparent to-rose-500/20",
  "from-emerald-400/20 via-transparent to-sky-500/10"
];

export default function Aurora() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-[#020208]">
      {layers.map((gradient, idx) => (
        <div
          key={gradient}
          className={`absolute inset-0 blur-[120px] opacity-70 mix-blend-screen animate-aurora-${idx}`}
        >
          <div className={`absolute inset-0 bg-gradient-to-br ${gradient}`} />
        </div>
      ))}
      <div className="absolute inset-x-0 top-0 mx-auto h-48 w-1/2 blur-[140px]">
        <div className="h-full w-full bg-gradient-to-r from-sky-500/40 to-fuchsia-500/40" />
      </div>
      <div className="absolute inset-0">
        <div className="noise-mask h-full w-full opacity-10" />
      </div>
    </div>
  );
}

