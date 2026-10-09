"""
Service Integration Adapters for Person 2 (Backend API).

Provides drop-in implementations of:
- BaseOptimizationService.optimize(request: OptimizationRequest) -> OptimizationResponse
- BaseGraphService.build_graph(request: GraphRequest) -> GraphResponse

Enables Person 2 to inject ProcuraXOptimizationService and ProcuraXGraphService
directly into FastAPI dependency injection without modifying backend routes.
"""

from typing import Any, Dict, List, Optional, Protocol, Union
from procurax.optimizer import optimize_allocation
from procurax.scenarios import simulate_scenario
from procurax.graph import build_procurement_graph

# Import backend models if backend package exists, else provide fallback Pydantic schemas
try:
    from backend.app.models import (
        OptimizationRequest,
        OptimizationResponse,
        SupplierAllocation,
        OptimizationScenario,
        GraphRequest,
        GraphResponse,
        GraphNode,
        GraphEdge,
        NodeType,
        SupplierQuote,
    )
except ImportError:
    from enum import Enum
    from pydantic import BaseModel, Field

    class NodeType(str, Enum):
        DOCUMENT = "document"
        CLAIM = "claim"
        SUPPLIER = "supplier"
        COST = "cost"
        RISK = "risk"
        DECISION = "decision"

    class SupplierAllocation(BaseModel):
        supplier_id: str
        supplier_name: str
        allocated_quantity: int
        effective_unit_price: float
        unit_transport_cost: float
        landed_cost: float
        capacity_utilization_pct: float

    class OptimizationScenario(BaseModel):
        price_multipliers: Dict[str, float] = Field(default_factory=dict)
        capacity_reductions: Dict[str, float] = Field(default_factory=dict)

    class OptimizationRequest(BaseModel):
        suppliers: List[Any]
        target_demand: int
        budget_limit: Optional[float] = None
        scenario: Optional[OptimizationScenario] = None

    class OptimizationResponse(BaseModel):
        status: str = "optimal"
        target_demand: int
        total_allocated_quantity: int
        total_landed_cost: float
        budget_limit: Optional[float] = None
        budget_exceeded: bool = False
        allocations: List[SupplierAllocation]
        unmet_demand: int = 0
        warnings: List[str] = Field(default_factory=list)
        is_mock: bool = False
        message: str = "Optimization solver run complete."

    class GraphNode(BaseModel):
        id: str
        label: str
        type: NodeType
        properties: Dict[str, Any] = Field(default_factory=dict)

    class GraphEdge(BaseModel):
        id: str
        source: str
        target: str
        label: str
        relation_type: str

    class GraphRequest(BaseModel):
        suppliers: List[Any]
        optimization_result: Optional[OptimizationResponse] = None

    class GraphResponse(BaseModel):
        nodes: List[GraphNode]
        edges: List[GraphEdge]
        is_mock: bool = False
        message: str = "Evidence-to-decision graph constructed."


class BaseOptimizationService(Protocol):
    """Protocol expected by Person 2's backend service layer."""
    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        ...


class BaseGraphService(Protocol):
    """Protocol expected by Person 2's backend service layer."""
    def build_graph(self, request: GraphRequest) -> GraphResponse:
        ...


