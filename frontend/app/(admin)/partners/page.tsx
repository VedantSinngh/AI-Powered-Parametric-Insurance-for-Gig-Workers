"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Users, Building2, MapPin, Search, Plus, Filter, UserPlus } from "lucide-react";
import Link from "next/link";
import { CITIES } from "@/lib/mock-data";
import { ApiError, apiGet, apiPatch, apiPost } from "@/lib/api";
import { fetchCityRiskSummary, type CityRiskSummary, type RiskTier } from "@/lib/city-risk";
import { getAccessToken, zoneFromH3 } from "@/lib/gridguard";

type AdminPartner = {
  _id?: string;
  id?: string;
  full_name: string;
  email: string;
  city: string;
  platform: string;
  risk_tier: "low" | "medium" | "high" | "critical";
  is_active: boolean;
  primary_zone_h3?: string | null;
  created_at: string;
  current_policy?: Array<{
    premium_amount: number;
    status: string;
  }>;
};

type PartnersResponse = {
  partners: AdminPartner[];
  total: number;
  limit: number;
  offset: number;
};

type SummaryResponse = {
  active_partners: number;
  top_disrupted_zones: Array<{
    _id: string;
    event_count: number;
    city?: string;
  }>;
};

type PartnerStatusFilter = "all" | "active" | "suspended";
type PartnerRiskFilter = "all" | "low" | "medium" | "high" | "critical";

type CreatePartnerPayload = {
  full_name: string;
  email: string;
  city: string;
  platform: string;
  device_id: string;
  upi_handle?: string;
  preferred_language: string;
};

function formatJoinDate(value?: string): string {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleDateString("en-IN", {
    month: "short",
    year: "numeric",
  });
}

function trustScore(partner: AdminPartner, cityRisk?: CityRiskSummary | null): number {
  let score = cityRisk
    ? Math.round((1 - cityRisk.risk_score) * 100)
    : partner.risk_tier === "low"
      ? 90
      : partner.risk_tier === "medium"
        ? 78
        : partner.risk_tier === "high"
          ? 62
          : 45;

  if (partner.is_active) {
    score += 4;
  }
  if ((partner.current_policy || []).length > 0) {
    score += 2;
  }
  return Math.min(99, Math.max(1, score));
}

function statusBadge(isActive: boolean): string {
  return isActive
    ? "bg-green-100 text-green-700"
    : "bg-red-100 text-red-700";
}

function riskBadge(riskTier: RiskTier): string {
  if (riskTier === "low") {
    return "bg-green-100 text-green-700";
  }
  if (riskTier === "medium") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-red-100 text-red-700";
}

