"use client";

import { type FraudAlert } from "@/lib/mock-data";
import { AlertTriangle, Eye, ShieldX, ShieldCheck } from "lucide-react";

interface FraudAlertRowProps {
  alert: FraudAlert;
  isSelected: boolean;
  onClick: () => void;
}

const SEVERITY_STYLES = {
  critical: "border-l-4 border-l-red-500 bg-red-50/50",
  warning: "border-l-4 border-l-amber-500 bg-amber-50/50",
  info: "border-l-4 border-l-blue-500 bg-blue-50/50",
};

const SEVERITY_BADGE = {
  critical: "bg-red-100 text-red-700",
  warning: "bg-amber-100 text-amber-700",
  info: "bg-blue-100 text-blue-700",
};

const RULE_LABELS: Record<string, string> = {
  wrong_zone: "Wrong Zone",
  stationary_device: "Stationary Device",
  no_pre_activity: "No Pre-Activity",
  velocity_abuse: "Velocity Abuse",
  multi_account: "Multi Account",
};

export default function FraudAlertRow({ alert, isSelected, onClick }: FraudAlertRowProps) {
  return (
    <div
      onClick={onClick}
      className={`
        p-4 rounded-xl cursor-pointer transition-all
        ${SEVERITY_STYLES[alert.severity]}
        ${isSelected ? "ring-2 ring-navy shadow-card" : "hover:shadow-card"}
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className={`w-4 h-4 ${
            alert.severity === "critical" ? "text-red-500" :
            alert.severity === "warning" ? "text-amber-500" : "text-blue-500"
          }`} />
          <span className="text-sm font-semibold text-ink-primary">{alert.partnerName}</span>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_BADGE[alert.severity]}`}>
          {alert.severity}
        </span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-ink-muted">
          {RULE_LABELS[alert.rule] || alert.rule} · {alert.timestamp}
        </span>
        <div className="flex items-center gap-1.5">
          <button className="p-1.5 rounded-lg hover:bg-white/80 transition-colors" title="View">
            <Eye className="w-3.5 h-3.5 text-ink-muted" />
          </button>
          <button className="p-1.5 rounded-lg hover:bg-red-100 transition-colors" title="Confirm">
            <ShieldX className="w-3.5 h-3.5 text-red-500" />
          </button>
          <button className="p-1.5 rounded-lg hover:bg-green-100 transition-colors" title="Dismiss">
            <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
          </button>
        </div>
      </div>
    </div>
  );
}
