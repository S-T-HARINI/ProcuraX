"""
Unit tests for Task 4: build_procurement_graph and build_evidence_graph, and FastAPI /api/graph endpoint.
"""

import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from procurax.optimizer import optimize_allocation
from procurax.scenarios import simulate_scenario
from procurax.graph import build_procurement_graph, build_evidence_graph

client = TestClient(app)

SAMPLE_SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "supplier_name": "Apex Eco Solutions",
        "product_name": "Reusable Bottle",
        "unit_price": 80.0,
        "currency": "INR",
        "moq": 100,
        "capacity": 600,
        "delivery_days": 5,
        "transport_cost": 500.0,
        "sustainability_claims": [],
        "missing_fields": [],
        "claims": [
            {
                "field": "unit_price",
                "value": 80.0,
                "source_file": "supplier_a.pdf",
                "source_page": 1,
                "source_excerpt": "Unit price quoted at INR 80.",
                "status": "extracted",
            }
        ],
    }
]


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
            "sustainability_claims": ["100% Recycled PET", "Zero Landfill Certified"],
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


def test_generate_graph_success():
    payload = {"suppliers": SAMPLE_SUPPLIERS}
    response = client.post("/api/graph", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0

    node_types = {n["type"] for n in data["nodes"]}
    assert "supplier" in node_types
    assert "claim" in node_types
    assert "document" in node_types
    assert "recommendation" in node_types or "decision" in node_types


def test_generate_graph_empty_suppliers():
    response = client.post("/api/graph", json={"suppliers": []})
    assert response.status_code == 400


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


def test_sustainability_claims_unverified(graph_test_suppliers):
    allocation = optimize_allocation(graph_test_suppliers, demand=100)
    graph = build_procurement_graph(graph_test_suppliers, allocation)

    # Check that sustainability claims are represented as unverified claims
    sust_nodes = [n for n in graph["nodes"] if n.get("category") == "sustainability"]
    assert len(sust_nodes) == 2
    for sn in sust_nodes:
        assert sn["is_verified"] is False
        assert sn["status"] == "unverified"
        assert "Sustainability Claim" in sn["label"]


def test_conflicts_representation(graph_test_suppliers):
    allocation = optimize_allocation(graph_test_suppliers, demand=100)
    conflicts = [
        {
            "field": "lead_time",
            "description": "SUP-001 claims 5 days whereas SUP-002 has missing lead times.",
            "supplier_ids": ["SUP-001", "SUP-002"],
        }
    ]
    graph = build_procurement_graph(graph_test_suppliers, allocation, conflicts=conflicts)

    conflict_nodes = [n for n in graph["nodes"] if n["type"] == "conflict"]
    assert len(conflict_nodes) == 1
    assert conflict_nodes[0]["field"] == "lead_time"

    conflict_edges = [e for e in graph["edges"] if e.get("type") == "HAS_CONFLICT"]
    assert len(conflict_edges) == 2


def test_evidence_linkage(graph_test_suppliers):
    allocation = optimize_allocation(graph_test_suppliers, demand=100)
    graph = build_procurement_graph(graph_test_suppliers, allocation)

    # Check evidence nodes and page formatting
    evidence_nodes = [n for n in graph["nodes"] if n["type"] == "evidence"]
    assert len(evidence_nodes) >= 2
    for en in evidence_nodes:
        if en.get("page") is not None:
            assert f"Evidence: p.{en['page']}" == en["label"]
        else:
            assert en["label"] == "Evidence Excerpt"

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


def test_build_evidence_graph_with_scenario(graph_test_suppliers):
    alloc = optimize_allocation(graph_test_suppliers, demand=200)
    scenario = {"type": "price_increase", "supplier_id": "SUP-002", "percentage": 20.0}
    scen_impact = simulate_scenario(graph_test_suppliers, demand=200, scenario=scenario)

    graph = build_evidence_graph(
        suppliers=graph_test_suppliers,
        allocation_result=alloc,
        scenario_impact=scen_impact,
    )

    # Check scenario node and edge
    sc_nodes = [n for n in graph["nodes"] if n["type"] == "scenario"]
    assert len(sc_nodes) == 1
    assert "Scenario Shock" in sc_nodes[0]["label"]

    shock_edges = [e for e in graph["edges"] if e.get("relation_type") == "SIMULATES_SHOCK_ON"]
    assert len(shock_edges) == 1