export default function PartnersPage() {
  const searchParams = useSearchParams();
  const pageSize = 10;

  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [cityFilter, setCityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<PartnerStatusFilter>("all");
  const [riskFilter, setRiskFilter] = useState<PartnerRiskFilter>("all");
  const [page, setPage] = useState(1);

  const [partners, setPartners] = useState<AdminPartner[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [cityRiskMap, setCityRiskMap] = useState<Record<string, CityRiskSummary>>({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [suspendingPartnerId, setSuspendingPartnerId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingPartner, setCreatingPartner] = useState(false);
  const [newPartner, setNewPartner] = useState<CreatePartnerPayload>({
    full_name: "",
    email: "",
    city: "bengaluru",
    platform: "other",
    device_id: "",
    upi_handle: "",
    preferred_language: "en",
  });

  const loadPartners = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Login required to view partner management.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");

      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String((page - 1) * pageSize),
      });
      if (cityFilter !== "all") {
        params.set("city", cityFilter.toLowerCase());
      }
      if (statusFilter !== "all") {
        params.set("status", statusFilter === "active" ? "true" : "false");
      }
      if (riskFilter !== "all") {
        params.set("risk_tier", riskFilter);
      }
      if (search.trim()) {
        params.set("search", search.trim());
      }

      const [partnersResponse, summaryResponse] = await Promise.all([
        apiGet<PartnersResponse>(`/admin/partners?${params.toString()}`, token),
        apiGet<SummaryResponse>("/admin/analytics/summary", token),
      ]);

      const uniqueCities = Array.from(
        new Set(
          partnersResponse.partners
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

      setPartners(partnersResponse.partners);
      setTotal(partnersResponse.total);
      setSummary(summaryResponse);
      setCityRiskMap(nextCityRiskMap);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setError("Admin access required. Use an approved admin account to continue.");
      } else {
        setError(err instanceof ApiError ? err.message : "Unable to load partner data.");
      }
      setCityRiskMap({});
    } finally {
      setLoading(false);
    }
  }, [cityFilter, page, riskFilter, search, statusFilter]);

  useEffect(() => {
    loadPartners();
  }, [loadPartners]);

  useEffect(() => {
    setPage(1);
  }, [search, cityFilter, statusFilter, riskFilter]);

  useEffect(() => {
    const externalSearch = searchParams.get("search") || "";
    setSearch(externalSearch);
  }, [searchParams]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const zonesCovered = useMemo(() => {
    const partnerZones = partners
      .map((partner) => zoneFromH3(partner.primary_zone_h3))
      .filter((zone) => zone !== "N/A");
    const disruptedZones = (summary?.top_disrupted_zones || []).map((zone) => zoneFromH3(zone._id));
    return new Set([...partnerZones, ...disruptedZones]).size;
  }, [partners, summary]);

  const handleSuspend = async (partnerId: string) => {
    const token = getAccessToken();
    if (!token) {
      setError("Login required to suspend partners.");
      return;
    }

    try {
      setSuspendingPartnerId(partnerId);
      await apiPatch(`/admin/partners/${partnerId}/suspend`, undefined, token);
      setPartners((currentPartners) =>
        currentPartners.map((partner) =>
          (partner._id || partner.id) === partnerId
            ? { ...partner, is_active: false }
            : partner,
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to suspend this partner.");
    } finally {
      setSuspendingPartnerId(null);
    }
  };

  const handleCreatePartner = async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Login required to create partners.");
      return;
    }

    try {
      setCreatingPartner(true);
      setError("");

      const payload: CreatePartnerPayload = {
        ...newPartner,
        full_name: newPartner.full_name.trim(),
        email: newPartner.email.trim().toLowerCase(),
        city: newPartner.city.trim().toLowerCase(),
        platform: newPartner.platform.trim().toLowerCase(),
        device_id: newPartner.device_id.trim(),
        upi_handle: newPartner.upi_handle?.trim().toLowerCase() || undefined,
      };

      if (!payload.full_name || !payload.email || !payload.device_id) {
        setError("Name, email, and device ID are required to create a partner.");
        return;
      }

      await apiPost("/admin/partners/create", payload, token);
      setShowCreateModal(false);
      setNewPartner({
        full_name: "",
        email: "",
        city: "bengaluru",
        platform: "other",
        device_id: "",
        upi_handle: "",
        preferred_language: "en",
      });
      await loadPartners();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create partner right now.");
    } finally {
      setCreatingPartner(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Header / Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white p-6 rounded-2xl shadow-card border border-slate-100"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider">Total Partners</p>
              <p className="text-2xl font-bold text-navy">{loading ? "..." : total.toLocaleString("en-IN")}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white p-6 rounded-2xl shadow-card border border-slate-100"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-orange-100 flex items-center justify-center text-orange-600">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider">Active Partners</p>
              <p className="text-2xl font-bold text-navy">
                {loading ? "..." : (summary?.active_partners || 0).toLocaleString("en-IN")}
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white p-6 rounded-2xl shadow-card border border-slate-100"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-navy/10 flex items-center justify-center text-navy">
              <MapPin className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider">Zones Covered</p>
              <p className="text-2xl font-bold text-navy">{loading ? "..." : zonesCovered.toLocaleString("en-IN")}</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Partners Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-navy">Service Partners</h2>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-secondary" />
                <input
                  type="text"
                  placeholder="Search name or email..."
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-navy/10 w-64"
                />
              </div>
              <select
                value={cityFilter}
                onChange={(event) => setCityFilter(event.target.value)}
                className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm"
              >
                <option value="all">All Cities</option>
                {CITIES.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
              <select
                value={riskFilter}
                onChange={(event) => setRiskFilter(event.target.value as PartnerRiskFilter)}
                className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm"
              >
                <option value="all">All Risks</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as PartnerStatusFilter)}
                className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
              </select>
              <button onClick={loadPartners} className="p-2 bg-white border border-slate-200 rounded-lg text-ink-secondary hover:bg-slate-50">
                <Filter className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-navy text-white rounded-lg text-sm font-medium hover:bg-navy/90"
              >
                <Plus className="w-4 h-4" />
                Add Partner
              </button>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Name/Contact</th>
                    <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Join Date</th>
                    <th className="px-6 py-3 text-xs font-bold text-ink-secondary uppercase tracking-wider">Metrics</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {partners.map((partner) => {
                    const partnerId = partner._id || partner.id || "";
                    const liveCityRisk = cityRiskMap[partner.city?.toLowerCase() || ""];
                    const liveRiskTier: RiskTier = liveCityRisk?.risk_tier || partner.risk_tier;
                    const score = trustScore(partner, liveCityRisk);
                    return (
                    <motion.tr
                      key={partnerId}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-navy">
                            {partner.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-navy">{partner.full_name}</p>
                            <p className="text-xs text-ink-secondary">{partner.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                            statusBadge(partner.is_active)
                          }`}
                        >
                          {partner.is_active ? "active" : "suspended"}
                        </span>
                        <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${riskBadge(liveRiskTier)}`}>
                          {liveRiskTier}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-xs text-ink-secondary font-medium">{formatJoinDate(partner.created_at)}</p>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="text-ink-secondary">Trust Score</span>
                            <span className="font-bold text-navy">{score}%</span>
                          </div>
                          <div className="w-24 h-1 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-navy rounded-full"
                              style={{ width: `${score}%` }}
                            />
                          </div>
                          {partner.is_active && (
                            <button
                              onClick={() => handleSuspend(partnerId)}
                              disabled={suspendingPartnerId === partnerId || !partnerId}
                              className="text-[10px] w-fit px-2 py-1 rounded-md border border-red-200 text-red-700 hover:bg-red-50"
                            >
                              {suspendingPartnerId === partnerId ? "Suspending..." : "Suspend"}
                            </button>
                          )}
                        </div>
                      </td>
                    </motion.tr>
                  );
                  })}

                  {!loading && partners.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-sm text-ink-muted text-center">
                        No partners found for these filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-ink-secondary">
                Showing {partners.length} of {total.toLocaleString("en-IN")} partners
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                  className="px-3 py-1 text-xs border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-50"
                >
                  Prev
                </button>
                <button className="px-3 py-1 text-xs border border-slate-200 rounded-md bg-navy text-white">
                  {page}/{totalPages}
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                  className="px-3 py-1 text-xs border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar - Hot Zones */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl shadow-card border border-slate-100">
            <h3 className="font-bold text-navy mb-4">Top Disruption Zones</h3>
            <div className="space-y-4">
              {(summary?.top_disrupted_zones || []).slice(0, 6).map((zone) => (
                <div key={zone._id} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-bold bg-white px-2 py-1 rounded border border-slate-200 uppercase">
                      {zoneFromH3(zone._id)}
                    </span>
                    <div>
                      <p className="text-xs font-bold text-navy">{zone.event_count.toLocaleString("en-IN")} Active Events</p>
                      <p className="text-[10px] text-ink-secondary uppercase tracking-tighter">{zone.city || "unknown city"}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-red-600">Risk</p>
                  </div>
                </div>
              ))}
              {!loading && (summary?.top_disrupted_zones || []).length === 0 && (
                <p className="text-sm text-ink-muted">No live disruption zones right now.</p>
              )}
            </div>
            <Link href="/admin-live-map" className="w-full mt-4 py-3 text-sm font-bold text-navy border border-navy/10 rounded-xl hover:bg-slate-50 block text-center">
              View Live Map
            </Link>
          </div>

          <div className="bg-orange-500 rounded-2xl p-6 text-white relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/20 rounded-full -mr-16 -mt-16 blur-2xl" />
            <div className="relative z-10">
              <UserPlus className="w-8 h-8 mb-4" />
              <h3 className="font-bold text-lg">Partner Onboarding</h3>
              <p className="text-sm opacity-90 mb-6">
                Onboarding APIs are available through the auth register + OTP verification flow.
              </p>
              <Link href="/analytics" className="w-full py-3 bg-white text-orange-600 rounded-xl text-sm font-bold shadow-lg block text-center">
                Open Analytics
              </Link>
            </div>
          </div>
        </div>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-navy">Add Partner</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-sm text-ink-muted">Close</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                placeholder="Full name"
                value={newPartner.full_name}
                onChange={(event) => setNewPartner((s) => ({ ...s, full_name: event.target.value }))}
                className="h-10 px-3 rounded-lg border border-gray-200 text-sm"
              />
              <input
                placeholder="Email"
                value={newPartner.email}
                onChange={(event) => setNewPartner((s) => ({ ...s, email: event.target.value }))}
                className="h-10 px-3 rounded-lg border border-gray-200 text-sm"
              />
              <input
                placeholder="Device ID"
                value={newPartner.device_id}
                onChange={(event) => setNewPartner((s) => ({ ...s, device_id: event.target.value }))}
                className="h-10 px-3 rounded-lg border border-gray-200 text-sm"
              />
              <input
                placeholder="UPI handle (optional)"
                value={newPartner.upi_handle}
                onChange={(event) => setNewPartner((s) => ({ ...s, upi_handle: event.target.value }))}
                className="h-10 px-3 rounded-lg border border-gray-200 text-sm"
              />
              <select
                value={newPartner.city}
                onChange={(event) => setNewPartner((s) => ({ ...s, city: event.target.value }))}
                className="h-10 px-3 rounded-lg border border-gray-200 text-sm"
              >
                {CITIES.map((city) => (
                  <option key={city} value={city.toLowerCase()}>{city}</option>
                ))}
              </select>
              <select
                value={newPartner.platform}
                onChange={(event) => setNewPartner((s) => ({ ...s, platform: event.target.value }))}
                className="h-10 px-3 rounded-lg border border-gray-200 text-sm"
              >
                <option value="zomato">Zomato</option>
                <option value="swiggy">Swiggy</option>
                <option value="zepto">Zepto</option>
                <option value="blinkit">Blinkit</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="h-10 px-4 rounded-lg border border-gray-200 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleCreatePartner}
                disabled={creatingPartner}
                className="h-10 px-4 rounded-lg bg-navy text-white text-sm font-semibold disabled:opacity-60"
              >
                {creatingPartner ? "Creating..." : "Create Partner"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}