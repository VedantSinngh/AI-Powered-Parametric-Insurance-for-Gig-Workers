"use client";

import { useEffect, useMemo, useState } from "react";
import { ClipboardList, ShieldAlert, ReceiptText, Activity } from "lucide-react";
import { ApiError, apiGet } from "@/lib/api";
import { formatIsoToUi, getAccessToken } from "@/lib/gridguard";

type PayoutTimelineResponse = {
  payouts: Array<{
    id: string;
    partner_name: string;
    amount: number;
    status: string;
    provider?: string;
    created_at: string;
  }>;
};

type FraudFlagsResponse = {
  flags: Array<{
    id: string;
    partner_name?: string;
    flag_type: string;
    status: string;
    severity: string;
    flagged_at: string;
  }>;
};

type AuditRow = {
  id: string;
  type: "payout" | "fraud";
  title: string;
  subtitle: string;
  status: string;
  timestamp: string;
};

export default function AuditTrailPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [timeline, setTimeline] = useState<AuditRow[]>([]);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        setError("Login required to view audit trail.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const [payoutRes, fraudRes] = await Promise.all([
          apiGet<PayoutTimelineResponse>("/admin/payouts/recent?limit=120", token),
          apiGet<FraudFlagsResponse>("/fraud/flags?limit=100", token),
        ]);

        const payoutRows: AuditRow[] = payoutRes.payouts.map((payout) => ({
          id: `payout-${payout.id}`,
          type: "payout",
          title: `Payout ${payout.status}`,
          subtitle: `${payout.partner_name || "Unknown"} · ₹${Math.round(payout.amount)} · ${payout.provider || "mock"}`,
          status: payout.status,
          timestamp: payout.created_at,
        }));

        const fraudRows: AuditRow[] = fraudRes.flags.map((flag) => ({
          id: `fraud-${flag.id}`,
          type: "fraud",
          title: `Fraud ${flag.status}`,
          subtitle: `${flag.partner_name || "Unknown"} · ${flag.flag_type.replaceAll("_", " ")} · ${flag.severity}`,
          status: flag.status,
          timestamp: flag.flagged_at,
        }));

        const merged = [...payoutRows, ...fraudRows]
          .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
          .slice(0, 180);

        setTimeline(merged);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load audit timeline.");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

  const stats = useMemo(() => {
    return {
      payoutEvents: timeline.filter((row) => row.type === "payout").length,
      fraudEvents: timeline.filter((row) => row.type === "fraud").length,
    };
  }, [timeline]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy flex items-center gap-2">
          <ClipboardList className="w-6 h-6 text-amber" /> Audit Trail
        </h1>
        <p className="text-sm text-ink-muted">Unified immutable event stream for payouts and fraud decisions.</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Timeline Events</p>
          <p className="text-2xl font-bold text-navy mt-1">{loading ? "..." : timeline.length}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Payout Events</p>
          <p className="text-2xl font-bold text-green-700 mt-1">{loading ? "..." : stats.payoutEvents}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Fraud Events</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{loading ? "..." : stats.fraudEvents}</p>
        </div>
      </div>

      <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 font-semibold text-navy">Chronological Activity Feed</div>
        <div className="divide-y divide-slate-100">
          {timeline.map((event) => (
            <div key={event.id} className="px-5 py-4 flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center ${event.type === "payout" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                  {event.type === "payout" ? <ReceiptText className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
                </span>
                <div>
                  <p className="font-semibold text-ink-primary">{event.title}</p>
                  <p className="text-xs text-ink-muted mt-1">{event.subtitle}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-ink-muted">{formatIsoToUi(event.timestamp)}</p>
                <p className="text-xs font-semibold mt-1 capitalize text-ink-primary flex items-center justify-end gap-1">
                  <Activity className="w-3 h-3" /> {event.status}
                </p>
              </div>
            </div>
          ))}
          {!loading && timeline.length === 0 && (
            <div className="px-5 py-8 text-sm text-ink-muted">No audit entries available.</div>
          )}
        </div>
      </div>
    </div>
  );
}
