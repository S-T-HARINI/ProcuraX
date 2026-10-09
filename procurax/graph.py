"""
Task 4: Evidence-to-Decision Consistency Graph Engine for ProcuraX.

Uses NetworkX to construct a directed knowledge & lineage graph connecting:
- Supplier documents
- Extracted claims
- Source excerpts and page references
- Missing and conflicting information
- Cost calculations
- Supplier risks
- Optimization allocations
- Final sourcing recommendations

Enforces core project constraints:
1. Distinguishes extracted claims from independently verified facts (claims default to is_verified=False).
2. Explicitly flags when recommendations depend on incomplete or unverified information.
3. Preserves exact document citations (file, page, excerpt) without fabrication.
4. Returns JSON-compatible node and edge structures for frontend visualization.
"""

from typing import Any, Dict, List, Optional, Union
import networkx as nx
from procurax.models import Supplier


def build_procurement_graph(
    suppliers: List[Union[Dict[str, Any], Supplier]],
    allocation: Dict[str, Any],
    risks: Optional[List[Dict[str, Any]]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Construct the Evidence-to-Decision Consistency Graph using NetworkX.

    Args:
        suppliers: List of supplier dicts or Supplier models following the shared contract.
        allocation: Output from optimize_allocation().
        risks: Optional list of identified supplier or supply chain risks.
               Example: [{"supplier_id": "SUP-001", "risk_type": "Capacity Concentration", "severity": "medium", "description": "Takes 80% of demand"}]
        conflicts: Optional list of detected conflicting claims/data.
               Example: [{"field": "delivery_days", "description": "Contradictory lead times found", "supplier_ids": ["SUP-001"]}]

    Returns:
        JSON-compatible dict containing:
        - "nodes": list of node objects with id, type, label, and attributes
        - "edges": list of edge objects with source, target, type, and attributes
        - "graph_metrics": summary graph metrics
        - "decision_audit": verification and completeness audit of the recommendation
    """
    G = nx.DiGraph()

    # Normalize suppliers
    supplier_dicts: List[Dict[str, Any]] = []
    for s in suppliers:
        if isinstance(s, Supplier):
            supplier_dicts.append(s.model_dump())
        else:
            supplier_dicts.append(dict(s))

    documents_seen = set()
    missing_info_nodes = []
    allocated_supplier_ids = {
        a["supplier_id"] for a in allocation.get("allocations", []) if a.get("allocated_quantity", 0) > 0
    }
    incomplete_suppliers_allocated = []

    # 1. Process Suppliers, Claims, Documents, Evidence, and Missing Info
    for s in supplier_dicts:
        sup_id = s.get("supplier_id", "UNKNOWN")
        sup_name = s.get("supplier_name", sup_id)

        # Supplier Node
        s_node_id = f"supplier:{sup_id}"
        G.add_node(
            s_node_id,
            id=s_node_id,
            type="supplier",
            label=f"Supplier: {sup_name} ({sup_id})",
            supplier_id=sup_id,
            supplier_name=sup_name,
            currency=s.get("currency", "INR"),
            capacity=s.get("capacity"),
            moq=s.get("moq"),
        )

        # Missing Fields Nodes
        missing_fields = list(s.get("missing_fields") or [])
        # Check if unit_price or transport_cost or capacity were null but not in missing_fields
        for field_name in ["unit_price", "transport_cost", "capacity", "moq", "delivery_days"]:
            if s.get(field_name) is None and field_name not in missing_fields:
                missing_fields.append(field_name)

        for mf in missing_fields:
            m_node_id = f"missing:{sup_id}:{mf}"
            G.add_node(
                m_node_id,
                id=m_node_id,
                type="missing_info",
                label=f"Missing: {mf} ({sup_id})",
                field=mf,
                supplier_id=sup_id,
                severity="high" if mf in ["unit_price", "capacity"] else "medium",
            )
            G.add_edge(
                s_node_id,
                m_node_id,
                source=s_node_id,
                target=m_node_id,
                type="HAS_MISSING_INFO",
                label="flags missing",
            )
            missing_info_nodes.append((sup_id, m_node_id, mf))

        # Claims & Evidence
        claims = s.get("claims") or []
        for idx, claim in enumerate(claims):
            c_dict = claim if isinstance(claim, dict) else claim.model_dump()
            c_field = c_dict.get("field", f"claim_{idx}")
            c_value = c_dict.get("value")
            c_status = c_dict.get("status", "extracted")
            src_file = c_dict.get("source_file")
            src_page = c_dict.get("source_page")
            src_excerpt = c_dict.get("source_excerpt")

            c_node_id = f"claim:{sup_id}:{c_field}:{idx}"
            # Core Innovation Rule: Never treat claims as independently verified facts!
            G.add_node(
                c_node_id,
                id=c_node_id,
                type="claim",
                label=f"Claim: {c_field} = {c_value}",
                field=c_field,
                value=str(c_value),
                status=c_status,
                is_verified=False,  # Unverified supplier claim
                supplier_id=sup_id,
            )
            G.add_edge(
                s_node_id,
                c_node_id,
                source=s_node_id,
                target=c_node_id,
                type="CLAIMS",
                label="makes claim",
            )

            # Document Node (if citation exists)
            if src_file:
                doc_node_id = f"doc:{src_file}"
                if doc_node_id not in documents_seen:
                    G.add_node(
                        doc_node_id,
                        id=doc_node_id,
                        type="document",
                        label=f"Doc: {src_file}",
                        filename=src_file,
                    )
                    documents_seen.add(doc_node_id)

                G.add_edge(
                    c_node_id,
                    doc_node_id,
                    source=c_node_id,
                    target=doc_node_id,
                    type="EXTRACTED_FROM",
                    label="extracted from document",
                )

            # Evidence Node (page & verbatim excerpt)
            if src_excerpt or src_page is not None:
                ev_node_id = f"evidence:{sup_id}:{c_field}:{idx}"
                G.add_node(
                    ev_node_id,
                    id=ev_node_id,
                    type="evidence",
                    label=f"Evidence: p.{src_page or '?'}",
                    source_file=src_file,
                    page=src_page,
                    excerpt=src_excerpt,
                )
                G.add_edge(
                    c_node_id,
                    ev_node_id,
                    source=c_node_id,
                    target=ev_node_id,
                    type="SUPPORTED_BY",
                    label="supported by excerpt",
                )

    # 2. Conflicts (if any)
    if conflicts:
        for idx, conf in enumerate(conflicts):
            conf_node_id = f"conflict:{conf.get('field', idx)}:{idx}"
            G.add_node(
                conf_node_id,
                id=conf_node_id,
                type="conflict",
                label=f"Conflict: {conf.get('field', 'Contradiction')}",
                description=conf.get("description", "Conflicting claims detected"),
                field=conf.get("field"),
                supplier_ids=conf.get("supplier_ids", []),
            )
            for sid in conf.get("supplier_ids", []):
                s_node = f"supplier:{sid}"
                if G.has_node(s_node):
                    G.add_edge(
                        s_node,
                        conf_node_id,
                        source=s_node,
                        target=conf_node_id,
                        type="HAS_CONFLICT",
                        label="involved in conflict",
                    )

    # 3. Cost Calculation Nodes
    for s in supplier_dicts:
        sup_id = s.get("supplier_id", "UNKNOWN")
        cost_node_id = f"cost:{sup_id}"
        u_price = s.get("unit_price")
        t_cost = s.get("transport_cost")

        G.add_node(
            cost_node_id,
            id=cost_node_id,
            type="cost_calculation",
            label=f"Landed Cost Rate ({sup_id})",
            supplier_id=sup_id,
            unit_price=u_price,
            transport_cost=t_cost,
            currency=s.get("currency", "INR"),
            has_complete_inputs=(u_price is not None and t_cost is not None),
        )

        G.add_edge(
            f"supplier:{sup_id}",
            cost_node_id,
            source=f"supplier:{sup_id}",
            target=cost_node_id,
            type="EVALUATES_COST",
            label="calculates landed cost",
        )

        # Link relevant pricing claims to cost node
        for n, attrs in list(G.nodes(data=True)):
            if attrs.get("type") == "claim" and attrs.get("supplier_id") == sup_id:
                if attrs.get("field") in ["unit_price", "transport_cost", "moq"]:
                    G.add_edge(
                        n,
                        cost_node_id,
                        source=n,
                        target=cost_node_id,
                        type="INFLUENCES_COST",
                        label="influences cost",
                    )

    # 4. Supplier Risks
    if risks:
        for idx, r in enumerate(risks):
            r_sup_id = r.get("supplier_id", "UNKNOWN")
            r_node_id = f"risk:{r_sup_id}:{idx}"
            G.add_node(
                r_node_id,
                id=r_node_id,
                type="supplier_risk",
                label=f"Risk: {r.get('risk_type', 'Operational')}",
                supplier_id=r_sup_id,
                severity=r.get("severity", "medium"),
                description=r.get("description", ""),
            )
            s_node = f"supplier:{r_sup_id}"
            if G.has_node(s_node):
                G.add_edge(
                    s_node,
                    r_node_id,
                    source=s_node,
                    target=r_node_id,
                    type="EXPOSES_RISK",
                    label="risk exposure",
                )

    # 5. Optimization & Allocation Nodes
    allocations = allocation.get("allocations", [])
    recommendation_node_id = "decision:recommendation"

    # Final Decision / Recommendation Node
    G.add_node(
        recommendation_node_id,
        id=recommendation_node_id,
        type="recommendation",
        label="Sourcing Recommendation",
        status=allocation.get("status", "unknown"),
        is_feasible=allocation.get("is_feasible", False),
        demanded_quantity=allocation.get("requested_demand", 0),
        allocated_quantity=allocation.get("allocated_demand", 0),
        total_procurement_cost=allocation.get("total_cost"),
        currency=allocation.get("currency", "INR"),
        budget=allocation.get("budget"),
        budget_utilized_pct=allocation.get("budget_utilized_pct"),
    )

    for alloc in allocations:
        sup_id = alloc.get("supplier_id", "UNKNOWN")
        qty = alloc.get("allocated_quantity", 0)
        cost_bd = alloc.get("cost_breakdown") or {}

        alloc_node_id = f"allocation:{sup_id}"
        G.add_node(
            alloc_node_id,
            id=alloc_node_id,
            type="allocation",
            label=f"Allocated: {qty} units ({sup_id})",
            supplier_id=sup_id,
            quantity=qty,
            share_of_demand_pct=alloc.get("share_of_demand_pct", 0.0),
            total_landed_cost=cost_bd.get("total_landed_cost"),
            cost_per_unit=cost_bd.get("cost_per_unit"),
        )

        # Link Cost calculation -> Allocation
        cost_node_id = f"cost:{sup_id}"
        if G.has_node(cost_node_id):
            G.add_edge(
                cost_node_id,
                alloc_node_id,
                source=cost_node_id,
                target=alloc_node_id,
                type="DETERMINES_ALLOCATION",
                label="cost determines volume",
            )

        # Link Risk -> Allocation (if risk exists for this supplier)
        if risks:
            for idx, r in enumerate(risks):
                if r.get("supplier_id") == sup_id:
                    r_node_id = f"risk:{sup_id}:{idx}"
                    if G.has_node(r_node_id):
                        G.add_edge(
                            r_node_id,
                            alloc_node_id,
                            source=r_node_id,
                            target=alloc_node_id,
                            type="AFFECTS_ALLOCATION",
                            label="risk factor",
                        )

        # Link Allocation -> Final Recommendation
        G.add_edge(
            alloc_node_id,
            recommendation_node_id,
            source=alloc_node_id,
            target=recommendation_node_id,
            type="CONTRIBUTES_TO",
            label="contributes to recommendation",
        )

        # 6. Check if this allocated supplier had missing information
        # Core Requirement: Identify when recommendations depend on incomplete information!
        sup_missing = [mf for (sid, m_id, mf) in missing_info_nodes if sid == sup_id]
        if sup_missing:
            incomplete_suppliers_allocated.append(sup_id)
            for (sid, m_id, mf) in missing_info_nodes:
                if sid == sup_id:
                    G.add_edge(
                        recommendation_node_id,
                        m_id,
                        source=recommendation_node_id,
                        target=m_id,
                        type="DEPENDS_ON_INCOMPLETE_DATA",
                        label="CAUTION: relies on missing data",
                    )

    # Convert NetworkX graph to JSON-compatible data structures
    nodes_data: List[Dict[str, Any]] = []
    for n, attrs in G.nodes(data=True):
        # Guarantee serializability
        clean_attrs = {}
        for k, v in attrs.items():
            if isinstance(v, (int, float, str, bool, list, dict)) or v is None:
                clean_attrs[k] = v
            else:
                clean_attrs[k] = str(v)
        nodes_data.append(clean_attrs)

    edges_data: List[Dict[str, Any]] = []
    for u, v, attrs in G.edges(data=True):
        clean_attrs = {"source": u, "target": v}
        for k, val in attrs.items():
            if isinstance(val, (int, float, str, bool, list, dict)) or val is None:
                clean_attrs[k] = val
            else:
                clean_attrs[k] = str(val)
        edges_data.append(clean_attrs)

    # Decision audit analysis
    depends_on_incomplete = len(incomplete_suppliers_allocated) > 0
    decision_audit = {
        "status": allocation.get("status"),
        "is_feasible": allocation.get("is_feasible"),
        "depends_on_incomplete_data": depends_on_incomplete,
        "affected_suppliers": list(set(incomplete_suppliers_allocated)),
        "unverified_claims_count": sum(1 for n in nodes_data if n.get("type") == "claim" and not n.get("is_verified")),
        "documents_referenced": list(documents_seen),
        "total_nodes": len(nodes_data),
        "total_edges": len(edges_data),
    }

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "graph_metrics": {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "is_dag": nx.is_directed_acyclic_graph(G),
            "node_types": list(set(n.get("type") for n in nodes_data)),
            "edge_types": list(set(e.get("type") for e in edges_data)),
        },
        "decision_audit": decision_audit,
    }
