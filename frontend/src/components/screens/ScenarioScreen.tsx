"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Play,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Building2,
  RefreshCw,
} from "lucide-react";
import { ApiClient } from "@/lib/apiClient";
import { OptimizationResponse, SupplierQuote } from "@/types/procurement";

interface ScenarioScreenProps {
  suppliers: SupplierQuote[];
}

export function ScenarioScreen({ suppliers }: ScenarioScreenProps) {
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>("SUP-001");
  const [priceHikePct, setPriceHikePct] = useState<number>(15);
  const [capacityCutPct, setCapacityCutPct] = useState<number>(50);
  const [demand, setDemand] = useState<number>(500);

  const [baselineOpt, setBaselineOpt] = useState<OptimizationResponse | null>(null);
  const [scenarioOpt, setScenarioOpt] = useState<OptimizationResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const runSimulation = async () => {
    setIsSimulating(true);
    try {
      // Baseline run
      const base = await ApiClient.optimizeSourcing(suppliers, demand);
      setBaselineOpt(base);

      // Scenario run
      const scen = await ApiClient.optimizeSourcing(suppliers, demand, null, {
        supplier_id: selectedSupplierId,
        price_hike: priceHikePct,
        cap_cut: capacityCutPct,
      });
      setScenarioOpt(scen);
    } catch (err) {
      alert("Scenario simulation error: " + String(err));
    } finally {
      setIsSimulating(false);
    }
  };

  const costDelta =
    baselineOpt?.total_landed_cost && scenarioOpt?.total_landed_cost
      ? scenarioOpt.total_landed_cost - baselineOpt.total_landed_cost
      : 0;

  const costDeltaPct =
    baselineOpt?.total_landed_cost && costDelta
      ? Math.round((costDelta / baselineOpt.total_landed_cost) * 1000) / 10
      : 0;

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen text-slate-800">
      {/* Control Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div>
          <h3 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-violet-600" />
            Procurement What-If Risk & Cost Simulator
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Simulate supplier price increases and capacity disruptions. Real-time MILP recalculation compares baseline vs scenario spend.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Target Supplier
            </label>
            <select
              value={selectedSupplierId}
              onChange={(e) => setSelectedSupplierId(e.target.value)}
              className="w-full px-3 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-900 focus:outline-none"
            >
              {suppliers.map((s) => (
                <option key={s.supplier_id} value={s.supplier_id}>
                  {s.supplier_id} — {s.supplier_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Price Increase (+%)
            </label>
            <input
              type="number"
              min={0}
              max={200}
              value={priceHikePct}
              onChange={(e) => setPriceHikePct(parseInt(e.target.value) || 0)}
              className="w-full px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Capacity Reduction (-%)
            </label>
            <input
              type="number"
              min={0}
              max={100}
              value={capacityCutPct}
              onChange={(e) => setCapacityCutPct(parseInt(e.target.value) || 0)}
              className="w-full px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl font-bold text-slate-900"
            />
          </div>

          <button
            onClick={runSimulation}
            disabled={isSimulating}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:opacity-95 text-white font-bold text-sm shadow-lg shadow-violet-600/30 transition-all flex items-center justify-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${isSimulating ? "animate-spin" : ""}`} />
            <span>Simulate Disruption</span>
          </button>
        </div>
      </div>

      {/* Simulation Results Display */}
      {baselineOpt && scenarioOpt && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {/* Comparison Delta Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Baseline Landed Cost
              </span>
              <div className="text-2xl font-bold text-slate-900">
                ₹{baselineOpt.total_landed_cost?.toLocaleString()}
              </div>
              <p className="text-xs text-slate-500">Normal operating conditions</p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Scenario Landed Cost
              </span>
              <div className="text-2xl font-bold text-violet-600">
                ₹{scenarioOpt.total_landed_cost?.toLocaleString()}
              </div>
              <p className="text-xs text-slate-500">Post-disruption MILP allocation</p>
            </div>

            <div className={`p-6 rounded-2xl border shadow-sm space-y-2 ${
              costDelta > 0 ? "bg-rose-50 border-rose-200 text-rose-900" : "bg-emerald-50 border-emerald-200 text-emerald-900"
            }`}>
              <span className="text-xs font-bold uppercase tracking-wider opacity-80">
                Cost Impact Delta
              </span>
              <div className="text-2xl font-bold flex items-baseline gap-2">
                <span>{costDelta > 0 ? `+₹${costDelta.toLocaleString()}` : `₹${costDelta.toLocaleString()}`}</span>
                <span className="text-sm font-semibold">({costDeltaPct}%)</span>
              </div>
              <p className="text-xs opacity-90">
                {costDelta > 0 ? "Additional budget required" : "Savings achieved under scenario"}
              </p>
            </div>
          </div>

          {/* Narrative Explanation */}
          <div className="bg-slate-900 text-white p-6 rounded-2xl border border-slate-800 space-y-2">
            <h4 className="text-sm font-bold text-violet-400 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Scenario Impact Narrative Synthesis
            </h4>
            <p className="text-sm text-slate-200">
              Applying a <span className="text-violet-300 font-semibold">+{priceHikePct}% price increase</span> and{" "}
              <span className="text-amber-300 font-semibold">-{capacityCutPct}% capacity reduction</span> to{" "}
              <span className="font-bold text-white">{selectedSupplierId}</span> changes total landed cost from ₹
              {baselineOpt.total_landed_cost?.toLocaleString()} to ₹{scenarioOpt.total_landed_cost?.toLocaleString()} (
              {costDeltaPct > 0 ? `+${costDeltaPct}%` : `${costDeltaPct}%`}).
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
