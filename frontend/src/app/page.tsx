"use client";

import React, { useEffect, useState } from "react";
import { Sidebar, ScreenId } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { DashboardScreen } from "@/components/screens/DashboardScreen";
import { UploadScreen } from "@/components/screens/UploadScreen";
import { ComparisonScreen } from "@/components/screens/ComparisonScreen";
import { OptimizationScreen } from "@/components/screens/OptimizationScreen";
import { GraphScreen } from "@/components/screens/GraphScreen";
import { ScenarioScreen } from "@/components/screens/ScenarioScreen";
import { EvidenceAuditScreen } from "@/components/screens/EvidenceAuditScreen";
import { ApiClient } from "@/lib/apiClient";
import { DEMO_SUPPLIERS, getDemoGraph } from "@/lib/demoData";
import { GraphResponse, SupplierQuote } from "@/types/procurement";

export default function Home() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>("dashboard");
  const [isBackendLive, setIsBackendLive] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [suppliers, setSuppliers] = useState<SupplierQuote[]>(DEMO_SUPPLIERS);
  const [graphData, setGraphData] = useState<GraphResponse>(getDemoGraph());

  useEffect(() => {
    async function checkBackend() {
      const health = await ApiClient.checkHealth();
      setIsBackendLive(health.isBackendLive);
    }
    checkBackend();
  }, []);

  const handleToggleDemoMode = (enabled: boolean) => {
    setIsDemoMode(enabled);
    ApiClient.setDemoMode(enabled);
  };

  const handleExtractionComplete = (newSuppliers: SupplierQuote[]) => {
    if (newSuppliers && newSuppliers.length > 0) {
      setSuppliers(newSuppliers);
    }
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case "dashboard":
        return <DashboardScreen suppliers={suppliers} onNavigate={setCurrentScreen} />;
      case "upload":
        return (
          <UploadScreen
            isBackendLive={isBackendLive}
            onExtractionComplete={handleExtractionComplete}
          />
        );
      case "comparison":
        return <ComparisonScreen suppliers={suppliers} />;
      case "optimization":
        return <OptimizationScreen suppliers={suppliers} />;
      case "graph":
        return <GraphScreen graphData={graphData} />;
      case "scenarios":
        return <ScenarioScreen suppliers={suppliers} />;
      case "evidence":
        return <EvidenceAuditScreen suppliers={suppliers} />;
      default:
        return <DashboardScreen suppliers={suppliers} onNavigate={setCurrentScreen} />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 font-sans antialiased overflow-hidden select-none">
      {/* Dark Navy Sidebar */}
      <Sidebar
        currentScreen={currentScreen}
        onSelectScreen={setCurrentScreen}
        isBackendLive={isBackendLive}
        isDemoMode={isDemoMode}
        onToggleDemoMode={handleToggleDemoMode}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col h-screen overflow-y-auto bg-slate-50">
        <Header
          currentScreen={currentScreen}
          isBackendLive={isBackendLive}
          isDemoMode={isDemoMode}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />
        <main className="flex-1">{renderScreen()}</main>
      </div>
    </div>
  );
}
