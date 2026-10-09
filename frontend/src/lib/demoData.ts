import { GraphResponse, SupplierQuote } from "@/types/procurement";

/**
 * Clearly labeled synthetic demo supplier quotations for offline demonstration
 * and initial dashboard rendering.
 */
export const DEMO_SUPPLIERS: SupplierQuote[] = [
  {
    supplier_id: "SUP-001",
    supplier_name: "Apex Sustainable Packaging Ltd.",
    product_name: "Reusable Industrial Bottle (500ml)",
    unit_price: 80.0,
    currency: "INR",
    moq: 100,
    capacity: 600,
    delivery_days: 5,
    transport_cost: 500.0,
    discount_terms: "5% off on orders exceeding 500 units.",
    sustainability_claims: [
      "Certified 100% Ocean Bound Recycled HDPE",
      "Closed-loop manufacturing process",
    ],
    missing_fields: [],
    ambiguous_fields: [],
    conflicting_fields: [],
    claims: [
      {
        field: "unit_price",
        value: 80.0,
        source_file: "synthetic_supplier_alpha.pdf",
        source_page: 1,
        source_excerpt: "Base Unit Price: 80.00 INR per bottle",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "moq",
        value: 100,
        source_file: "synthetic_supplier_alpha.pdf",
        source_page: 1,
        source_excerpt: "Minimum Order Quantity (MOQ): 100 units",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "capacity",
        value: 600,
        source_file: "synthetic_supplier_alpha.pdf",
        source_page: 1,
        source_excerpt: "Production Monthly Capacity: 600 units",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "delivery_days",
        value: 5,
        source_file: "synthetic_supplier_alpha.pdf",
        source_page: 1,
        source_excerpt: "Standard Delivery Lead Time: 5 business days",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "transport_cost",
        value: 500.0,
        source_file: "synthetic_supplier_alpha.pdf",
        source_page: 1,
        source_excerpt: "Fixed Transportation & Freight: 500.00 INR flat charge per shipment",
        status: "extracted",
        is_verified_fact: false,
      },
    ],
    metadata: {
      is_synthetic: true,
      demo_scenario: "Standard baseline reliable supplier",
    },
  },
  {
    supplier_id: "SUP-002",
    supplier_name: "BlueWave Logistics & Supplies",
    product_name: "Reusable Industrial Bottle (500ml)",
    unit_price: 72.5,
    currency: "INR",
    moq: 300,
    capacity: 1000,
    delivery_days: null,
    transport_cost: null,
    discount_terms: null,
    sustainability_claims: ["Recyclable resin blend (Code 2)"],
    missing_fields: ["delivery_days", "transport_cost"],
    ambiguous_fields: ["delivery_days"],
    conflicting_fields: [],
    claims: [
      {
        field: "unit_price",
        value: 72.5,
        source_file: "synthetic_supplier_beta.pdf",
        source_page: 1,
        source_excerpt: "Unit Price: 72.50 INR per bottle",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "moq",
        value: 300,
        source_file: "synthetic_supplier_beta.pdf",
        source_page: 1,
        source_excerpt: "Minimum Order Quantity (MOQ): 300 units",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "delivery_days",
        value: "5 to 14 business days",
        source_file: "synthetic_supplier_beta.pdf",
        source_page: 1,
        source_excerpt: "Delivery Lead Time: 5 to 14 business days (variable depending on transport backlog)",
        status: "ambiguous",
        notes: "Wide delivery window dependent on external backlog",
        is_verified_fact: false,
      },
      {
        field: "transport_cost",
        value: null,
        source_file: "synthetic_supplier_beta.pdf",
        source_page: 1,
        source_excerpt: "Freight / Shipping: To be determined upon delivery destination (Not Included)",
        status: "extracted",
        notes: "Freight not quoted by supplier; destination pending",
        is_verified_fact: false,
      },
    ],
    metadata: {
      is_synthetic: true,
      demo_scenario: "Incomplete quotation with ambiguous delivery and missing freight",
    },
  },
  {
    supplier_id: "SUP-003",
    supplier_name: "GreenSource Manufacturing Co.",
    product_name: "Reusable Industrial Bottle (500ml)",
    unit_price: 85.0,
    currency: "INR",
    moq: 50,
    capacity: 400,
    delivery_days: 3,
    transport_cost: 350.0,
    discount_terms: null,
    sustainability_claims: [],
    missing_fields: [],
    ambiguous_fields: [],
    conflicting_fields: ["unit_price"],
    claims: [
      {
        field: "unit_price",
        value: 85.0,
        source_file: "synthetic_supplier_gamma.pdf",
        source_page: 1,
        source_excerpt: "Standard Unit Price: 85.00 INR per bottle",
        status: "conflicting",
        notes: "Standard pricing baseline",
        is_verified_fact: false,
      },
      {
        field: "unit_price",
        value: 95.0,
        source_file: "synthetic_supplier_gamma.pdf",
        source_page: 1,
        source_excerpt: "Urgent Dispatch Unit Price: 95.00 INR per bottle (contradictory rush pricing stated)",
        status: "conflicting",
        notes: "Alternative rush pricing conflicts with standard rate",
        is_verified_fact: false,
      },
      {
        field: "moq",
        value: 50,
        source_file: "synthetic_supplier_gamma.pdf",
        source_page: 1,
        source_excerpt: "Minimum Order Quantity (MOQ): 50 units",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "capacity",
        value: 400,
        source_file: "synthetic_supplier_gamma.pdf",
        source_page: 1,
        source_excerpt: "Maximum Production Capacity: 400 units",
        status: "extracted",
        is_verified_fact: false,
      },
      {
        field: "delivery_days",
        value: 3,
        source_file: "synthetic_supplier_gamma.pdf",
        source_page: 1,
        source_excerpt: "Delivery Lead Time: 3 business days",
        status: "extracted",
        is_verified_fact: false,
      },
    ],
    metadata: {
      is_synthetic: true,
      demo_scenario: "Conflicting unit prices between standard and rush quotes",
    },
  },
];

