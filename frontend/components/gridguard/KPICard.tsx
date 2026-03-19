"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
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

export default function KPICard({
  title, value, change, changeType, icon: Icon, iconColor, sparklineData,
}: KPICardProps) {
  const [count, setCount] = useState(0);
  const numericValue = parseFloat(value.replace(/[^0-9.]/g, ""));

  useEffect(() => {
    const duration = 1000;
    const steps = 30;
    const increment = numericValue / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= numericValue) {
        setCount(numericValue);
        clearInterval(timer);
      } else {
        setCount(current);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [numericValue]);

  const sparkData = sparklineData?.map((v, i) => ({ v, i })) || [];

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
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkData}>
              <Line type="monotone" dataKey="v" stroke="#1A3C5E" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  );
}
