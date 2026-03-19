"use client";

interface RiskTierPillProps {
  tier: "low" | "medium" | "high";
  className?: string;
}

const TIER_STYLES = {
  low: "bg-green-100 text-green-700 border-green-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  high: "bg-red-100 text-red-700 border-red-200",
};

export default function RiskTierPill({ tier, className = "" }: RiskTierPillProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border capitalize ${TIER_STYLES[tier]} ${className}`}
    >
      {tier}
    </span>
  );
}