/**
 * Returns pre-built evidence-to-decision lineage graph for demo and fallback states.
 */
export function getDemoGraph(): GraphResponse {
  return {
    nodes: [
      // Document Nodes
      {
        id: "doc:alpha",
        label: "synthetic_supplier_alpha.pdf",
        type: "document",
        properties: { filename: "synthetic_supplier_alpha.pdf", format: "PDF", pages: 1 },
      },
      {
        id: "doc:beta",
        label: "synthetic_supplier_beta.pdf",
        type: "document",
        properties: { filename: "synthetic_supplier_beta.pdf", format: "PDF", pages: 1 },
      },
      {
        id: "doc:gamma",
        label: "synthetic_supplier_gamma.pdf",
        type: "document",
        properties: { filename: "synthetic_supplier_gamma.pdf", format: "PDF", pages: 1 },
      },

      // Supplier Nodes
      {
        id: "sup:SUP-001",
        label: "Apex Sustainable Packaging Ltd.",
        type: "supplier",
        properties: { supplier_id: "SUP-001", capacity: 600, moq: 100, currency: "INR" },
      },
      {
        id: "sup:SUP-002",
        label: "BlueWave Logistics & Supplies",
        type: "supplier",
        properties: { supplier_id: "SUP-002", capacity: 1000, moq: 300, currency: "INR" },
      },
      {
        id: "sup:SUP-003",
        label: "GreenSource Manufacturing Co.",
        type: "supplier",
        properties: { supplier_id: "SUP-003", capacity: 400, moq: 50, currency: "INR" },
      },

      // Claim Nodes
      {
        id: "claim:alpha:price",
        label: "Claim: Unit Price ₹80.00",
        type: "claim",
        properties: {
          field: "unit_price",
          value: 80.0,
          excerpt: "Base Unit Price: 80.00 INR per bottle",
          source_page: 1,
          status: "extracted",
        },
      },
      {
        id: "claim:beta:price",
        label: "Claim: Unit Price ₹72.50",
        type: "claim",
        properties: {
          field: "unit_price",
          value: 72.5,
          excerpt: "Unit Price: 72.50 INR per bottle",
          source_page: 1,
          status: "extracted",
        },
      },
      {
        id: "claim:gamma:conflict_price",
        label: "Claim: Conflicting Prices (₹85 / ₹95)",
        type: "conflict",
        properties: {
          field: "unit_price",
          value: "85.0 vs 95.0",
          excerpt: "Urgent Dispatch Unit Price: 95.00 INR per bottle (contradictory rush pricing stated)",
          status: "conflicting",
        },
      },

      // Risk Nodes
      {
        id: "risk:beta:freight",
        label: "Risk: Missing Freight Charge",
        type: "risk",
        properties: {
          field: "transport_cost",
          issue: "Freight TBD - landed cost cannot be reliably estimated",
          severity: "high",
        },
      },
      {
        id: "risk:gamma:conflict",
        label: "Risk: Price Contradiction",
        type: "risk",
        properties: {
          field: "unit_price",
          issue: "Discrepancy between standard (85 INR) and urgent quote (95 INR)",
          severity: "medium",
        },
      },

      // Cost Nodes
      {
        id: "cost:alpha:landed",
        label: "Landed Cost: ₹40,500 (500 units)",
        type: "cost",
        properties: {
          quantity: 500,
          base_cost: 40000,
          transport_cost: 500,
          effective_unit_rate: 81.0,
        },
      },

      // Recommendation / Decision Node
      {
        id: "rec:optimal_allocation",
        label: "Decision: 100% Allocation to Apex (500 units)",
        type: "recommendation",
        properties: {
          target_demand: 500,
          primary_supplier: "Apex Sustainable Packaging Ltd.",
          allocated_quantity: 500,
          total_cost: 40500,
          rationale: "Lowest confirmed landed cost with verified capacity and no missing cost inputs.",
        },
      },
    ],
    edges: [
      { id: "e1", source: "doc:alpha", target: "claim:alpha:price", label: "contains", relation_type: "evidence" },
      { id: "e2", source: "claim:alpha:price", target: "sup:SUP-001", label: "quotes", relation_type: "supplier_claim" },
      { id: "e3", source: "doc:beta", target: "claim:beta:price", label: "contains", relation_type: "evidence" },
      { id: "e4", source: "claim:beta:price", target: "sup:SUP-002", label: "quotes", relation_type: "supplier_claim" },
      { id: "e5", source: "doc:beta", target: "risk:beta:freight", label: "omits", relation_type: "missing_info" },
      { id: "e6", source: "doc:gamma", target: "claim:gamma:conflict_price", label: "contains", relation_type: "evidence" },
      { id: "e7", source: "claim:gamma:conflict_price", target: "risk:gamma:conflict", label: "triggers", relation_type: "conflict" },
      { id: "e8", source: "sup:SUP-001", target: "cost:alpha:landed", label: "calculates", relation_type: "cost_calculation" },
      { id: "e9", source: "cost:alpha:landed", target: "rec:optimal_allocation", label: "justifies", relation_type: "recommendation" },
    ],
    metadata: {
      generated_at: "2026-03-15T00:00:00.000Z",
      is_synthetic: true,
      graph_version: "1.0",
    },
    is_mock: true,
    message: "Demo evidence-to-decision lineage graph loaded.",
  };
}
