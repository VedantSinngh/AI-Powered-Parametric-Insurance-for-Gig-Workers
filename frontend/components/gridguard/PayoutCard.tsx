"use client";

import { EVENT_ICONS, EVENT_COLORS, type Payout } from "@/lib/mock-data";
import ZoneHexBadge from "./ZoneHexBadge";

interface PayoutCardProps {
  payout: Payout;
}

const DOT_COLORS: Record<string, string> = {
  rain: "bg-blue-500",
  heat: "bg-orange-500",
  aqi: "bg-purple-500",
  outage: "bg-violet-500",
};

export default function PayoutCard({ payout }: PayoutCardProps) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-surface transition-colors cursor-pointer group">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <span className="text-xl">{EVENT_ICONS[payout.eventType]}</span>
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${DOT_COLORS[payout.eventType]}`} />
        <ZoneHexBadge zone={payout.zone} />
        <span className="text-sm text-ink-primary truncate">{payout.eventName}</span>
      </div>
      <div className="flex items-center gap-4 flex-shrink-0">
        <span className="text-sm font-bold text-ink-primary">₹{payout.amount}</span>
        <span className="text-xs text-ink-muted">{payout.timestamp}</span>
        <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
          payout.status === "paid" ? "bg-green-100 text-green-700" :
          payout.status === "pending" ? "bg-amber-100 text-amber-700" :
          "bg-red-100 text-red-700"
        }`}>
          {payout.status.charAt(0).toUpperCase() + payout.status.slice(1)}
        </span>
      </div>
    </div>
  );
}
