"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  FileText,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  Search,
  ExternalLink,
} from "lucide-react";
import { Claim, SupplierQuote } from "@/types/procurement";

interface EvidenceAuditScreenProps {
  suppliers: SupplierQuote[];
}

export function EvidenceAuditScreen({ suppliers }: EvidenceAuditScreenProps) {
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Aggregate all claims across all suppliers
  const allClaims: (Claim & { supplier_id: string; supplier_name: string })[] = [];
  suppliers.forEach((s) => {
    s.claims.forEach((c) => {
      allClaims.push({
        ...c,
        supplier_id: s.supplier_id,
        supplier_name: s.supplier_name,
      });
    });
  });

  const filteredClaims = allClaims.filter((c) => {
    const matchesStatus = filterStatus === "ALL" || c.status === filterStatus;
    const matchesSearch =
      c.field.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.source_file.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.source_excerpt.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.supplier_name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen text-slate-800">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-blue-600" />
            Evidence Verification & Claim Audit Log
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Audit extracted supplier claims against verbatim document excerpts and page references. Distinguishes extracted claims from verified facts.
          </p>
        </div>

        {/* Status Filters */}
        <div className="flex items-center space-x-2 overflow-x-auto">
          <span className="text-xs font-semibold text-slate-400">Filter Status:</span>
          {["ALL", "extracted", "verified", "conflicting", "ambiguous", "missing"].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                filterStatus === st
                  ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Claims Audit Log Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="p-4">Claim Field</th>
                <th className="p-4">Extracted Value</th>
                <th className="p-4">Supplier</th>
                <th className="p-4">Source Document & Citation</th>
                <th className="p-4">Verbatim Source Excerpt</th>
                <th className="p-4">Claim Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredClaims.map((claim, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="p-4 font-bold text-slate-900 uppercase">
                    {claim.field}
                  </td>
                  <td className="p-4 font-semibold text-blue-600">
                    {claim.value !== null ? String(claim.value) : <span className="text-amber-600">null</span>}
                  </td>
                  <td className="p-4 text-slate-800">
                    <span className="font-bold">{claim.supplier_name}</span>
                    <span className="block text-[10px] text-slate-400 font-normal">{claim.supplier_id}</span>
                  </td>
                  <td className="p-4 text-slate-600">
                    <div className="flex items-center space-x-1.5">
                      <FileText className="w-3.5 h-3.5 text-purple-600 flex-shrink-0" />
                      <span className="font-mono">{claim.source_file}</span>
                    </div>
                    <span className="text-[10px] text-slate-400">Page {claim.source_page || 1}</span>
                  </td>
                  <td className="p-4 max-w-md">
                    <p className="italic text-slate-600 bg-slate-50 p-2 rounded border border-slate-150 text-[11px]">
                      "{claim.source_excerpt}"
                    </p>
                  </td>
                  <td className="p-4">
                    <span
                      className={`inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${
                        claim.status === "conflicting"
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : claim.status === "ambiguous" || claim.status === "missing"
                          ? "bg-amber-50 text-amber-700 border-amber-200"
                          : claim.status === "verified"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-blue-50 text-blue-700 border-blue-200"
                      }`}
                    >
                      {claim.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
