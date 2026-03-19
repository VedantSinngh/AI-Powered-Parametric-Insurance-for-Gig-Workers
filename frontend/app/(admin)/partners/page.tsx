"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Eye, Ban, Flag, Download, Bell, ChevronLeft, ChevronRight } from "lucide-react";
import ZoneHexBadge from "@/components/gridguard/ZoneHexBadge";
import RiskTierPill from "@/components/gridguard/RiskTierPill";
import { mockPartners, CITIES, PLATFORMS, type Partner } from "@/lib/mock-data";

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  suspended: "bg-red-100 text-red-700",
  pending: "bg-amber-100 text-amber-700",
};

export default function PartnersPage() {
  const [search, setSearch] = useState("");
  const [cityFilter, setCityFilter] = useState<string>("");
  const [riskFilter, setRiskFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const filtered = useMemo(() => {
    return mockPartners.filter((p) => {
      if (search) {
        const q = search.toLowerCase();
        if (!p.name.toLowerCase().includes(q) && !p.deviceId.toLowerCase().includes(q) && !p.email.toLowerCase().includes(q)) return false;
      }
      if (cityFilter && p.city !== cityFilter) return false;
      if (riskFilter && p.riskTier !== riskFilter) return false;
      if (statusFilter && p.status !== statusFilter) return false;
      return true;
    });
  }, [search, cityFilter, riskFilter, statusFilter]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const paged = filtered.slice((page - 1) * perPage, page * perPage);

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const toggleAll = () => {
    if (selected.size === paged.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(paged.map((p) => p.id)));
    }
  };

  const exportCSV = () => {
    const headers = "Name,Device ID,Email,City,Platform,Zone,Risk,Premium,Status\n";
    const rows = filtered.map(p =>
      `${p.name},${p.deviceId},${p.email},${p.city},${p.platform},${p.zone},${p.riskTier},₹${p.premium},${p.status}`
    ).join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "partners.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-ink-primary">Partners</h1>
        <span className="text-sm text-ink-muted">{filtered.length} total</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search name, device ID, email..."
            className="w-full h-10 pl-9 pr-4 rounded-lg bg-white border border-gray-200 text-sm focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none"
          />
        </div>
        <select
          value={cityFilter}
          onChange={(e) => { setCityFilter(e.target.value); setPage(1); }}
          className="h-10 px-3 rounded-lg bg-white border border-gray-200 text-sm outline-none"
        >
          <option value="">All Cities</option>
          {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={riskFilter}
          onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
          className="h-10 px-3 rounded-lg bg-white border border-gray-200 text-sm outline-none"
        >
          <option value="">All Risk</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="h-10 px-3 rounded-lg bg-white border border-gray-200 text-sm outline-none"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      {/* Bulk toolbar */}
      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-navy rounded-xl mb-4 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-white text-sm font-medium">{selected.size} selected</span>
              <div className="flex gap-2">
                <button onClick={exportCSV} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 text-white text-xs rounded-lg hover:bg-white/20 transition">
                  <Download className="w-3.5 h-3.5" /> Export CSV
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-300 text-xs rounded-lg hover:bg-red-500/30 transition">
                  <Ban className="w-3.5 h-3.5" /> Suspend
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-amber/20 text-amber-light text-xs rounded-lg hover:bg-amber/30 transition">
                  <Bell className="w-3.5 h-3.5" /> Notify
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="p-3 text-left">
                  <input type="checkbox" checked={selected.size === paged.length && paged.length > 0}
                    onChange={toggleAll} className="rounded" />
                </th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Name</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Zone</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">City</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Risk</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Premium</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Last Payout</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Status</th>
                <th className="p-3 text-left font-semibold text-ink-muted text-xs uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((p) => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-surface/50 transition">
                  <td className="p-3">
                    <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleSelect(p.id)} className="rounded" />
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-navy/10 flex items-center justify-center text-xs font-bold text-navy">
                        {p.name.split(" ").map(n => n[0]).join("")}
                      </div>
                      <div>
                        <p className="font-medium text-ink-primary">{p.name}</p>
                        <p className="text-xs text-ink-muted font-mono">{p.deviceId}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-3"><ZoneHexBadge zone={p.zone} /></td>
                  <td className="p-3">
                    <span className="text-ink-primary">{p.city}</span>
                    <span className="ml-1">{PLATFORMS.find(pl => pl.name === p.platform)?.emoji}</span>
                  </td>
                  <td className="p-3"><RiskTierPill tier={p.riskTier} /></td>
                  <td className="p-3 font-medium text-ink-primary">₹{p.premium}</td>
                  <td className="p-3 text-ink-muted">{p.lastPayout}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[p.status]}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        p.status === "active" ? "bg-green-500" : p.status === "suspended" ? "bg-red-500" : "bg-amber-500"
                      }`} />
                      {p.status.charAt(0).toUpperCase() + p.status.slice(1)}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex gap-1">
                      <button className="p-1.5 rounded-lg hover:bg-surface transition" title="View"><Eye className="w-4 h-4 text-ink-muted" /></button>
                      <button className="p-1.5 rounded-lg hover:bg-red-50 transition" title="Suspend"><Ban className="w-4 h-4 text-red-400" /></button>
                      <button className="p-1.5 rounded-lg hover:bg-amber-50 transition" title="Flag"><Flag className="w-4 h-4 text-amber" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
          <div className="flex items-center gap-2 text-sm text-ink-muted">
            <span>Rows:</span>
            <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1); }}
              className="h-8 px-2 rounded border border-gray-200 text-sm outline-none">
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-ink-muted">
              Page {page} of {totalPages}
            </span>
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
              className="p-1.5 rounded-lg hover:bg-surface disabled:opacity-30 transition">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
              className="p-1.5 rounded-lg hover:bg-surface disabled:opacity-30 transition">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
