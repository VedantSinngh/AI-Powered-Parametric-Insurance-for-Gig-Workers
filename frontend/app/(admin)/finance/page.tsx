"use client";

import { useEffect, useMemo, useState } from "react";
import { Landmark, ArrowDownUp, AlertOctagon } from "lucide-react";
import { ApiError, apiGet } from "@/lib/api";
import { formatIsoToUi, getAccessToken } from "@/lib/gridguard";

type RecentPayoutsResponse = {
  payouts: Array<{
    id: string;
    partner_name: string;
    city: string;
    amount: number;
    status: string;
    provider?: string;
    provider_status?: string;
    failure_reason?: string;
    created_at: string;
  }>;
};

function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function FinanceReconPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [payouts, setPayouts] = useState<RecentPayoutsResponse["payouts"]>([]);

  useEffect(() => {
    const run = async () => {
      const token = getAccessToken();
      if (!token) {
        setError("Login required to view finance reconciliation.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");
        const response = await apiGet<RecentPayoutsResponse>("/admin/payouts/recent?limit=200", token);
        setPayouts(response.payouts);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load finance data.");
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

  const metrics = useMemo(() => {
    const total = payouts.reduce((sum, payout) => sum + payout.amount, 0);
    const failed = payouts.filter((payout) => payout.status === "failed");
    const processing = payouts.filter((payout) => payout.status === "processing");
    const providerBreakdown = payouts.reduce<Record<string, number>>((acc, payout) => {
      const provider = payout.provider || "mock";
      acc[provider] = (acc[provider] || 0) + 1;
      return acc;
    }, {});

    return {
      total,
      failed,
      processing,
      providerBreakdown,
    };
  }, [payouts]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy flex items-center gap-2">
          <Landmark className="w-6 h-6 text-amber" /> Finance Reconciliation
        </h1>
        <p className="text-sm text-ink-muted">Monitor provider-level payout status, failures, and processing queues.</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Total Reconciled</p>
          <p className="text-2xl font-bold text-navy mt-1">{loading ? "..." : formatINR(metrics.total)}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Processing Queue</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">{loading ? "..." : metrics.processing.length}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Failures</p>
          <p className="text-2xl font-bold text-red-700 mt-1">{loading ? "..." : metrics.failed.length}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Provider Mix</p>
          <p className="text-sm font-semibold text-ink-primary mt-2">
            {Object.entries(metrics.providerBreakdown).map(([provider, count]) => `${provider}:${count}`).join(" · ") || "-"}
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <p className="font-semibold text-navy">Payout Ledger</p>
          <div className="text-xs text-ink-muted flex items-center gap-1">
            <ArrowDownUp className="w-3.5 h-3.5" /> latest first
          </div>
        </div>
        <div className="divide-y divide-slate-100">
          {payouts.map((payout) => (
            <div key={payout.id} className="px-5 py-4 flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-ink-primary">{payout.partner_name || "Unknown"}</p>
                <p className="text-xs text-ink-muted">{payout.city} · {formatIsoToUi(payout.created_at)}</p>
              </div>
              <div className="text-right">
                <p className="font-bold text-navy">{formatINR(payout.amount)}</p>
                <p className="text-xs text-ink-muted capitalize">{payout.provider || "mock"} · {payout.provider_status || payout.status}</p>
                {payout.failure_reason && (
                  <p className="text-xs text-red-600 flex items-center justify-end gap-1 mt-1">
                    <AlertOctagon className="w-3 h-3" /> {payout.failure_reason}
                  </p>
                )}
              </div>
            </div>
          ))}
          {!loading && payouts.length === 0 && (
            <div className="px-5 py-8 text-sm text-ink-muted">No payouts available.</div>
          )}
        </div>
      </div>
    </div>
  );
}
