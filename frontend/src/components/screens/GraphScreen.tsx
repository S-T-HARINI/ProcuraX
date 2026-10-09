"use client";

import React, { useState } from "react";
import {
  GitGraph,
  FileText,
  Building2,
  AlertTriangle,
  CircleDollarSign,
  ShieldAlert,
  Info,
  Layers,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { GraphEdge, GraphNode, GraphResponse } from "@/types/procurement";

interface GraphScreenProps {
  graphData: GraphResponse;
}

const nodeTypeColors: Record<string, { bg: string; text: string; border: string }> = {
  document: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  claim: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  supplier: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  cost: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  risk: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  conflict: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  allocation: { bg: "bg-cyan-50", text: "text-cyan-700", border: "border-cyan-200" },
  recommendation: { bg: "bg-violet-900", text: "text-white", border: "border-violet-700" },
};

export function GraphScreen({ graphData }: GraphScreenProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterType, setFilterType] = useState<string>("ALL");

  const filteredNodes = graphData.nodes.filter(
    (n) => filterType === "ALL" || n.type === filterType
  );

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen text-slate-800">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <GitGraph className="w-5 h-5 text-indigo-600" />
            Evidence-to-Decision Lineage Graph
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Visual graph mapping source quotation documents, extracted claims, landed costs, risk factors, and sourcing decisions.
          </p>
        </div>

        {/* Node Filter Selector */}
        <div className="flex items-center space-x-2 overflow-x-auto">
          <span className="text-xs font-semibold text-slate-400">Filter Node:</span>
          {["ALL", "document", "claim", "supplier", "cost", "risk", "recommendation"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                filterType === type
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Main Graph Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Interactive Node Map */}
        <div className="lg:col-span-2 bg-slate-950 p-6 rounded-2xl border border-slate-800 text-white min-h-[500px] flex flex-col justify-between relative overflow-hidden">
          {/* Node Map Grid */}
          <div className="space-y-6 z-10">
            <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800 pb-3">
              <span className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                Lineage Nodes ({filteredNodes.length}) & Edges ({graphData.edges.length})
              </span>
              <span>Click node to inspect evidence lineage</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[420px] overflow-y-auto pr-2">
              {filteredNodes.map((node) => {
                const style = nodeTypeColors[node.type] || {
                  bg: "bg-slate-800",
                  text: "text-slate-200",
                  border: "border-slate-700",
                };
                const isSelected = selectedNode?.id === node.id;

                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all duration-150 ${
                      isSelected
                        ? "ring-2 ring-indigo-500 scale-[1.02] shadow-lg shadow-indigo-500/20"
                        : "hover:border-indigo-500/50"
                    } ${style.bg} ${style.border}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-[10px] font-bold uppercase tracking-wider ${style.text}`}>
                        {node.type}
                      </span>
                      <span className="text-[10px] text-slate-400">{node.id.split(":")[0]}</span>
                    </div>
                    <h5 className={`font-bold text-xs mt-1.5 ${node.type === "recommendation" ? "text-white" : "text-slate-900"}`}>
                      {node.label}
                    </h5>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Graph Legend Footer */}
          <div className="pt-4 border-t border-slate-800 flex flex-wrap gap-3 text-[11px] text-slate-400 z-10">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span> Document
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-400"></span> Claim
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400"></span> Supplier
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Risk
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-violet-500"></span> Decision
            </span>
          </div>
        </div>

        {/* Right Node Evidence Inspector Panel */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <h4 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Info className="w-4 h-4 text-indigo-600" />
            Node Lineage Inspector
          </h4>

          {selectedNode ? (
            <div className="space-y-4 text-xs animate-in fade-in duration-200">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">
                  Node Type: {selectedNode.type}
                </span>
                <h5 className="font-bold text-slate-900 text-sm">{selectedNode.label}</h5>
                <p className="text-[11px] text-slate-400 font-mono">ID: {selectedNode.id}</p>
              </div>

              {/* Properties Display */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Attributes & Lineage Audit
                </span>
                <div className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-[11px] space-y-1.5 overflow-x-auto">
                  {Object.entries(selectedNode.properties).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-indigo-400">{k}:</span>
                      <span className="text-slate-200">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Edge Connections */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Connected Lineage Edges
                </span>
                <div className="space-y-1.5">
                  {graphData.edges
                    .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                    .map((edge, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-700 flex justify-between">
                        <span className="font-semibold text-blue-600">{edge.label || edge.relation_type}</span>
                        <span className="text-slate-400 truncate max-w-[140px]">
                          {edge.source === selectedNode.id ? `→ ${edge.target}` : `← ${edge.source}`}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-slate-400 space-y-2">
              <GitGraph className="w-10 h-10 mx-auto opacity-40 text-slate-400" />
              <p className="text-xs">Click any node in the lineage map to inspect document citations and evidence properties.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
