"use client";

import { motion } from "framer-motion";

interface WorkabilityGaugeProps {
  score: number; // 0 to 1
  size?: number;
}

export default function WorkabilityGauge({ score, size = 200 }: WorkabilityGaugeProps) {
  const radius = (size - 20) / 2;
  const cy = size / 2 + 10;

  const color =
    score > 0.7 ? "#27AE60" : score > 0.4 ? "#F5A623" : "#E74C3C";

  return (
    <div className="relative" style={{ width: size, height: size / 2 + 40 }}>
      <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
        {/* Background arc */}
        <path
          d={`M 10 ${cy} A ${radius} ${radius} 0 0 1 ${size - 10} ${cy}`}
          fill="none"
          stroke="rgba(255,255,255,0.2)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <motion.path
          d={`M 10 ${cy} A ${radius} ${radius} 0 0 1 ${size - 10} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: score }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
        <span className="text-4xl font-bold text-white">{score.toFixed(2)}</span>
        <span className="text-sm text-white/60 mt-1">Workability</span>
      </div>
    </div>
  );
}
