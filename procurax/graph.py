"""
Task 4: Evidence-to-Decision Consistency Graph Engine for ProcuraX.

Uses NetworkX to construct a directed knowledge & lineage graph connecting:
- Supplier documents
- Extracted claims
- Source excerpts and page references
- Missing and conflicting information
- Sustainability claims (unverified by default)
- Cost calculations
- Supplier risks
- Optimization allocations
- Scenario simulations
- Final sourcing recommendations

Enforces core project constraints:
1. Distinguishes extracted claims from independently verified facts (claims default to is_verified=False).
2. Explicitly flags when recommendations depend on incomplete or unverified information.
3. Preserves exact document citations (file, page, excerpt) without fabrication.
4. Returns JSON-compatible node and edge structures for frontend visualization
   matching both standalone consumers and Person 2's Backend API interfaces.
"""

from typing import Any, Dict, List, Optional, Union
import networkx as nx
from procurax.models import Supplier


def build_procurement_graph(
    suppliers: List[Union[Dict[str, Any], Any]],
    allocation: Optional[Union[Dict[str, Any], Any]] = None,
    risks: Optional[List[Dict[str, Any]]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
    scenario_impact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct the Evidence-to-Decision Consistency Graph using NetworkX.

    Args:
        suppliers: List of supplier dicts, Supplier models, or Person 2's SupplierQuote models.
        allocation: Output from optimize_allocation() or Person 2's OptimizationResponse.
        risks: Optional list of identified supplier or supply chain risks.
        conflicts: Optional list of detected conflicting claims/data.
        scenario_impact: Optional scenario simulation results from simulate_scenario().

    Returns:
        JSON-compatible dict containing:
        - "nodes": list of node objects with id, type, label, and properties
        - "edges": list of edge objects with id, source, target, type, relation_type, and label
        - "graph_metrics": summary graph metrics
        - "decision_audit": verification and completeness audit of the recommendation
        - "metadata": metadata object for backend integration
    """
    G = nx.DiGraph()

    # Normalize suppliers to dicts
    supplier_dicts: List[Dict[str, Any]] = []
    for s in suppliers:
        if isinstance(s, dict):
            supplier_dicts.append(dict(s))
        elif hasattr(s, "model_dump"):
            supplier_dicts.append(s.model_dump())
        else:
            supplier_dicts.append(dict(s))

    # Normalize allocation to dict
    if allocation is None:
        alloc_dict = {}
    elif hasattr(allocation, "model_dump"):
        alloc_dict = allocation.model_dump()
    elif isinstance(allocation, dict):
        alloc_dict = dict(allocation)
    else:
        alloc_dict = {}

    documents_seen = set()
    missing_info_nodes = []
    incomplete_suppliers_allocated = []
    unverified_claims_count = 0

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
            delivery_days=s.get("delivery_days"),
        )

        # Missing Fields Nodes
        missing_fields = list(s.get("missing_fields") or [])
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
                relation_type="HAS_MISSING_INFO",
                label="flags missing",
            )
            missing_info_nodes.append((sup_id, m_node_id, mf))

        # Extracted Claims & Evidence
        claims = s.get("claims") or []
        for idx, claim in enumerate(claims):
            if hasattr(claim, "model_dump"):
                c_dict = claim.model_dump()
            elif isinstance(claim, dict):
                c_dict = dict(claim)
            else:
                c_dict = {"field": f"claim_{idx}", "value": str(claim)}

            c_field = c_dict.get("field", f"claim_{idx}")
            c_value = c_dict.get("value")
            c_status = c_dict.get("status", "extracted")
            if hasattr(c_status, "value"):
                c_status = c_status.value
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
            unverified_claims_count += 1

            G.add_edge(
                s_node_id,
                c_node_id,
                source=s_node_id,
                target=c_node_id,
                type="CLAIMS",
                relation_type="CLAIMS",
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
                    relation_type="EXTRACTED_FROM",
                    label="extracted from document",
                )

            # Evidence Node (page & verbatim excerpt)
            if src_excerpt or src_page is not None:
                ev_node_id = f"evidence:{sup_id}:{c_field}:{idx}"
                ev_label = f"Evidence: p.{src_page}" if src_page is not None else "Evidence Excerpt"
                G.add_node(
                    ev_node_id,
                    id=ev_node_id,
                    type="evidence",
                    label=ev_label,
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
                    relation_type="SUPPORTED_BY",
                    label="supported by excerpt",
                )

        # Sustainability Claims: Represent explicitly as UNVERIFIED claims
        sustainability_claims = s.get("sustainability_claims") or []
        for s_idx, s_claim in enumerate(sustainability_claims):
            sc_node_id = f"claim:{sup_id}:sustainability:{s_idx}"
            G.add_node(
                sc_node_id,
                id=sc_node_id,
                type="claim",
                label=f"Sustainability Claim: {s_claim}",
                field="sustainability",
                value=s_claim,
                status="unverified",
                is_verified=False,  # Never treat sustainability claims as confirmed facts!
                supplier_id=sup_id,
                category="sustainability",
            )
            unverified_claims_count += 1
            G.add_edge(
                s_node_id,
                sc_node_id,
                source=s_node_id,
                target=sc_node_id,
                type="CLAIMS",
                relation_type="CLAIMS",
                label="makes sustainability claim (unverified)",
            )

    # 2. Conflicts (Explicit and Auto-detected)
    conflict_list = list(conflicts or [])
    # Also check suppliers conflicting_fields if present
    for s in supplier_dicts:
        sid = s.get("supplier_id")
        for cf in s.get("conflicting_fields", []):
            if not any(c.get("field") == cf for c in conflict_list):
                conflict_list.append({
                    "field": cf,
                    "description": f"Conflicting information reported for field '{cf}' on {sid}",
                    "supplier_ids": [sid],
                })

    for idx, conf in enumerate(conflict_list):
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
                    relation_type="HAS_CONFLICT",
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
            relation_type="EVALUATES_COST",
            label="calculates landed cost",
        )

        for n, attrs in list(G.nodes(data=True)):
            if attrs.get("type") == "claim" and attrs.get("supplier_id") == sup_id:
                if attrs.get("field") in ["unit_price", "transport_cost", "moq"]:
                    G.add_edge(
                        n,
                        cost_node_id,
                        source=n,
                        target=cost_node_id,
                        type="INFLUENCES_COST",
                        relation_type="INFLUENCES_COST",
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
                    relation_type="EXPOSES_RISK",
                    label="risk exposure",
                )

    # 5. Optimization & Allocation Nodes
    allocations = alloc_dict.get("allocations", [])
    recommendation_node_id = "decision:recommendation"

    # Final Decision / Recommendation Node
    G.add_node(
        recommendation_node_id,
        id=recommendation_node_id,
        type="recommendation",
        label="Sourcing Recommendation",
        status=alloc_dict.get("status", "unknown"),
        is_feasible=alloc_dict.get("is_feasible", False),
        demanded_quantity=alloc_dict.get("requested_demand") or alloc_dict.get("target_demand", 0),
        allocated_quantity=alloc_dict.get("allocated_demand") or alloc_dict.get("total_allocated_quantity", 0),
        total_procurement_cost=alloc_dict.get("total_cost") or alloc_dict.get("total_landed_cost"),
        currency=alloc_dict.get("currency", "INR"),
        budget=alloc_dict.get("budget") or alloc_dict.get("budget_limit"),
        budget_utilized_pct=alloc_dict.get("budget_utilized_pct"),
    )

    for alloc in allocations:
        if hasattr(alloc, "model_dump"):
            a_data = alloc.model_dump()
        else:
            a_data = dict(alloc)

        sup_id = a_data.get("supplier_id", "UNKNOWN")
        qty = a_data.get("allocated_quantity", 0)
        cost_bd = a_data.get("cost_breakdown") or {}
        landed = a_data.get("landed_cost") or cost_bd.get("total_landed_cost")
        cost_unit = a_data.get("effective_unit_price") or cost_bd.get("cost_per_unit")

        alloc_node_id = f"allocation:{sup_id}"
        G.add_node(
            alloc_node_id,
            id=alloc_node_id,
            type="allocation",
            label=f"Allocated: {qty} units ({sup_id})",
            supplier_id=sup_id,
            quantity=qty,
            share_of_demand_pct=a_data.get("share_of_demand_pct", 0.0),
            total_landed_cost=landed,
            cost_per_unit=cost_unit,
        )

        cost_node_id = f"cost:{sup_id}"
        if G.has_node(cost_node_id):
            G.add_edge(
                cost_node_id,
                alloc_node_id,
                source=cost_node_id,
                target=alloc_node_id,
                type="DETERMINES_ALLOCATION",
                relation_type="DETERMINES_ALLOCATION",
                label="cost determines volume",
            )

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
                            relation_type="AFFECTS_ALLOCATION",
                            label="risk factor",
                        )

        G.add_edge(
            alloc_node_id,
            recommendation_node_id,
            source=alloc_node_id,
            target=recommendation_node_id,
            type="CONTRIBUTES_TO",
            relation_type="CONTRIBUTES_TO",
            label="contributes to recommendation",
        )

        # Incomplete Dependency Detection
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
                        relation_type="DEPENDS_ON_INCOMPLETE_DATA",
                        label="CAUTION: relies on missing data",
                    )

    # 6. Scenario Simulation Nodes (if scenario impact passed)
    if scenario_impact:
        sc_node_id = "scenario:simulation"
        sc_type = scenario_impact.get("scenario_type", "disruption")
        narrative = scenario_impact.get("narrative_explanation", "")
        cost_delta = scenario_impact.get("total_cost_delta")

        G.add_node(
            sc_node_id,
            id=sc_node_id,
            type="scenario",
            label=f"Scenario Shock: {sc_type}",
            scenario_type=sc_type,
            total_cost_delta=cost_delta,
            narrative=narrative,
        )

        G.add_edge(
            sc_node_id,
            recommendation_node_id,
            source=sc_node_id,
            target=recommendation_node_id,
            type="SIMULATES_SHOCK_ON",
            relation_type="SIMULATES_SHOCK_ON",
            label="shifts recommendation",
        )

        # Link to affected suppliers
        for sid, q_change in scenario_impact.get("quantity_changes", {}).items():
            s_node = f"supplier:{sid}"
            if G.has_node(s_node):
                G.add_edge(
                    sc_node_id,
                    s_node,
                    source=sc_node_id,
                    target=s_node,
                    type="REALLOCATES_VOLUME",
                    relation_type="REALLOCATES_VOLUME",
                    label=f"volume shift: {q_change:+}",
                )

    # Convert NetworkX graph to JSON-compatible structures with properties dict
    nodes_data: List[Dict[str, Any]] = []
    for n, attrs in G.nodes(data=True):
        clean_attrs = {}
        for k, v in attrs.items():
            if isinstance(v, (int, float, str, bool, list, dict)) or v is None:
                clean_attrs[k] = v
            else:
                clean_attrs[k] = str(v)

        # Provide both top-level keys and properties dictionary for Person 2 compatibility
        props = {k: v for k, v in clean_attrs.items() if k not in ("id", "label", "type")}
        clean_attrs["properties"] = props
        nodes_data.append(clean_attrs)

    edges_data: List[Dict[str, Any]] = []
    for idx, (u, v, attrs) in enumerate(G.edges(data=True)):
        edge_id = attrs.get("id") or f"edge-{u}-{v}-{idx}"
        rel_type = attrs.get("relation_type") or attrs.get("type", "CONNECTED_TO")
        lbl = attrs.get("label", rel_type)

        edge_obj = {
            "id": edge_id,
            "source": u,
            "target": v,
            "type": rel_type,
            "relation_type": rel_type,
            "label": lbl,
        }
        for k, val in attrs.items():
            if k not in edge_obj:
                if isinstance(val, (int, float, str, bool, list, dict)) or val is None:
                    edge_obj[k] = val
                else:
                    edge_obj[k] = str(val)
        edges_data.append(edge_obj)

    # Decision audit summary
    depends_on_incomplete = len(incomplete_suppliers_allocated) > 0
    decision_audit = {
        "status": alloc_dict.get("status"),
        "is_feasible": alloc_dict.get("is_feasible"),
        "depends_on_incomplete_data": depends_on_incomplete,
        "affected_suppliers": list(set(incomplete_suppliers_allocated)),
        "unverified_claims_count": unverified_claims_count,
        "documents_referenced": list(documents_seen),
        "total_nodes": len(nodes_data),
        "total_edges": len(edges_data),
    }

    graph_metrics = {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(G),
        "node_types": list(set(n.get("type") for n in nodes_data)),
        "edge_types": list(set(e.get("relation_type") for e in edges_data)),
    }

    metadata = {
        "is_mock": False,
        "graph_metrics": graph_metrics,
        "decision_audit": decision_audit,
        "has_conflicts": len(conflict_list) > 0,
        "depends_on_incomplete_data": depends_on_incomplete,
    }

    return {
        "nodes": nodes_data,
        "edges": edges_data,
        "graph_metrics": graph_metrics,
        "decision_audit": decision_audit,
        "metadata": metadata,
    }


def build_evidence_graph(
    suppliers: List[Union[Dict[str, Any], Any]],
    allocation_result: Optional[Union[Dict[str, Any], Any]] = None,
    scenario_impact: Optional[Dict[str, Any]] = None,
    risks: Optional[List[Dict[str, Any]]] = None,
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Direct interface alias expected by Person 2's backend GraphService.
    Bridges GraphService.build_graph() directly to NetworkX graph builder.
    """
    return build_procurement_graph(
        suppliers=suppliers,
        allocation=allocation_result,
        risks=risks,
        conflicts=conflicts,
        scenario_impact=scenario_impact,
    )