class ProcuraXOptimizationService(BaseOptimizationService):
    """
    MILP Optimization Service implementing Person 2's BaseOptimizationService contract.
    Replaces Person 2's MockOptimizationService with exact integer programming.
    """

    def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        demand = request.target_demand
        budget = request.budget_limit
        suppliers = request.suppliers
        scenario = request.scenario

        # If a scenario is passed, execute scenario solver
        if scenario and (scenario.price_multipliers or scenario.capacity_reductions):
            sc_result = simulate_scenario(
                suppliers=suppliers,
                demand=demand,
                scenario=scenario,
                budget=budget,
            )
            raw_opt = sc_result["scenario_summary"]
            extra_msg = f"Scenario evaluated: {sc_result.get('narrative_explanation')}"
        else:
            raw_opt = optimize_allocation(
                suppliers=suppliers,
                demand=demand,
                budget=budget,
            )
            extra_msg = raw_opt.get("explanations", ["Optimization complete."])[0]

        # Convert raw allocations to Person 2's SupplierAllocation list
        allocations: List[SupplierAllocation] = []
        for a in raw_opt.get("allocations", []):
            qty = a.get("allocated_quantity", 0)
            unit_p = round(float(a.get("effective_unit_price") or a.get("unit_price") or 0.0), 2)
            t_cost = round(float(a.get("transport_cost") or 0.0), 2)
            unit_t = round(t_cost / max(1, qty), 2)
            landed = round(float(a.get("landed_cost") or (qty * unit_p + t_cost)), 2)
            util_pct = round(float(a.get("capacity_utilization_pct") or 0.0), 2)

            allocations.append(
                SupplierAllocation(
                    supplier_id=a["supplier_id"],
                    supplier_name=a["supplier_name"],
                    allocated_quantity=qty,
                    effective_unit_price=unit_p,
                    unit_transport_cost=unit_t,
                    landed_cost=landed,
                    capacity_utilization_pct=util_pct,
                )
            )

        status = raw_opt.get("status", "optimal")
        total_allocated = raw_opt.get("allocated_demand", 0)
        unmet = raw_opt.get("unmet_demand", 0)
        total_landed = float(raw_opt.get("total_cost") or 0.0)

        budget_exceeded = False
        if budget is not None and total_landed > budget:
            budget_exceeded = True
            if status == "optimal":
                status = "infeasible"

        return OptimizationResponse(
            status=status,
            target_demand=demand,
            total_allocated_quantity=total_allocated,
            total_landed_cost=round(total_landed, 2),
            budget_limit=budget,
            budget_exceeded=budget_exceeded,
            allocations=allocations,
            unmet_demand=unmet,
            warnings=raw_opt.get("warnings", []),
            is_mock=False,
            message=extra_msg,
        )


class ProcuraXGraphService(BaseGraphService):
    """
    NetworkX Evidence-to-Decision Consistency Graph Service implementing Person 2's BaseGraphService.
    Replaces Person 2's MockGraphService with real multi-entity citation and risk tracking.
    """

    def build_graph(self, request: GraphRequest) -> GraphResponse:
        suppliers = request.suppliers
        opt_res = request.optimization_result

        # Build comprehensive graph via Task 4
        graph_dict = build_procurement_graph(
            suppliers=suppliers,
            allocation=opt_res.model_dump() if opt_res and hasattr(opt_res, "model_dump") else opt_res,
        )

        nodes: List[GraphNode] = []
        for n in graph_dict.get("nodes", []):
            nid = n.get("id")
            nlabel = n.get("label", nid)
            raw_type = n.get("type", "supplier")

            # Map raw type to Person 2's NodeType enum
            if raw_type == "document":
                node_type = NodeType.DOCUMENT
            elif raw_type in ("claim", "evidence"):
                node_type = NodeType.CLAIM
            elif raw_type in ("cost_calculation", "cost"):
                node_type = NodeType.COST
            elif raw_type in ("supplier_risk", "risk"):
                node_type = NodeType.RISK
            elif raw_type in ("recommendation", "allocation", "decision"):
                node_type = NodeType.DECISION
            else:
                node_type = NodeType.SUPPLIER

            props = {k: v for k, v in n.items() if k not in ("id", "label", "type")}
            nodes.append(GraphNode(id=nid, label=nlabel, type=node_type, properties=props))

        edges: List[GraphEdge] = []
        for idx, e in enumerate(graph_dict.get("edges", [])):
            eid = f"edge-{e.get('source')}-{e.get('target')}-{idx}"
            src = e.get("source")
            tgt = e.get("target")
            etype = e.get("type", "CONNECTED_TO")
            label = e.get("label", etype)
            edges.append(GraphEdge(id=eid, source=src, target=tgt, label=label, relation_type=etype))

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            is_mock=False,
            message=f"NetworkX Consistency Graph built ({len(nodes)} nodes, {len(edges)} edges).",
        )
