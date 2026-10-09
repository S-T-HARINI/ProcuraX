from typing import Optional, Protocol
from backend.app.models import (
    GraphEdge,
    GraphNode,
    GraphRequest,
    GraphResponse,
    NodeType,
    SupplierQuote,
)


class BaseGraphService(Protocol):
    """
    Interface Contract for Person 3 (Evidence-to-Decision Graph Module).
    
    Person 3 should implement this protocol or inherit from BaseGraphService
    to construct dynamic knowledge graphs and export NetworkX / JSON graph structures.
    """
    def build_graph(self, request: GraphRequest) -> GraphResponse:
        ...


class GraphService:
    """
    Service wrapper delegating to Person 3's graph module or baseline mock.
    """

    def __init__(self, graph_builder: Optional[BaseGraphService] = None):
        self._graph_builder = graph_builder or MockGraphService()

    def build_graph(self, request: GraphRequest) -> GraphResponse:
        return self._graph_builder.build_graph(request)


class MockGraphService:
    """
    Constructs an Evidence-to-Decision Consistency Graph linking source documents,
    extracted supplier claims, supplier entities, cost/risk metrics, and sourcing decisions.
    """

    def build_graph(self, request: GraphRequest) -> GraphResponse:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        suppliers = request.suppliers
        optimization_result = request.optimization_result

        # Decision node
        decision_id = "node-decision-001"
        nodes.append(
            GraphNode(
                id=decision_id,
                label="Procurement Allocation Decision",
                type=NodeType.DECISION,
                properties={
                    "total_suppliers": len(suppliers),
                    "optimization_status": optimization_result.status if optimization_result else "pending",
                    "total_landed_cost": optimization_result.total_landed_cost if optimization_result else None,
                },
            )
        )

        for supp_idx, supp in enumerate(suppliers):
            supp_node_id = f"node-supplier-{supp.supplier_id}"
            nodes.append(
                GraphNode(
                    id=supp_node_id,
                    label=f"Supplier: {supp.supplier_name}",
                    type=NodeType.SUPPLIER,
                    properties={
                        "supplier_id": supp.supplier_id,
                        "product_name": supp.product_name,
                        "unit_price": supp.unit_price,
                        "currency": supp.currency,
                        "moq": supp.moq,
                        "capacity": supp.capacity,
                    },
                )
            )

            # Edge from supplier to decision node
            edges.append(
                GraphEdge(
                    id=f"edge-supp-dec-{supp.supplier_id}",
                    source=supp_node_id,
                    target=decision_id,
                    label="EVALUATED_FOR",
                    relation_type="EVALUATED_FOR",
                )
            )

            # Cost node for supplier
            cost_node_id = f"node-cost-{supp.supplier_id}"
            nodes.append(
                GraphNode(
                    id=cost_node_id,
                    label=f"Landed Cost ({supp.supplier_id})",
                    type=NodeType.COST,
                    properties={
                        "unit_price": supp.unit_price,
                        "transport_cost": supp.transport_cost,
                        "currency": supp.currency,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    id=f"edge-supp-cost-{supp.supplier_id}",
                    source=supp_node_id,
                    target=cost_node_id,
                    label="HAS_COST_STRUCTURE",
                    relation_type="HAS_COST_STRUCTURE",
                )
            )

            # Process claims & source documents
            for claim_idx, claim in enumerate(supp.claims):
                doc_node_id = f"node-doc-{claim.source_file.replace('.', '_')}"
                if not any(n.id == doc_node_id for n in nodes):
                    nodes.append(
                        GraphNode(
                            id=doc_node_id,
                            label=f"Document: {claim.source_file}",
                            type=NodeType.DOCUMENT,
                            properties={"filename": claim.source_file},
                        )
                    )

                claim_node_id = f"node-claim-{supp.supplier_id}-{claim_idx}"
                nodes.append(
                    GraphNode(
                        id=claim_node_id,
                        label=f"Claim: {claim.field} = {claim.value}",
                        type=NodeType.CLAIM,
                        properties={
                            "field": claim.field,
                            "value": claim.value,
                            "source_file": claim.source_file,
                            "source_page": claim.source_page,
                            "source_excerpt": claim.source_excerpt,
                            "status": claim.status.value,
                        },
                    )
                )

                # Edge document -> claim (EVIDENCE_FOR)
                edges.append(
                    GraphEdge(
                        id=f"edge-doc-claim-{supp.supplier_id}-{claim_idx}",
                        source=doc_node_id,
                        target=claim_node_id,
                        label="EVIDENCE_FOR",
                        relation_type="EVIDENCE_FOR",
                    )
                )

                # Edge claim -> supplier (ATTACHED_TO)
                edges.append(
                    GraphEdge(
                        id=f"edge-claim-supp-{supp.supplier_id}-{claim_idx}",
                        source=claim_node_id,
                        target=supp_node_id,
                        label="ATTACHED_TO",
                        relation_type="ATTACHED_TO",
                    )
                )

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            is_mock=True,
            message="Evidence-to-Decision Consistency Graph created successfully.",
        )
