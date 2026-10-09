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
    """Health check endpoint to verify backend operational state."""
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
    Parses content and preserves source page numbers / sheet details.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
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
    Extract structured supplier information and claims from parsed document text.
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
    Uses Person 3's graph builder or baseline fallback.
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
