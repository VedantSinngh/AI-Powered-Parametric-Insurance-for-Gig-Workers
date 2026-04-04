"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Headset, Search, TriangleAlert, UserRound } from "lucide-react";
import { fetchCityRiskSummary, type CityRiskSummary } from "@/lib/city-risk";
import { ApiError, apiGet } from "@/lib/api";
import { formatIsoToUi, getAccessToken, zoneFromH3 } from "@/lib/gridguard";

type PartnersResponse = {
  partners: Array<{
    _id?: string;
    id?: string;
    full_name: string;
    email: string;
    city: string;
    risk_tier: string;
    is_active: boolean;
    primary_zone_h3?: string | null;
  }>;
};

type FraudFlagsResponse = {
  flags: Array<{
    id: string;
    partner_name?: string;
    partner_email?: string;
    partner_id: string;
    flag_type: string;
    severity: "info" | "warning" | "critical";
    status: "pending" | "dismissed" | "escalated" | "confirmed";
    flagged_at: string;
    primary_zone_h3?: string | null;
  }>;
};

function severityClass(severity: string): string {
  if (severity === "critical") return "bg-red-100 text-red-700";
  if (severity === "warning") return "bg-amber-100 text-amber-700";
  return "bg-slate-100 text-slate-700";
}

export default function SupportConsolePage() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("search") || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [partners, setPartners] = useState<PartnersResponse["partners"]>([]);
  const [cityRiskMap, setCityRiskMap] = useState<Record<string, CityRiskSummary>>({});
  const [flags, setFlags] = useState<FraudFlagsResponse["flags"]>([]);

  const runSearch = async (nextQuery?: string) => {
    const token = getAccessToken();
    if (!token) {
      setError("Login required to use support console.");
      setLoading(false);
      return;
    }

    const effectiveQuery = (nextQuery ?? query).trim();

    try {
      setLoading(true);
      setError("");

      const partnerParams = new URLSearchParams({ limit: "12", offset: "0" });
      const flagParams = new URLSearchParams({ limit: "12", offset: "0" });
      if (effectiveQuery) {
        partnerParams.set("search", effectiveQuery);
        flagParams.set("search", effectiveQuery);
      }

      const [partnerRes, fraudRes] = await Promise.all([
        apiGet<PartnersResponse>(`/admin/partners?${partnerParams.toString()}`, token),
        apiGet<FraudFlagsResponse>(`/fraud/flags?${flagParams.toString()}`, token),
      ]);

      const uniqueCities = Array.from(
        new Set(
          partnerRes.partners
            .map((partner) => partner.city?.trim().toLowerCase())
            .filter((value): value is string => Boolean(value)),
        ),
      );

      const cityRiskEntries = await Promise.all(
        uniqueCities.map(async (cityKey) => {
          try {
            const summaryForCity = await fetchCityRiskSummary(cityKey);
            return [cityKey, summaryForCity] as const;
          } catch {
            return [cityKey, null] as const;
          }
        }),
      );

      const nextCityRiskMap: Record<string, CityRiskSummary> = {};
      for (const [cityKey, cityRisk] of cityRiskEntries) {
        if (cityRisk) {
          nextCityRiskMap[cityKey] = cityRisk;
        }
      }

      setPartners(partnerRes.partners);
      setCityRiskMap(nextCityRiskMap);
      setFlags(fraudRes.flags);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load support data.");
      setCityRiskMap({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSearch(searchParams.get("search") || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const pendingFlags = useMemo(
    () => flags.filter((flag) => flag.status === "pending" || flag.status === "escalated"),
    [flags],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy flex items-center gap-2">
            <Headset className="w-6 h-6 text-amber" /> Support Console
          </h1>
          <p className="text-sm text-ink-muted">Quick lookup for partner account and risk incidents.</p>
        </div>
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2 min-w-[320px]">
          <Search className="w-4 h-4 text-ink-muted" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                runSearch();
              }
            }}
            placeholder="Search partner name, email, or id"
            className="w-full text-sm outline-none"
          />
          <button onClick={() => runSearch()} className="text-xs font-semibold text-navy">Search</button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Matches</p>
          <p className="text-2xl font-bold text-navy mt-1">{loading ? "..." : partners.length}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Pending Flag Alerts</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{loading ? "..." : pendingFlags.length}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-5">
          <p className="text-xs uppercase text-ink-muted">Verified Active Riders</p>
          <p className="text-2xl font-bold text-green-700 mt-1">
            {loading ? "..." : partners.filter((partner) => partner.is_active).length}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 font-semibold text-navy">Partner Search Results</div>
          <div className="divide-y divide-slate-100">
            {partners.map((partner) => (
              <div key={partner._id || partner.id} className="px-5 py-4 flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-ink-primary">{partner.full_name}</p>
                  <p className="text-xs text-ink-muted">{partner.email}</p>
                  <p className="text-xs text-ink-muted mt-1">{partner.city} · Zone {zoneFromH3(partner.primary_zone_h3)}</p>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${partner.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {partner.is_active ? "active" : "suspended"}
                  </span>
                  <p className="text-xs mt-2 text-ink-muted">
                    Risk: {(cityRiskMap[partner.city?.toLowerCase() || ""]?.risk_tier || partner.risk_tier).toUpperCase()}
                  </p>
                </div>
              </div>
            ))}
            {!loading && partners.length === 0 && (
              <div className="px-5 py-8 text-sm text-ink-muted">No partners found.</div>
            )}
          </div>
        </div>

        <div className="bg-white border border-slate-100 rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 font-semibold text-navy flex items-center gap-2">
            <TriangleAlert className="w-4 h-4 text-amber" /> Fraud & Risk Flags
          </div>
          <div className="divide-y divide-slate-100">
            {flags.map((flag) => (
              <div key={flag.id} className="px-5 py-4 flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-ink-primary flex items-center gap-2">
                    <UserRound className="w-4 h-4 text-ink-muted" />
                    {flag.partner_name || flag.partner_id}
                  </p>
                  <p className="text-xs text-ink-muted mt-1">{flag.partner_email || flag.partner_id}</p>
                  <p className="text-xs text-ink-muted">{flag.flag_type.replaceAll("_", " ")} · {formatIsoToUi(flag.flagged_at)}</p>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${severityClass(flag.severity)}`}>
                    {flag.severity}
                  </span>
                  <p className="text-xs mt-2 text-ink-muted">{flag.status}</p>
                </div>
              </div>
            ))}
            {!loading && flags.length === 0 && (
              <div className="px-5 py-8 text-sm text-ink-muted">No flags found.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
