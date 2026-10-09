"use client";

import React from "react";
import {
  Building2,
  FileCheck,
  CircleDollarSign,
  TrendingDown,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  HelpCircle,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { SupplierQuote } from "@/types/procurement";
import { ScreenId } from "../layout/Sidebar";

interface DashboardScreenProps {
  suppliers: SupplierQuote[];
  onNavigate: (screen: ScreenId) => void;
}

export function DashboardScreen({ suppliers, onNavigate }: DashboardScreenProps) {
  const chartData = suppliers.map((s) => ({
    name: s.supplier_id,
    fullName: s.supplier_name,
    unitPrice: s.unit_price || 0,
    transport: s.transport_cost || 0,
    landedRate: (s.unit_price || 0) + (s.transport_cost || 0) / (s.capacity || 1),
    capacity: s.capacity || 0,
    moq: s.moq || 0,
  }));

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen text-slate-800">
      {/* Top Banner Alert */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white rounded-2xl p-6 shadow-xl relative overflow-hidden flex items-center justify-between">
        <div className="space-y-2 max-w-2xl z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold border border-blue-400/30">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>ProcuraX Sourcing Intelligence Active</span>
          </div>
          <h3 className="text-2xl font-bold tracking-tight">
            Evidence-Driven Sourcing Recommendation Available
          </h3>
          <p className="text-sm text-slate-300">
            Analysis of 3 supplier quotations shows optimal landed cost for 500 units is{" "}
            <span className="font-bold text-white">₹40,500 INR</span>. Allocation concentrated with{" "}
            <span className="text-blue-300 font-semibold">Apex Sustainable Packaging Ltd.</span>
          </p>
        </div>
        <button
          onClick={() => onNavigate("optimization")}
          className="z-10 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm transition-all shadow-lg shadow-blue-600/40 flex items-center space-x-2"
        >
          <span>Run Optimization</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Metric 1 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Suppliers Analyzed
            </span>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-slate-900">{suppliers.length}</span>
            <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
              3 Quotes Validated
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">2 Complete • 1 Incomplete</p>
        </div>

        {/* Metric 2 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Optimal Landed Cost
            </span>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <CircleDollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-slate-900">₹40,500</span>
            <span className="text-xs font-semibold text-slate-500">for 500 units</span>
          </div>
          <p className="mt-2 text-xs text-slate-500">₹81.00 / unit effective landed rate</p>
        </div>

        {/* Metric 3 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Calculated Savings
            </span>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingDown className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-emerald-600">₹3,750</span>
            <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
              -8.5%
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">vs unoptimized average quote price</p>
        </div>

        {/* Metric 4 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Risk & Discrepancies
            </span>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-amber-600">2 Alerts</span>
            <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
              Requires Review
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">1 Missing Freight • 1 Price Conflict</p>
        </div>
      </div>

      {/* Main Grid: Charts & Risk Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Supplier Cost Comparison Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-base font-bold text-slate-900">
                Supplier Price & Freight Structure Benchmark
              </h4>
              <p className="text-xs text-slate-500">
                Comparison of base unit prices vs transport costs across evaluated suppliers
              </p>
            </div>
            <button
              onClick={() => onNavigate("comparison")}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700"
            >
              View Benchmark Matrix →
            </button>
          </div>

          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} unit=" ₹" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderRadius: "12px", border: "none", color: "#fff" }}
                  formatter={(value: any) => [`₹${value}`, ""]}
                />
                <Legend />
                <Bar dataKey="unitPrice" name="Unit Price (₹)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="transport" name="Freight Charge (₹)" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Column: Active Risk & Evidence Alerts */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <h4 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Evidence & Risk Audit Warnings
            </h4>
            <p className="text-xs text-slate-500 mt-1">
              Extracted claims requiring human procurement review
            </p>

            <div className="mt-4 space-y-3">
              {/* Alert 1 */}
              <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/80 space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold text-amber-800">
                  <span>SUP-002 (BlueWave Logistics)</span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px]">
                    MISSING FREIGHT
                  </span>
                </div>
                <p className="text-xs text-amber-700">
                  Freight cost omitted from quote. Landed cost calculated without shipping charges.
                </p>
              </div>

              {/* Alert 2 */}
              <div className="p-3.5 rounded-xl bg-rose-50/70 border border-rose-200/80 space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold text-rose-800">
                  <span>SUP-003 (GreenSource Mfg.)</span>
                  <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 text-[10px]">
                    PRICE CONFLICT
                  </span>
                </div>
                <p className="text-xs text-rose-700">
                  Standard quote states ₹85.00/unit, while rush dispatch clause states ₹95.00/unit.
                </p>
              </div>

              {/* Verified Notice */}
              <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200/80 space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold text-emerald-800">
                  <span>SUP-001 (Apex Sustainable Ltd.)</span>
                  <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px]">
                    VERIFIED QUOTE
                  </span>
                </div>
                <p className="text-xs text-emerald-700">
                  Full quotation verified with page citations and flat ₹500 freight rate.
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => onNavigate("evidence")}
            className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors text-center"
          >
            Audit All Evidence Citations
          </button>
        </div>
      </div>
    </div>
  );
}
