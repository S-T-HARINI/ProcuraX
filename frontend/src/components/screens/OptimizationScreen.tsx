"use client";

import React, { useState } from "react";
import {
  SlidersHorizontal,
  Play,
  CheckCircle2,
  AlertTriangle,
  CircleDollarSign,
  Building2,
  PieChart,
  Loader2,
  Info,
} from "lucide-react";
import { ApiClient } from "@/lib/apiClient";
import { OptimizationResponse, SupplierQuote } from "@/types/procurement";

interface OptimizationScreenProps {
  suppliers: SupplierQuote[];
}

export function OptimizationScreen({ suppliers }: OptimizationScreenProps) {
  const [demand, setDemand] = useState<number>(500);
  const [budget, setBudget] = useState<string>("50000");
  const [isSolving, setIsSolving] = useState(false);
  const [optResult, setOptResult] = useState<OptimizationResponse | null>(null);

  const handleSolve = async () => {
    setIsSolving(true);
    try {
      const budgetNum = budget ? parseFloat(budget) : null;
      const res = await ApiClient.optimizeSourcing(suppliers, demand, budgetNum);
      setOptResult(res);
    } catch (err) {
      alert("Optimization solver error: " + String(err));
    } finally {
      setIsSolving(false);
    }
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen text-slate-800">
      {/* Optimization Input Controls Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div>
          <h3 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <SlidersHorizontal className="w-5 h-5 text-blue-600" />
            MILP Sourcing Allocation Optimizer
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Specify target procurement demand and optional budget limits. The MILP solver minimizes total landed cost
            while respecting supplier MOQ and monthly capacity constraints.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Required Target Demand (Units)
            </label>
            <input
              type="number"
              min={1}
              value={demand}
              onChange={(e) => setDemand(parseInt(e.target.value) || 0)}
              className="w-full px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Max Budget Constraint (Optional INR ₹)
            </label>
            <input
              type="text"
              placeholder="e.g. 50000"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="w-full px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <button
            onClick={handleSolve}
            disabled={isSolving || demand <= 0}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:opacity-95 text-white font-bold text-sm shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            {isSolving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Solving MILP Model...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Run Sourcing Solver</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Solver Results Section */}
      {optResult && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {/* Status Banner */}
          <div
            className={`p-6 rounded-2xl border flex items-center justify-between shadow-sm ${
              optResult.status === "optimal"
                ? "bg-emerald-50/80 border-emerald-200 text-emerald-900"
                : "bg-rose-50/80 border-rose-200 text-rose-900"
            }`}
          >
            <div className="flex items-center space-x-4">
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  optResult.status === "optimal" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                }`}
              >
                {optResult.status === "optimal" ? (
                  <CheckCircle2 className="w-6 h-6" />
                ) : (
                  <AlertTriangle className="w-6 h-6" />
                )}
              </div>
              <div>
                <h4 className="text-lg font-bold">
                  Solver Status: {optResult.status.toUpperCase()}
                </h4>
                <p className="text-xs opacity-90">
                  {optResult.explanations?.[0] || "Allocation model solved successfully."}
                </p>
              </div>
            </div>

            <div className="text-right">
              <div className="text-2xl font-bold">
                {optResult.total_landed_cost
                  ? `₹${optResult.total_landed_cost.toLocaleString()}`
                  : "N/A"}
              </div>
              <div className="text-xs opacity-80">Total Landed Cost</div>
            </div>
          </div>

          {/* Allocation Results Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h4 className="text-base font-bold text-slate-900">Optimal Supplier Allocation Breakdown</h4>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                    <th className="p-3">Supplier Name</th>
                    <th className="p-3">Allocated Qty</th>
                    <th className="p-3">Effective Unit Price</th>
                    <th className="p-3">Unit Freight Cost</th>
                    <th className="p-3">Total Landed Cost</th>
                    <th className="p-3">Capacity Utilization</th>
                    <th className="p-3">Share of Demand</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {optResult.allocations.map((alloc) => (
                    <tr key={alloc.supplier_id} className="hover:bg-slate-50/80">
                      <td className="p-3 font-bold text-slate-900">
                        {alloc.supplier_name}
                        <span className="block text-[10px] text-slate-400 font-normal">
                          {alloc.supplier_id}
                        </span>
                      </td>
                      <td className="p-3 font-bold text-blue-600 text-sm">
                        {alloc.allocated_quantity} units
                      </td>
                      <td className="p-3 text-slate-700">
                        ₹{alloc.effective_unit_price || alloc.cost_breakdown?.unit_price || "-"}
                      </td>
                      <td className="p-3 text-slate-700">
                        ₹{alloc.unit_transport_cost || alloc.cost_breakdown?.transport_cost || "-"}
                      </td>
                      <td className="p-3 font-bold text-slate-900">
                        ₹{alloc.landed_cost?.toLocaleString() || alloc.cost_breakdown?.total_landed_cost?.toLocaleString() || "-"}
                      </td>
                      <td className="p-3">
                        <div className="w-32 space-y-1">
                          <div className="flex justify-between text-[10px] text-slate-500">
                            <span>{alloc.capacity_utilization_pct || 0}%</span>
                            <span>Cap: {alloc.capacity || "N/A"}</span>
                          </div>
                          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-600 rounded-full"
                              style={{ width: `${Math.min(100, alloc.capacity_utilization_pct || 0)}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3 font-semibold text-slate-700">
                        {alloc.share_of_demand_pct || 0}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
