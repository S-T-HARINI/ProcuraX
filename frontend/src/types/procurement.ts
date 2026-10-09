export type ClaimStatus = "extracted" | "verified" | "conflicting" | "ambiguous" | "missing";

export interface Claim {
  field: string;
  value: string | number | boolean | null;
  source_file: string;
  source_page?: number | null;
  source_excerpt: string;
  status: ClaimStatus;
  is_verified_fact?: boolean;
  notes?: string;
}

export interface SupplierQuote {
  supplier_id: string;
  supplier_name: string;
  product_name: string;
  unit_price: number | null;
  currency: string;
  moq: number | null;
  capacity: number | null;
  delivery_days: number | null;
  transport_cost: number | null;
  discount_terms?: string | null;
  sustainability_claims: string[];
  missing_fields: string[];
  ambiguous_fields?: string[];
  conflicting_fields?: string[];
  claims: Claim[];
  metadata?: Record<string, any>;
}

export interface SupplierAllocation {
  supplier_id: string;
  supplier_name: string;
  allocated_quantity: number;
  effective_unit_price?: number;
  unit_transport_cost?: number;
  landed_cost?: number;
  cost_breakdown?: {
    supplier_id: string;
    supplier_name: string;
    quantity: number;
    unit_price?: number | null;
    base_cost?: number | null;
    transport_cost?: number | null;
    total_landed_cost?: number | null;
    cost_per_unit?: number | null;
    currency?: string;
  };
  capacity?: number | null;
  moq?: number | null;
  capacity_utilization_pct?: number;
  share_of_demand_pct?: number;
}

export interface OptimizationResponse {
  status: "optimal" | "infeasible" | "suboptimal" | string;
  is_feasible?: boolean;
  target_demand: number;
  total_allocated_quantity: number;
  unmet_demand: number;
  total_landed_cost: number | null;
  currency?: string;
  budget_limit?: number | null;
  budget_utilized_pct?: number | null;
  allocations: SupplierAllocation[];
  unassigned_suppliers?: string[];
  explanations?: string[];
  warnings?: string[];
  scenario_impact?: ScenarioImpact | null;
  is_mock?: boolean;
  message?: string;
}

export interface ScenarioImpact {
  scenario_type: string;
  parameters: Record<string, any>;
  baseline_status: string;
  scenario_status: string;
  is_feasible: boolean;
  total_cost_delta?: number | null;
  percentage_cost_change?: number | null;
  quantity_changes?: Record<string, number>;
  narrative_explanation: string;
  baseline_summary?: any;
  scenario_summary?: any;
}

export type NodeType = "document" | "claim" | "supplier" | "cost" | "risk" | "decision" | "recommendation" | "evidence" | "missing_info" | "conflict" | "allocation";

export interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  relation_type?: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata?: Record<string, any>;
  is_mock?: boolean;
  message?: string;
}

export interface WorkflowResponse {
  document: {
    filename: string;
    raw_text: string;
  };
  extraction: {
    suppliers: SupplierQuote[];
    missing_fields_summary: string[];
    conflicts_summary: string[];
    is_mock: boolean;
    message?: string;
  };
  optimization: OptimizationResponse;
  graph: GraphResponse;
  summary: string;
}
