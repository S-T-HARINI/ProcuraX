"""
Unit tests for Task 4: build_procurement_graph
"""

import json
import pytest
from procurax.optimizer import optimize_allocation
from procurax.graph import build_procurement_graph


@pytest.fixture
def graph_test_suppliers():
    return [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "EcoBottles Ltd",
            "product_name": "Reusable Bottle",
            "unit_price": 80.0,
            "currency": "INR",
            "moq": 100,
            "capacity": 600,
            "delivery_days": 5,
            "transport_cost": 500.0,
            "sustainability_claims": ["100% Recycled PET"],
            "missing_fields": [],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 80.0,
                    "source_file": "quotation_eco.pdf",
                    "source_page": 1,
                    "source_excerpt": "Unit Price: INR 80.00 for orders above 100 units.",
                    "status": "extracted",
                },
                {
                    "field": "moq",
                    "value": 100,
                    "source_file": "quotation_eco.pdf",
                    "source_page": 2,
                    "source_excerpt": "Minimum Order Quantity is 100 units.",
                    "status": "extracted",
                },
            ],
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "GreenPacks Inc",
            "product_name": "Reusable Bottle",
            "unit_price": 75.0,
            "currency": "INR",
            "moq": 50,
            "capacity": 300,
            "delivery_days": None,  # Missing field!
            "transport_cost": 400.0,
            "sustainability_claims": [],
            "missing_fields": ["delivery_days"],
            "claims": [
                {
                    "field": "unit_price",
                    "value": 75.0,
                    "source_file": "greenpacks_quote.xlsx",
                    "source_page": 1,
                    "source_excerpt": "Unit rate: INR 75.00/unit",
                    "status": "extracted",
                }
            ],
        },
    ]


def test_build_procurement_graph_structure(graph_test_suppliers):
    # Optimize allocation for demand 200
    allocation = optimize_allocation(graph_test_suppliers, demand=200)
    risks = [
        {
            "supplier_id": "SUP-001",
            "risk_type": "LeadTimeRisk",
            "severity": "low",
            "description": "Standard delivery is 5 days",
        }
    ]

    graph = build_procurement_graph(graph_test_suppliers, allocation, risks=risks)

    assert "nodes" in graph
    assert "edges" in graph
    assert "graph_metrics" in graph
    assert "decision_audit" in graph

    # Verify JSON serializability
    json_str = json.dumps(graph)
    assert len(json_str) > 0

    node_types = graph["graph_metrics"]["node_types"]
    assert "supplier" in node_types
    assert "claim" in node_types
    assert "document" in node_types
    assert "evidence" in node_types
    assert "cost_calculation" in node_types
    assert "allocation" in node_types
    assert "recommendation" in node_types


def test_claims_unverified_by_default(graph_test_suppliers):
    allocation = optimize_allocation(graph_test_suppliers, demand=100)
    graph = build_procurement_graph(graph_test_suppliers, allocation)

    claim_nodes = [n for n in graph["nodes"] if n["type"] == "claim"]
    assert len(claim_nodes) >= 2
    for cn in claim_nodes:
        # Crucial Innovation Rule: Claims must not be marked verified facts!
        assert cn["is_verified"] is False
        assert cn["status"] == "extracted"


def test_evidence_linkage(graph_test_suppliers):
    allocation = optimize_allocation(graph_test_suppliers, demand=100)
    graph = build_procurement_graph(graph_test_suppliers, allocation)

    # Check evidence nodes
    evidence_nodes = [n for n in graph["nodes"] if n["type"] == "evidence"]
    assert len(evidence_nodes) >= 2

    # Check SUPPORTED_BY edges
    supported_edges = [e for e in graph["edges"] if e.get("type") == "SUPPORTED_BY"]
    assert len(supported_edges) >= 2

    # Check EXTRACTED_FROM edges to document
    doc_edges = [e for e in graph["edges"] if e.get("type") == "EXTRACTED_FROM"]
    assert len(doc_edges) >= 2


def test_depends_on_incomplete_flag(graph_test_suppliers):
    # SUP-002 has missing 'delivery_days'
    # Force allocation to SUP-002 (since it's cheaper: 75 vs 80)
    allocation = optimize_allocation(graph_test_suppliers, demand=100)
    graph = build_procurement_graph(graph_test_suppliers, allocation)

    # Check if recommendation flagged incomplete dependency
    incomplete_edges = [e for e in graph["edges"] if e.get("type") == "DEPENDS_ON_INCOMPLETE_DATA"]
    assert len(incomplete_edges) > 0
    assert graph["decision_audit"]["depends_on_incomplete_data"] is True
    assert "SUP-002" in graph["decision_audit"]["affected_suppliers"]
