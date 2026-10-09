"use client";

import React from "react";
import { Search, Bell, Cpu, ShieldCheck } from "lucide-react";
import { ScreenId } from "./Sidebar";

interface HeaderProps {
  currentScreen: ScreenId;
  isBackendLive: boolean;
  isDemoMode: boolean;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

const titles: Record<ScreenId, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Procurement Overview & Analytics",
    subtitle: "Real-time cost intelligence, supplier benchmarking, and risk monitoring",
  },
  upload: {
    title: "Quotation Document Parsing & Extraction",
    subtitle: "Upload PDF, CSV, or XLSX supplier quotes for Gemma 4 evidence extraction",
  },
  comparison: {
    title: "Supplier Quotation Benchmark Matrix",
    subtitle: "Compare unit prices, transport rates, capacities, and sustainability claims",
  },
  optimization: {
    title: "Sourcing Allocation & Landed-Cost Optimizer",
    subtitle: "Solve MILP procurement allocation under demand, MOQ, capacity, and budget limits",
  },
  graph: {
    title: "Evidence-to-Decision Consistency Lineage Graph",
    subtitle: "Visual graph connecting source documents, extracted claims, landed costs, and allocations",
  },
  scenarios: {
    title: "Procurement What-If Risk & Cost Simulator",
    subtitle: "Simulate price increases, transport spikes, and capacity disruption scenarios",
  },
  evidence: {
    title: "Evidence Verification & Claim Audit Log",
    subtitle: "Audit source filenames, page citations, verbatim passages, and missing fields",
  },
};

export function Header({
  currentScreen,
  isBackendLive,
  isDemoMode,
  searchQuery,
  onSearchChange,
}: HeaderProps) {
  const meta = titles[currentScreen] || {
    title: "Procurement Intelligence",
    subtitle: "Evidence-Driven Procurement Platform",
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-10">
      <div>
        <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
          {meta.title}
          {isDemoMode && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200">
              Synthetic Demo Data
            </span>
          )}
        </h2>
        <p className="text-xs text-slate-500">{meta.subtitle}</p>
      </div>

      <div className="flex items-center space-x-4">
        {/* Global Search Bar */}
        <div className="relative w-64">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search suppliers, claims, files..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />
        </div>

        {/* Engine Status Badge */}
        <div className="flex items-center space-x-2 text-xs px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200">
          <Cpu className="w-4 h-4 text-blue-600" />
          <span className="text-slate-600 font-medium">Model:</span>
          <span className="font-semibold text-slate-800">
            {isBackendLive ? "Gemma 4 (Local/E2B)" : "Gemma 4 (Simulated Demo)"}
          </span>
        </div>

        {/* System Verified Badge */}
        <div className="p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-blue-600 ring-2 ring-white"></span>
        </div>
      </div>
    </header>
  );
}
