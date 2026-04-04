"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string;
  change: string;
  changeType: "positive" | "negative";
  icon: LucideIcon;
  iconColor: string;
  sparklineData?: number[];
}

function sparklinePath(values: number[]): string {
  if (values.length === 0) {
    return "";
  }
  if (values.length === 1) {
    return "M 0 16 L 120 16";
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const width = 120;
  const height = 32;

  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export default function KPICard({
  title, value, change, changeType, icon: Icon, iconColor, sparklineData,
}: KPICardProps) {
  const sparkData = sparklineData?.map((v, i) => ({ v, i })) || [];
  const trendPath = sparklinePath(sparkData.map((point) => point.v));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl p-6 shadow-card hover:shadow-card-hover transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconColor}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-ink-primary">{value}</p>
            <p className="text-xs text-ink-muted mt-0.5">{title}</p>
          </div>
        </div>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
          changeType === "positive" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
        }`}>
          {change}
        </span>
      </div>
      {sparkData.length > 0 && (
        <div className="mt-3 h-10">
          <svg viewBox="0 0 120 32" className="h-full w-full" aria-hidden="true">
            <path
              d={trendPath}
              fill="none"
              stroke="#1A3C5E"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      )}
    </motion.div>
  );
}
