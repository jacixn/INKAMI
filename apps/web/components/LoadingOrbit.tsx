"use client";

import { useMemo } from "react";

interface LoadingOrbitProps {
  size?: number;
}

export default function LoadingOrbit({ size = 72 }: LoadingOrbitProps) {
  const dots = useMemo(() => Array.from({ length: 12 }), []);

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {dots.map((_, idx) => (
        <span
          // eslint-disable-next-line react/no-array-index-key
          key={idx}
          className="absolute h-2 w-2 rounded-full bg-white/70"
          style={{
            transform: `rotate(${idx * 30}deg) translate(${size / 2.5}px)`,
            opacity: 1 - idx * 0.06,
            animation: "pulseOrbit 1.2s linear infinite",
            animationDelay: `${idx * 0.05}s`
          }}
        />
      ))}
    </div>
  );
}

