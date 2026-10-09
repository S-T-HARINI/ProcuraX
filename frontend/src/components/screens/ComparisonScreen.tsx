"use client";

import React, { useState } from "react";
import {
  Building2,
  SlidersHorizontal,
  ArrowUpDown,
  Search,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  X,
  ShieldAlert,
  Leaf,
} from "lucide-react";
import { SupplierQuote } from "@/types/procurement";

interface ComparisonScreenProps {
  suppliers: SupplierQuote[];
}

export function ComparisonScreen({ suppliers }: ComparisonScreenProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<"unit_price" | "capacity" | "moq">("unit_price");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierQuote | null>(null);

  const filteredSuppliers = suppliers
    .filter(
      (s) =>
        s.supplier_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.supplier_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.product_name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      const valA = a[sortField] ?? 999999;
      const valB = b[sortField] ?? 999999;
      return sortOrder === "asc" ? valA - valB : valB - valA;
    });

  const toggleSort = (field: "unit_price" | "capacity" | "moq") => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen text-slate-800">
      {/* Search & Sort Controls */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Filter suppliers by name or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto overflow-x-auto">
          <span className="text-xs font-semibold text-slate-400">Sort by:</span>
          <button
            onClick={() => toggleSort("unit_price")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center space-x-1 ${
              sortField === "unit_price"
                ? "bg-blue-50 text-blue-700 border-blue-200"
                : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
            }`}
          >
            <span>Unit Price</span>
            <ArrowUpDown className="w-3 h-3" />
          </button>
          <button
            onClick={() => toggleSort("capacity")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center space-x-1 ${
              sortField === "capacity"
                ? "bg-blue-50 text-blue-700 border-blue-200"
                : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
            }`}
          >
            <span>Capacity</span>
            <ArrowUpDown className="w-3 h-3" />
          </button>
          <button
            onClick={() => toggleSort("moq")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center space-x-1 ${
              sortField === "moq"
                ? "bg-blue-50 text-blue-700 border-blue-200"
                : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
            }`}
          >
            <span>MOQ</span>
            <ArrowUpDown className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Supplier Comparison Matrix Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="p-4">Supplier & Product</th>
                <th className="p-4">Unit Price</th>
                <th className="p-4">Freight Rate</th>
                <th className="p-4">Est. Landed Rate</th>
                <th className="p-4">MOQ</th>
                <th className="p-4">Capacity</th>
                <th className="p-4">Lead Time</th>
                <th className="p-4">Sustainability</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredSuppliers.map((s) => {
                const landedUnit = (s.unit_price || 0) + (s.transport_cost || 0) / (s.capacity || 1);
                const hasMissing = s.missing_fields.length > 0;
                const hasConflict = (s.conflicting_fields || []).length > 0;

                return (
                  <tr key={s.supplier_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-bold text-slate-900">
                      <div>{s.supplier_name}</div>
                      <div className="text-[11px] font-normal text-slate-400">
                        {s.supplier_id} • {s.product_name}
                      </div>
                    </td>
                    <td className="p-4 font-semibold text-slate-900">
                      {s.unit_price ? `₹${s.unit_price.toFixed(2)}` : <span className="text-amber-600">null</span>}
                    </td>
                    <td className="p-4 text-slate-700">
                      {s.transport_cost ? `₹${s.transport_cost.toFixed(2)}` : <span className="text-rose-600 font-medium">Missing</span>}
                    </td>
                    <td className="p-4 font-bold text-blue-600">
                      ₹{landedUnit.toFixed(2)} / unit
                    </td>
                    <td className="p-4 text-slate-700">{s.moq ?? "N/A"}</td>
                    <td className="p-4 text-slate-700">{s.capacity ? `${s.capacity} units` : "N/A"}</td>
                    <td className="p-4 text-slate-700">
                      {s.delivery_days ? `${s.delivery_days} days` : <span className="text-amber-600">Ambiguous</span>}
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap gap-1">
                        {s.sustainability_claims.map((claim, i) => (
                          <span key={i} className="inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <Leaf className="w-2.5 h-2.5" />
                            <span>{claim}</span>
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="p-4">
                      {hasConflict ? (
                        <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Conflicting</span>
                        </span>
                      ) : hasMissing ? (
                        <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                          <HelpCircle className="w-3 h-3" />
                          <span>Incomplete</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle className="w-3 h-3" />
                          <span>Verified</span>
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => setSelectedSupplier(s)}
                        className="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold text-xs transition-colors"
                      >
                        Inspect Claims
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Supplier Detail Slide-Over Drawer */}
      {selectedSupplier && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex justify-end">
          <div className="w-full max-w-md bg-white h-full shadow-2xl p-6 overflow-y-auto space-y-6 animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">{selectedSupplier.supplier_name}</h3>
                <p className="text-xs text-slate-500">ID: {selectedSupplier.supplier_id}</p>
              </div>
              <button
                onClick={() => setSelectedSupplier(null)}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Claims & Source Citations */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Grounded Claims & Source Citations
              </h4>

              {selectedSupplier.claims.map((claim, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-slate-800 uppercase">{claim.field}</span>
                    <span className="text-blue-600 font-semibold">
                      {claim.value !== null ? String(claim.value) : "null"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 italic">"{claim.source_excerpt}"</p>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-200/60">
                    <span>Source: {claim.source_file}</span>
                    <span>Page {claim.source_page || "1"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
