"use client";

import React from "react";
import {
  LayoutDashboard,
  FileUp,
  Building2,
  SlidersHorizontal,
  GitGraph,
  Sparkles,
  ShieldAlert,
  Radio,
} from "lucide-react";

export type ScreenId =
  | "dashboard"
  | "upload"
  | "comparison"
  | "optimization"
  | "graph"
  | "scenarios"
  | "evidence";

interface SidebarProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
  isBackendLive: boolean;
  isDemoMode: boolean;
  onToggleDemoMode: (enabled: boolean) => void;
}

export function Sidebar({
  currentScreen,
  onSelectScreen,
  isBackendLive,
  isDemoMode,
  onToggleDemoMode,
}: SidebarProps) {
  const navItems: { id: ScreenId; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: "upload", label: "Quotation Upload", icon: <FileUp className="w-5 h-5" />, badge: "AI" },
    { id: "comparison", label: "Supplier Comparison", icon: <Building2 className="w-5 h-5" /> },
    { id: "optimization", label: "Allocation Optimizer", icon: <SlidersHorizontal className="w-5 h-5" /> },
    { id: "graph", label: "Evidence Lineage Graph", icon: <GitGraph className="w-5 h-5" /> },
    { id: "scenarios", label: "Scenario Simulator", icon: <Sparkles className="w-5 h-5" /> },
    { id: "evidence", label: "Evidence & Audit", icon: <ShieldAlert className="w-5 h-5" /> },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between h-screen sticky top-0 text-slate-200 select-none z-20">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800/80 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <span className="font-extrabold text-white text-xl tracking-wider">X</span>
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
              ProcuraX
              <span className="text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                v0.1
              </span>
            </h1>
            <p className="text-xs text-slate-400">Procurement Intelligence</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-1.5">
          <div className="px-3 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Workspace
          </div>
          {navItems.map((item) => {
            const isActive = currentScreen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectScreen(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <span className={isActive ? "text-white" : "text-slate-400"}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      isActive
                        ? "bg-white/20 text-white"
                        : "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Backend & Mode Status Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-900/50 space-y-3">
        {/* Backend Status Indicator */}
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs">
          <div className="flex items-center space-x-2">
            <Radio
              className={`w-3.5 h-3.5 animate-pulse ${
                isBackendLive ? "text-emerald-400" : "text-amber-400"
              }`}
            />
            <span className="text-slate-300 font-medium">FastAPI Backend</span>
          </div>
          <span
            className={`font-semibold text-[11px] px-2 py-0.5 rounded-full ${
              isBackendLive
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            }`}
          >
            {isBackendLive ? "Live API" : "Demo Fallback"}
          </span>
        </div>

        {/* Demo Mode Toggle */}
        <div className="flex items-center justify-between px-3 py-2 text-xs">
          <span className="text-slate-400 font-medium">Demo Mode</span>
          <button
            onClick={() => onToggleDemoMode(!isDemoMode)}
            className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              isDemoMode ? "bg-blue-600" : "bg-slate-700"
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                isDemoMode ? "translate-x-4" : "translate-x-0"
              }`}
            />
          </button>
        </div>
      </div>
    </aside>
  );
}
