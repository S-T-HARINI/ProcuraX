import {
  GraphResponse,
  OptimizationResponse,
  SupplierQuote,
  WorkflowResponse,
} from "@/types/procurement";
import { DEMO_SUPPLIERS, getDemoGraph } from "./demoData";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface HealthCheckResult {
  isBackendLive: boolean;
  status?: string;
  service?: string;
  version?: string;
}

export interface DocumentParseResult {
  filename: string;
  file_type: string;
  total_pages: number;
  pages: { page_number: number; text: string }[];
  raw_text: string;
}

export interface ExtractClaimsResult {
  suppliers: SupplierQuote[];
  missing_fields_summary?: string[];
  conflicts_summary?: string[];
  is_mock?: boolean;
  message?: string;
}

export interface ScenarioParams {
  supplier_id?: string;
  price_hike?: number;
  cap_cut?: number;
}

class ApiClientClass {
  private demoModeEnabled: boolean = false;

  constructor() {
    if (typeof window !== "undefined") {
      this.demoModeEnabled =
        localStorage.getItem("procurax_demo_mode") === "true";
    }
  }

  /**
   * Toggle simulated demo mode vs live backend calls.
   */
  public setDemoMode(enabled: boolean): void {
    this.demoModeEnabled = enabled;
    if (typeof window !== "undefined") {
      localStorage.setItem("procurax_demo_mode", String(enabled));
    }
  }

  public isDemoMode(): boolean {
    return this.demoModeEnabled;
  }

