from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from backend.app.models import (
    DocumentParseResponse,
    ExtractRequest,
    ExtractResponse,
    GraphRequest,
    GraphResponse,
    OptimizationRequest,
    OptimizationResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from backend.app.services.document_service import DocumentService
from backend.app.services.extraction_service import ExtractionService
from backend.app.services.graph_service import GraphService
from backend.app.services.optimization_service import OptimizationService

app = FastAPI(
    title="ProcuraX — Procurement Intelligence API",
    description="Evidence-Driven Procurement Intelligence and Sourcing Optimization API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

extraction_service = ExtractionService()
optimization_service = OptimizationService()
graph_service = GraphService()


@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint verifying backend operational status."""
    return {
        "status": "ok",
        "service": "ProcuraX Backend API",
        "version": "0.1.0",
    }


@app.post(
    "/api/documents/upload",
    response_model=DocumentParseResponse,
    tags=["Documents"],
    status_code=status.HTTP_200_OK,
)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload supplier quotation document (PDF, CSV, XLSX).
    Parses document content preserving source filename and page/sheet references.
    """
    if not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    try:
        parsed_doc = DocumentService.parse_document(content, file.filename)
        return parsed_doc
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse document '{file.filename}': {str(err)}",
        )


@app.post(
    "/api/extract",
    response_model=ExtractResponse,
    tags=["Extraction"],
    status_code=status.HTTP_200_OK,
)
def extract_claims(request: ExtractRequest):
    """
    Extract structured supplier claims from quotation text.
    Uses Person 1's Gemma 4 extraction module or mock fallback.
    """
    try:
        return extraction_service.extract(request)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction processing error: {str(err)}",
        )


@app.post(
    "/api/optimize",
    response_model=OptimizationResponse,
    tags=["Optimization"],
    status_code=status.HTTP_200_OK,
)
def optimize_sourcing(request: OptimizationRequest):
    """
    Optimize supplier purchase allocation under demand, capacity, MOQ, budget,
    and scenario constraints (price multipliers and capacity reductions).
    Uses Person 3's optimization solver or baseline fallback.
    """
    if not request.suppliers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier list cannot be empty for optimization.",
        )
    if request.target_demand <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target demand must be greater than zero.",
        )

    try:
        return optimization_service.optimize(request)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization solver error: {str(err)}",
        )


@app.post(
    "/api/graph",
    response_model=GraphResponse,
    tags=["Graph"],
    status_code=status.HTTP_200_OK,
)
def generate_graph(request: GraphRequest):
    """
    Build Evidence-to-Decision Consistency Graph linking source documents,
    claims, supplier entities, cost metrics, and sourcing decisions.
    Uses Person 3's graph builder.
    """
    if not request.suppliers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier list cannot be empty for graph generation.",
        )

    try:
        return graph_service.build_graph(request)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph generation error: {str(err)}",
        )


@app.post(
    "/api/workflow",
    response_model=WorkflowResponse,
    tags=["End-to-End Workflow"],
    status_code=status.HTTP_200_OK,
)
def run_end_to_end_workflow(request: WorkflowRequest):
    """
    Complete Evidence-to-Decision Sourcing Workflow:
    Upload/Text Input -> Gemma Claim Extraction -> Supplier Data Validation ->
    Landed Cost & MILP Optimization -> Scenario Simulation -> Evidence Graph Generation.
    """
    doc_filename = request.document_filename or "supplier_quotation.pdf"
    raw_text = request.document_text or ""

    if not raw_text.strip():
        raw_text = (
            f"Quotation Reference: DEMO-{doc_filename}\n"
            f"Supplier: Apex Sustainable Packaging Ltd.\n"
            f"Base Unit Price: 80.00 INR per bottle\n"
            f"Minimum Order Quantity (MOQ): 100 units\n"
            f"Production Monthly Capacity: 600 units\n"
            f"Standard Delivery Lead Time: 5 business days\n"
            f"Transportation & Freight: 500.00 INR flat charge per shipment\n"
        )

    # 1. Extraction Phase (Person 1 Gemma Module)
    extract_req = ExtractRequest(
        filename=doc_filename,
        raw_text=raw_text,
        use_mock=request.use_mock_extraction,
    )
    extract_res = extraction_service.extract(extract_req)

    if not extract_res.suppliers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extraction yielded no valid supplier quotations.",
        )

    # 2. Optimization Phase (Person 3 MILP Solver)
    opt_req = OptimizationRequest(
        suppliers=extract_res.suppliers,
        target_demand=request.target_demand,
        budget_limit=request.budget_limit,
        scenario=request.scenario,
    )
    opt_res = optimization_service.optimize(opt_req)

    # 3. Graph Construction Phase (Person 3 Graph Engine)
    graph_req = GraphRequest(
        suppliers=extract_res.suppliers,
        optimization_result=opt_res,
        scenario_impact=opt_res.scenario_impact,
    )
    graph_res = graph_service.build_graph(graph_req)

    # 4. Synthesize Evidence-to-Decision Executive Summary
    summary_parts = [
        f"ProcuraX Sourcing Report for '{doc_filename}':",
        f"• Extracted claims for {len(extract_res.suppliers)} supplier(s) ({'Mock/Fallback Data' if extract_res.is_mock else 'Verified Gemma 4 Extraction'}).",
        f"• Target Demand: {request.target_demand} units. Status: {opt_res.status.upper()}.",
        f"• Allocated Quantity: {opt_res.total_allocated_quantity}/{request.target_demand} units.",
    ]
    if opt_res.total_landed_cost is not None:
        summary_parts.append(f"• Total Landed Cost: {opt_res.total_landed_cost:,.2f} {opt_res.currency}.")
    if opt_res.explanations:
        summary_parts.append(f"• Allocation Logic: {' '.join(opt_res.explanations)}")
    summary_parts.append(
        f"• Evidence Graph: {len(graph_res.nodes)} nodes and {len(graph_res.edges)} edges created linking source claims to allocation decisions."
    )

    return WorkflowResponse(
        document={
            "filename": doc_filename,
            "raw_text": raw_text[:500] + ("..." if len(raw_text) > 500 else ""),
        },
        extraction=extract_res,
        optimization=opt_res,
        graph=graph_res,
        summary="\n".join(summary_parts),
    )
