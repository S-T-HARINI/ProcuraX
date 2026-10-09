import logging
from typing import Any, Dict, List, Optional, Protocol
from backend.app.models import (
    GraphEdge,
    GraphNode,
    GraphRequest,
    GraphResponse,
)
from procurax.graph import build_evidence_graph

logger = logging.getLogger("procurax.backend.graph")


class BaseGraphService(Protocol):
    """
    Interface Contract for Person 3 (Evidence Graph Module).
    """
    def build_graph(self, request: GraphRequest) -> GraphResponse:
        ...


class GraphService:
    """
    Service layer bridging API requests to Person 3's Evidence-to-Decision Graph engine.
    """

    def build_graph(self, request: GraphRequest) -> GraphResponse:
        suppliers_data = [s.model_dump() for s in request.suppliers]
        opt_res_dict = request.optimization_result.model_dump() if request.optimization_result else None
        scenario_impact_dict = request.scenario_impact

        raw_graph_data = build_evidence_graph(
            suppliers=suppliers_data,
            allocation_result=opt_res_dict,
            scenario_impact=scenario_impact_dict,
        )

        nodes: List[GraphNode] = []
        for n in raw_graph_data.get("nodes", []):
            nodes.append(
                GraphNode(
                    id=n["id"],
                    label=n.get("label", n["id"]),
                    type=n.get("type", "supplier"),
                    properties=n.get("properties", {}),
                )
            )

        edges: List[GraphEdge] = []
        for e in raw_graph_data.get("edges", []):
            edges.append(
                GraphEdge(
                    id=e.get("id", f"{e['source']}-{e['target']}"),
                    source=e["source"],
                    target=e["target"],
                    label=e.get("label", e.get("relation_type", "CONNECTED_TO")),
                    relation_type=e.get("relation_type", "CONNECTED_TO"),
                )
            )

        metadata = raw_graph_data.get("metadata", {})
        is_mock_flag = metadata.get("is_mock", False)

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            metadata=metadata,
            is_mock=is_mock_flag,
            message="Evidence-to-Decision Consistency Graph constructed.",
        )