  /**
   * Check whether FastAPI backend is responsive on /api/health.
   */
  public async checkHealth(): Promise<HealthCheckResult> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);

      const res = await fetch(`${API_BASE_URL}/api/health`, {
        method: "GET",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        return {
          isBackendLive: true,
          status: data.status,
          service: data.service,
          version: data.version,
        };
      }
    } catch {
      // Backend is unreachable
    }
    return {
      isBackendLive: false,
      status: "offline",
    };
  }

  /**
   * Upload supplier quotation file (PDF, CSV, XLSX) to backend.
   */
  public async uploadDocument(file: File): Promise<DocumentParseResult> {
    if (this.demoModeEnabled) {
      return this.simulateDocumentParse(file);
    }

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorDetail = await res.text();
        throw new Error(`Upload failed (${res.status}): ${errorDetail}`);
      }

      return await res.json();
    } catch (err) {
      console.warn("Backend upload failed, using fallback parser:", err);
      return this.simulateDocumentParse(file);
    }
  }

  /**
   * Run Gemma 4 extraction on pre-parsed quotation text.
   */
  public async extractClaims(
    filename: string,
    rawText: string,
    useMock: boolean = false,
    model: string = "gemma4:e2b"
  ): Promise<ExtractClaimsResult> {
    if (this.demoModeEnabled || useMock) {
      return {
        suppliers: DEMO_SUPPLIERS,
        missing_fields_summary: ["SUP-002: missing delivery_days, transport_cost"],
        conflicts_summary: ["SUP-003: conflicting unit_price"],
        is_mock: true,
        message: "Extracted using demo supplier profiles.",
      };
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename,
          raw_text: rawText,
          use_mock: useMock,
          model,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Extraction failed (${res.status}): ${errText}`);
      }

      return await res.json();
    } catch (err) {
      console.warn("Live extraction failed, falling back to demo suppliers:", err);
      return {
        suppliers: DEMO_SUPPLIERS,
        missing_fields_summary: ["SUP-002: missing delivery_days, transport_cost"],
        conflicts_summary: ["SUP-003: conflicting unit_price"],
        is_mock: true,
        message: `Extraction fallback triggered: ${String(err)}`,
      };
    }
  }

  /**
   * Run MILP optimization under demand, capacity, MOQ, and scenario constraints.
   */
  public async optimizeSourcing(
    suppliers: SupplierQuote[],
    targetDemand: number,
    budgetLimit?: number | null,
    scenarioParams?: ScenarioParams | null
  ): Promise<OptimizationResponse> {
    let scenarioPayload: any = null;
    if (scenarioParams) {
      const hike = Number(scenarioParams.price_hike) || 0;
      const cut = Number(scenarioParams.cap_cut) || 0;
      const supplierId = scenarioParams.supplier_id || null;

      if (hike > 0 && cut > 0) {
        scenarioPayload = {
          type: "compound",
          supplier_id: supplierId,
          scenarios: [
            { type: "price_increase", supplier_id: supplierId, percentage: hike },
            { type: "capacity_reduction", supplier_id: supplierId, percentage: cut },
          ],
        };
      } else if (cut > 0) {
        scenarioPayload = {
          type: "capacity_reduction",
          supplier_id: supplierId,
          percentage: cut,
        };
      } else if (hike > 0) {
        scenarioPayload = {
          type: "price_increase",
          supplier_id: supplierId,
          percentage: hike,
        };
      }
    }

    if (!this.demoModeEnabled) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/optimize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            suppliers,
            target_demand: targetDemand,
            budget_limit: budgetLimit ?? null,
            scenario: scenarioPayload,
          }),
        });

        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn("Backend optimization call failed, running local simulator:", err);
      }
    }

    // Client-side fallback solver for demo mode or offline development
    return this.simulateOptimization(suppliers, targetDemand, budgetLimit, scenarioParams);
  }

  /**
   * Request evidence-to-decision lineage graph from backend.
   */
  public async generateGraph(
    suppliers: SupplierQuote[],
    optimizationResult?: any,
    scenarioImpact?: any
  ): Promise<GraphResponse> {
    if (!this.demoModeEnabled) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/graph`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            suppliers,
            optimization_result: optimizationResult,
            scenario_impact: scenarioImpact,
          }),
        });

        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn("Backend graph generation failed, using demo graph:", err);
      }
    }

    return getDemoGraph();
  }

  /**
   * Run end-to-end ProcuraX workflow pipeline.
   */
  public async runWorkflow(
    documentFilename: string = "supplier_quotation.pdf",
    documentText?: string,
    targetDemand: number = 500,
    budgetLimit?: number | null,
    scenarioParams?: ScenarioParams | null,
    useMockExtraction: boolean = false
  ): Promise<WorkflowResponse> {
    const res = await fetch(`${API_BASE_URL}/api/workflow`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_filename: documentFilename,
        document_text: documentText,
        target_demand: targetDemand,
        budget_limit: budgetLimit ?? null,
        scenario: scenarioParams ? { type: "price_increase", ...scenarioParams } : null,
        use_mock_extraction: useMockExtraction,
      }),
    });

    if (!res.ok) {
      throw new Error(`Workflow execution failed (${res.status})`);
    }

    return await res.json();
  }

  /**
   * Helper simulating text parsing for demo uploads.
   */
  private async simulateDocumentParse(file: File): Promise<DocumentParseResult> {
    let rawText = "";
    try {
      if (file.name.endsWith(".csv") || file.name.endsWith(".txt")) {
        rawText = await file.text();
      }
    } catch {
      // Ignored
    }

    if (!rawText.trim()) {
      rawText = `[Quotation Document: ${file.name}]\nSupplier: Apex Sustainable Packaging Ltd.\nItem: Reusable Industrial Bottle (500ml)\nUnit Price: 80.00 INR\nMOQ: 100 units\nCapacity: 600 units\nDelivery: 5 business days\nFreight: 500.00 INR`;
    }

    return {
      filename: file.name,
      file_type: file.type || "application/octet-stream",
      total_pages: 1,
      pages: [{ page_number: 1, text: rawText }],
      raw_text: rawText,
    };
  }

  /**
   * Deterministic client-side MILP simulation when backend is offline.
   */
  private simulateOptimization(
    suppliers: SupplierQuote[],
    demand: number,
    budget?: number | null,
    scenarioParams?: ScenarioParams | null
  ): OptimizationResponse {
    let remainingDemand = demand;
    const allocations: any[] = [];
    let totalLandedCost = 0;

    // Sort suppliers by unit price ascending
    const sorted = [...suppliers].sort(
      (a, b) => (a.unit_price || 9999) - (b.unit_price || 9999)
    );

    for (const supp of sorted) {
      if (remainingDemand <= 0) break;

      let effectivePrice = supp.unit_price || 0;
      let effectiveCapacity = supp.capacity || 0;

      // Apply scenario multipliers if targeted
      if (scenarioParams && scenarioParams.supplier_id === supp.supplier_id) {
        if (scenarioParams.price_hike) {
          effectivePrice *= 1 + scenarioParams.price_hike / 100;
        }
        if (scenarioParams.cap_cut) {
          effectiveCapacity = Math.round(
            effectiveCapacity * (1 - scenarioParams.cap_cut / 100)
          );
        }
      }

      const moq = supp.moq || 0;
      if (remainingDemand < moq && remainingDemand > 0) {
        // Demand below MOQ
        continue;
      }

      const allocQty = Math.min(remainingDemand, effectiveCapacity);
      if (allocQty > 0) {
        const transport = supp.transport_cost || 0;
        const itemCost = allocQty * effectivePrice + transport;

        allocations.push({
          supplier_id: supp.supplier_id,
          supplier_name: supp.supplier_name,
          allocated_quantity: allocQty,
          capacity: effectiveCapacity,
          moq,
          share_of_demand_pct: Math.round((allocQty / demand) * 1000) / 10,
          cost_breakdown: {
            supplier_id: supp.supplier_id,
            supplier_name: supp.supplier_name,
            quantity: allocQty,
            unit_price: effectivePrice,
            base_cost: allocQty * effectivePrice,
            transport_cost: transport,
            total_landed_cost: itemCost,
            cost_per_unit: Math.round((itemCost / allocQty) * 100) / 100,
            currency: supp.currency || "INR",
          },
        });

        totalLandedCost += itemCost;
        remainingDemand -= allocQty;
      }
    }

    const totalAllocated = demand - remainingDemand;
    const isFeasible = remainingDemand === 0 && (!budget || totalLandedCost <= budget);

    return {
      status: isFeasible ? "optimal" : remainingDemand > 0 ? "partial" : "budget_exceeded",
      is_feasible: isFeasible,
      target_demand: demand,
      total_allocated_quantity: totalAllocated,
      unmet_demand: remainingDemand,
      total_landed_cost: Math.round(totalLandedCost * 100) / 100,
      currency: "INR",
      budget_limit: budget ?? null,
      budget_utilized_pct: budget ? Math.round((totalLandedCost / budget) * 1000) / 10 : null,
      allocations,
      unassigned_suppliers: suppliers
        .filter((s) => !allocations.some((a) => a.supplier_id === s.supplier_id))
        .map((s) => s.supplier_id),
      explanations: [
        `Allocated ${totalAllocated}/${demand} units across ${allocations.length} supplier(s).`,
        remainingDemand > 0
          ? `Unmet demand: ${remainingDemand} units due to capacity or MOQ constraints.`
          : "Full demand satisfied within supplier capacities.",
      ],
      is_mock: true,
      message: "Optimization simulated deterministically.",
    };
  }
}

export const ApiClient = new ApiClientClass();
