from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime
import os
import re
from collections import Counter
from pydantic import BaseModel
import csv
import httpx
import pandas as pd
import warnings
from langchain_ollama import ChatOllama
import asyncio
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
import traceback
import logging
from pythonjsonlogger import jsonlogger
from prometheus_fastapi_instrumentator import Instrumentator

# Configure structured JSON Logging for Datadog/Splunk
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Embeddings initialisation for vector search in chatbot
embeddings = OllamaEmbeddings(model="nomic-embed-text")
VECTOR_STORES = {}
# Memory for conversational implementation
MEMORY_STORES = {}
VECTOR_STORE_DIR = "./vector_stores"

class ChatRequest(BaseModel):
    message: str
    model: str = "llama"
    disease_name: str = None 
    session_id: str = "default_session"

# Import existing modules
from excel_parser import CADExcelParser
from database import get_db, create_tables, DatabaseOperations
from models import (
    DiseaseResponse,
    DiseaseListResponse,
    ExcelUploadResponse,
    PathwayVisualizationResponse,
    PathwayStage,
    PathwayPainPoint,
    SolutionsByType,
    PainPointCreate
)
from verification import verify_pain_point
from fastapi.responses import StreamingResponse, FileResponse
from csv_utils import (
    get_csv_cache_status,
    create_csv_cache,
    check_file_size,
    get_csv_file_info
)
from multi_route_agent import create_agent

# Import authentication modules
from auth.database import create_auth_tables
from auth.routes import auth_router
from auth.dependencies import require_admin, get_current_user_info
from auth.models import AdminResponse, UserMe

# Create disease data tables on startup
create_tables()

MODEL_MAPPING = {
    "llama": "llama3"
}

SIMILARITY_STOPWORDS = {
    "a", "about", "above", "able", "across", "after", "again", "against", "all", "also",
    "always", "am", "an", "and", "any", "are", "as", "at", "be", "because", "been",
    "before", "being", "between", "both", "but", "by", "can", "care", "caregiver",
    "caregivers", "careplan", "careplans", "chronic", "clinical", "clinicalcare",
    "clinicalsupport", "condition", "conditions", "could", "disease", "diseases",
    "diagnosis", "diagnostic", "diagnoses", "eg", "each", "family", "factors", "follow",
    "article", "articles", "area", "areas", "body", "cause", "causes", "change", "changes",
    "common", "com", "www", "http", "https", "html", "pdf", "org", "net",
    "field", "fields", "has", "had", "having", "include", "includes", "including",
    "followup", "followupcare", "for", "from", "health", "healthcare", "how", "if",
    "in", "into", "intervention", "interventions", "is", "it", "its", "management",
    "medical", "monitoring", "more", "most", "not", "of", "off", "on", "one", "or",
    "other", "outcome", "outcomes", "patient", "patients", "patientcare", "patientscare",
    "pathway", "pathways", "program", "programs", "provider", "providers", "quality",
    "qualityoflife", "rehabilitation", "related", "risk", "screening", "services",
    "service", "should", "specialist", "specialists", "stage", "stages", "support",
    "supportive", "symptom", "symptoms", "team", "teams", "than", "that", "the", "their",
    "them", "there", "these", "they", "this", "those", "through", "treatment", "treatments",
    "therapy", "therapies", "using", "very", "was", "we", "were", "what", "when",
    "which", "who", "why", "with", "within", "would", "you", "your"
}

# Domain-generic pathway vocabulary that should not influence disease similarity.
GENERIC_PATHWAY_TERMS = {
    "abnormal", "abnormalities", "abnormality", "access", "accurate", "accuracy", "activity",
    "adoption", "adoptions", "alerts", "algorithm", "algorithms", "air", "among",
    "assessment", "care", "challenge", "challenges", "compliance", "continuity", "cost",
    "delay", "delays", "detection", "effectiveness", "efficacy", "efficiency", "engagement",
    "evidence", "evaluation", "follow", "followup", "guideline", "guidelines", "impact",
    "improve", "improved", "improvement", "limitations", "manual", "measurement", "metrics",
    "optimization", "optimize", "outpatient", "pathway", "pathways", "process", "processes",
    "progress", "progression", "record", "records", "referral", "report", "reporting",
    "risk", "risks", "screening", "stage", "stages", "standard", "standards", "symptom",
    "symptoms", "test", "testing", "timely", "workflow", "workflows",
    "prenatal", "prevention", "diagnosis", "treatment", "rehabilitation", "followup"
}

# Create authentication tables on startup
create_auth_tables()


def _similarity_tokens(raw: str, excluded_terms: Optional[set] = None) -> list:
    cleaned = re.sub(r"[^a-z\s]", " ", (raw or "").lower())
    excluded = excluded_terms or set()
    return [
        t for t in cleaned.split()
        if len(t) > 2
        and t not in SIMILARITY_STOPWORDS
        and t not in GENERIC_PATHWAY_TERMS
        and t not in excluded
    ]


def calculate_text_overlap_similarity(text_a: str, text_b: str, excluded_terms: Optional[set] = None) -> float:
    """Return a conservative similarity score based on meaningful keyword overlap.

    This intentionally avoids broad clinical vocabulary overlap (e.g. patient, treatment,
    diagnosis), which creates false positives across unrelated diseases like lung cancer
    and Alzheimer’s disease.
    """
    if not text_a or not text_b:
        return 0.0

    tokens_a = Counter(_similarity_tokens(text_a, excluded_terms=excluded_terms))
    tokens_b = Counter(_similarity_tokens(text_b, excluded_terms=excluded_terms))
    if not tokens_a or not tokens_b:
        return 0.0

    shared = sum(min(tokens_a[k], tokens_b[k]) for k in set(tokens_a) & set(tokens_b))
    total = sum(tokens_a.values()) + sum(tokens_b.values())
    if total == 0:
        return 0.0

    score = (2 * shared) / total
    return round(max(0.0, min(1.0, score)), 4)


def build_disease_similarity_text(disease) -> str:
    """Build a similarity profile focused on disease-specific pain-point language.

    We intentionally avoid stage labels, stakeholders, and solution text because
    they contain broad workflow vocabulary that inflates cross-disease similarity.
    """
    sections = [disease.name or ""]
    for stage in getattr(disease, "stages", []) or []:
        for pain_point in getattr(stage, "pain_points", []) or []:
            sections.append(pain_point.description or "")
    return " ".join(sections)


def is_greeting_message(message: str) -> bool:
    normalized = (message or "").strip().lower()
    greeting_tokens = {
        "hi", "hello", "hey", "yo", "hiya", "good morning", "good afternoon", "good evening"
    }
    if normalized in greeting_tokens:
        return True

    # Handle informal repeated greetings like "hii", "hellooo", "heyyy".
    if re.fullmatch(r"h+i+|h+e+y+|h+e+l+o+", normalized):
        return True

    return False


def sanitize_chat_response(text: str) -> str:
    """Remove repetitive self-intro boilerplate and return a cleaner answer."""
    cleaned = (text or "").strip()

    # Remove known low-value introductions that hurt UX quality.
    patterns = [
        r"^hello!?\s*i\s*'?m\s+a\s+strict,?\s+factual\s+medical\s+ai\s+assistant[^\.]*\.\s*",
        r"^i\s*am\s+a\s+strict,?\s+factual\s+medical\s+ai\s+assistant[^\.]*\.\s*",
        r"^hi!?\s*i\s*'?m\s+axon[^\.]*\.\s*",
        r"^hello!?\s*i\s*'?m\s+axon[^\.]*\.\s*",
        r"^as\s+an\s+ai\s+assistant[^\.]*\.\s*",
    ]

    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def format_disease_display_name(name: str) -> str:
    """Format disease names for UI text without breaking apostrophes/casing."""
    raw = (name or "").strip().replace("_", " ").replace("-", " ")
    if not raw:
        return "Disease"

    words = []
    for token in raw.split():
        lower_token = token.lower()
        if "'" in lower_token:
            parts = lower_token.split("'")
            head = parts[0].capitalize() if parts and parts[0] else ""
            tail = "'".join(parts[1:])
            words.append(f"{head}'{tail}" if tail else head)
        else:
            words.append(lower_token.capitalize())
    return " ".join(words)


def detect_disease_from_message(message: str, disease_names: List[str]) -> Optional[str]:
    """Detect disease mention from free text using simple normalized matching."""
    msg = (message or "").lower()
    for name in disease_names:
        n = (name or "").lower().strip()
        if n and n in msg:
            return n
    return None

app = FastAPI(
    title="Disease Pathway API with Authentication",
    description="API for managing disease pathways from Excel data with OAuth2 JWT authentication",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include authentication router
app.include_router(auth_router)

# Enable Prometheus Metrics endpoint
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    # Ensure vector store directory and try to load persisted stores
    Path(VECTOR_STORE_DIR).mkdir(exist_ok=True)
    try:
        for entry in os.listdir(VECTOR_STORE_DIR):
            entry_path = os.path.join(VECTOR_STORE_DIR, entry)
            if os.path.isdir(entry_path):
                try:
                    vs = FAISS.load_local(entry_path, embeddings)
                    VECTOR_STORES[entry] = vs
                    print(f"Loaded vector store for {entry}")
                except Exception:
                    print(f"Failed to load vector store for {entry}, skipping")
    except Exception:
        pass
    print("Disease Pathway API v3.0 with Authentication started successfully")

# Instantiate Multi-Route Analyzer Agent
AGENT = create_agent()

# PROTECTED ENDPOINTS - Admin Only

@app.post("/upload-excel", response_model=ExcelUploadResponse)
async def upload_excel(
    disease_name: str,
    disease_group: str = None,
    file: UploadFile = File(...),
    admin: AdminResponse = Depends(require_admin),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process Excel file - ADMIN ONLY
    Requires JWT token with admin privileges
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")

        # Validate disease name
        if not disease_name or not disease_name.strip():
            raise HTTPException(status_code=400, detail="Disease name is required")

        # Save uploaded file
        file_path = f"uploads/{disease_name.lower()}_{file.filename}"
        Path("uploads").mkdir(exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Parse using updated Excel parser
        parser = CADExcelParser(file_path)
        parsed_data = parser.parse_disease_pathway()
        summary_stats = parser.get_summary_stats(parsed_data)

        # Store in database using incremental update
        db_ops = DatabaseOperations(db)
        disease = db_ops.create_or_update_disease(disease_name.lower(), parsed_data, disease_group)

        # Schedule background indexing of newly uploaded/updated disease into FAISS vector store via Celery
        try:
            from tasks import index_disease_vector_store_task
            index_disease_vector_store_task.delay(disease.name or disease_name.lower(), parsed_data, True)
        except Exception as e:
            # Don't fail upload if background scheduling fails; log and continue
            print(f"Warning: failed to schedule vector indexing for {disease_name}: {e}")

        # Sync data to Neo4j Graph Database
        try:
            from graph_builder import KnowledgeGraphManager
            kg_manager = KnowledgeGraphManager()
            kg_manager.sync_disease_to_graph(disease_name.lower(), db_ops)
            kg_manager.close()
            print(f"Successfully synced {disease_name} to Neo4j")
        except Exception as e:
            print(f"Warning: failed to sync {disease_name} to Neo4j: {e}")

        # Clean up uploaded file
        Path(file_path).unlink(missing_ok=True)

        return ExcelUploadResponse(
            message=f"Excel file for {disease_name} processed successfully by admin {admin.email}",
            disease_name=disease_name.lower(),
            stages_created=list(parsed_data['sections'].keys()),
            total_stages=summary_stats['total_stages'],
            total_pain_points=summary_stats['total_pain_points'],
            total_solutions=summary_stats['total_solutions'],
            summary_stats=summary_stats
        )

    except HTTPException:
        raise
    except Exception as e:
        if 'file_path' in locals():
            Path(file_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {str(e)}")

@app.delete("/diseases/{disease_name}")
async def delete_disease(
    disease_name: str,
    admin: AdminResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a disease and all its data - ADMIN ONLY
    Requires JWT token with admin privileges
    """
    try:
        db_ops = DatabaseOperations(db)
        success = db_ops.delete_disease(disease_name.lower())
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Disease '{disease_name}' not found")

        return {
            "message": f"Disease '{disease_name}' deleted successfully by admin {admin.email}",
            "deleted_by": admin.email,
            "deleted_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting disease: {str(e)}")

# PUBLIC ENDPOINTS - No Authentication Required

@app.get("/diseases", response_model=List[DiseaseListResponse])
async def get_all_diseases(db: Session = Depends(get_db)):
    """Get list of all diseases - Public endpoint"""
    try:
        db_ops = DatabaseOperations(db)
        diseases = db_ops.get_all_diseases()
        result = []
        
        for disease in diseases:
            total_pain_points = sum(stage.pain_points_count for stage in disease.stages)
            result.append(DiseaseListResponse(
                id=disease.id,
                name=disease.name,
                created_at=disease.created_at,
                updated_at=disease.updated_at,
                stage_count=len(disease.stages),
                total_pain_points=total_pain_points
            ))
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching diseases: {str(e)}")

@app.get("/diseases/{disease_name}", response_model=DiseaseResponse)
async def get_disease_details(disease_name: str, db: Session = Depends(get_db)):
    """Get detailed disease information - Public endpoint"""
    try:
        db_ops = DatabaseOperations(db)
        disease = db_ops.get_disease_by_name(disease_name.lower())
        
        if not disease:
            raise HTTPException(status_code=404, detail=f"Disease '{disease_name}' not found")

        return disease

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching disease details: {str(e)}")

@app.get("/diseases/{disease_name}/pathway", response_model=PathwayVisualizationResponse)
async def get_disease_pathway(
    disease_name: str, 
    full: bool = False,  # New query parameter
    db: Session = Depends(get_db)
):
    """Get disease pathway data formatted for visualization - Public endpoint"""
    try:
        db_ops = DatabaseOperations(db)
        
        # Use different function based on full parameter
        if full:
            pathway_data = db_ops.get_complete_disease_pathway_data(disease_name.lower())
        else:
            pathway_data = db_ops.get_disease_pathway_data(disease_name.lower())
        
        if not pathway_data:
            raise HTTPException(status_code=404, detail=f"Disease '{disease_name}' not found")

        stages = {}
        total_pain_points = 0
        total_solutions = 0

        for stage_name, stage_data in pathway_data['stages'].items():
            pain_points = []
            for pain_point_data in stage_data['pain_points']:
                solutions_count = sum(len(solutions) for solutions in pain_point_data['solutions'].values())
                total_solutions += solutions_count

                solutions = SolutionsByType(
                    digitalization=pain_point_data['solutions'].get('digitalization', []),
                    automation=pain_point_data['solutions'].get('automation', []),
                    sensing=pain_point_data['solutions'].get('sensing', []),
                    clinical_innovation=pain_point_data['solutions'].get('clinical_innovation', []),
                    process_innovation=pain_point_data['solutions'].get('process_innovation', [])
                )

                pain_points.append(PathwayPainPoint(
                    description=pain_point_data['description'],
                    sources=pain_point_data.get('sources'),
                    coverage=pain_point_data.get('coverage'),
                    existing_solutions=pain_point_data.get('existing_solutions'),
                    solutions=solutions
                ))

            stages[stage_name] = PathwayStage(
                id=stage_data['id'],
                name=stage_data['name'],
                stakeholders=stage_data.get('stakeholders'),
                overview=stage_data.get('overview'),
                pain_points=pain_points
            )
            total_pain_points += len(pain_points)

        return PathwayVisualizationResponse(
            disease_name=disease_name,
            stages=stages,
            total_stages=len(stages),
            total_pain_points=total_pain_points,
            total_solutions=total_solutions
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pathway data: {str(e)}")

@app.get("/diseases/{disease_name}/download-csv")
async def download_pathway_csv(
    disease_name: str,
    db: Session = Depends(get_db)
):
    """Download complete pathway data as CSV - Public endpoint"""
    try:
        db_ops = DatabaseOperations(db)
        disease = db_ops.get_disease_by_name(disease_name.lower())
        
        if not disease:
            raise HTTPException(
                status_code=404,
                detail=f"Disease '{disease_name}' not found"
            )

        cache_valid, cached_file_path = get_csv_cache_status(
            disease_name.lower(),
            disease.updated_at
        )

        current_file_path = cached_file_path

        if not cache_valid:
            print(f"Generating new CSV for {disease_name}...")
            pathway_data = db_ops.get_disease_pathway_data_for_csv(disease_name.lower())
            if not pathway_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No pathway data found for disease '{disease_name}'"
                )

            success, message, file_path = create_csv_cache(disease_name.lower(), pathway_data)
            if not success:
                raise HTTPException(
                    status_code=413,
                    detail=message
                )
            
            current_file_path = file_path
            print(f"CSV generated: {message}")
        else:
            print(f"Using cached CSV for {disease_name}")

        file_exists, file_size = check_file_size(current_file_path)
        if not file_exists:
            raise HTTPException(
                status_code=500,
                detail="CSV file generation failed"
            )

        if file_size > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum allowed: 50MB"
            )

        file_info = get_csv_file_info(current_file_path)
        filename = f"{disease_name}_pathway.csv"
        
        def iter_redis(redis_key: str):
            from csv_utils import redis_client
            import json
            data = redis_client.get(redis_key)
            if data:
                yield json.loads(data)["content"].encode('utf-8')

        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Length": str(file_size),
            "X-CSV-Generated-At": file_info['modified_at'].isoformat(),
            "X-CSV-Size-MB": f"{file_info['size_mb']:.2f}"
        }

        return StreamingResponse(
            iter_redis(current_file_path),
            media_type="text/csv",
            headers=headers
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating CSV for {disease_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating CSV: {str(e)}"
        )

@app.get("/diseases/{disease_name}/csv-info")
async def get_csv_info(disease_name: str, db: Session = Depends(get_db)):
    """Get CSV cache information for debugging - Public endpoint"""
    try:
        db_ops = DatabaseOperations(db)
        disease = db_ops.get_disease_by_name(disease_name.lower())
        
        if not disease:
            raise HTTPException(status_code=404, detail=f"Disease '{disease_name}' not found")

        cache_valid, cached_file_path = get_csv_cache_status(disease_name.lower(), disease.updated_at)
        
        result = {
            "disease_name": disease_name,
            "cache_valid": cache_valid,
            "cached_file_path": cached_file_path,
            "disease_updated_at": disease.updated_at.isoformat()
        }
        
        if cached_file_path and os.path.exists(cached_file_path):
            file_info = get_csv_file_info(cached_file_path)
            result.update(file_info)
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting CSV info: {str(e)}")


# New endpoint: route a free-text query to vector/sql/csv based on heuristics
@app.post("/route-query")
async def route_query(request: ChatRequest, db: Session = Depends(get_db)):
    """Route a user query to vector search, SQL aggregation, or CSV/full-pathway pull."""
    try:
        async def vector_search_fn(query: str, disease_name: Optional[str] = None):
            # Simple adapter for FAISS stores in VECTOR_STORES
            key = (disease_name or "").lower() if disease_name else "global"
            store = VECTOR_STORES.get(key) or VECTOR_STORES.get("global")
            if not store:
                return []
            try:
                results = store.similarity_search(query, k=3)
                out = []
                for r in results:
                    if hasattr(r, 'page_content'):
                        out.append({'text': r.page_content, 'metadata': getattr(r, 'metadata', None)})
                    else:
                        out.append(r)
                return out
            except Exception as e:
                return {"error": str(e)}

        res = await AGENT.route(
            request.message,
            db_session=db,
            disease_name=request.disease_name,
            vector_search_fn=vector_search_fn
        )

        return res

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def index_disease_pathway_to_vector_store(disease_name: str, parsed_data: dict, persist: bool = True):
    """Chunks and embeds the parsed excel data into a vector store."""
    documents = []
    sections = {}
    
    if 'sections' in parsed_data:
        sections = parsed_data.get('sections', {})
    elif 'stages' in parsed_data:
        for stage_name, stage_data in parsed_data.get('stages', {}).items():
            sections[stage_name] = {
                'overview': stage_data.get('overview', ''),
                'stakeholders': stage_data.get('stakeholders', ''),
                'pain_points': stage_data.get('pain_points', [])
            }

    for stage_name, stage_data in sections.items():
        stage_meta = {
            "disease": disease_name,
            "stage": stage_name,
            "stakeholders": ", ".join(stage_data.get('stakeholders', []))
        }
        
        if stage_data.get('overview'):
            documents.append(Document(
                page_content=f"Stage: {stage_name}. Overview: {stage_data['overview']}",
                metadata=stage_meta
            ))
            
        for pp in stage_data.get('pain_points', []):
            content = (
                f"Stage: {stage_name} | Pain Point: {pp.get('description')} \n"
                f"Sources: {pp.get('sources')} | Coverage: {pp.get('coverage')} \n"
                f"Existing Solutions: {pp.get('existing_solutions')} \n"
            )
            for s_type, s_list in pp.get('solutions', {}).items():
                if s_list:
                    content += f"{s_type.replace('_', ' ').title()} Solutions: {', '.join(s_list)}\n"
                    
            documents.append(Document(page_content=content, metadata=stage_meta))

    if not documents:
        print(f"⚠️ No documents were created for {disease_name}. Check if your DB/Excel has data!")
        return

    # === THE FIX IS HERE: Split the text into chunks FIRST ===
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    split_docs = text_splitter.split_documents(documents)
    
    # === Create the FAISS index AFTER chunks are made ===
    db_vector = FAISS.from_documents(split_docs, embeddings)
    
    # Standardize name for storage (lowercase, no spaces)
    folder_name = disease_name.lower().strip().replace(" ", "_")
    VECTOR_STORES[folder_name] = db_vector
    
    # Persist vector store to disk
    if persist:
        try:
            dest = os.path.join(VECTOR_STORE_DIR, folder_name)
            Path(dest).mkdir(parents=True, exist_ok=True)
            db_vector.save_local(dest)
            print(f"SUCCESS: Saved vector store for {disease_name} to {dest}")
        except Exception as e:
            print(f"Failed to save vector store for {disease_name}: {e}")
    
def get_csv_context(file_path: str):
    """Helper to load and format the specific CSV for AI context"""
    try:
        if not os.path.exists(file_path):
            return ""

        # Load the CSV
        df = pd.read_csv(file_path)

        # Convert the first 50 rows to a text summary to avoid token limits
        # Adjust columns based on your specific CSV structure
        context_summary = "Relevant Pathway Data:\n"
        for _, row in df.head(50).iterrows():
            context_summary += f"- Stage: {row.get('Stage', 'N/A')}, Pain Point: {row.get('Pain Point', 'N/A')}, Solution: {row.get('Solution', 'N/A')}\n"

        return context_summary
    except Exception as e:
        print(f"Error reading CSV context: {e}")
        return ""


def get_db_context(disease_name: str, db) -> str:
    try:
        if not disease_name:
            return ""

        db_ops = DatabaseOperations(db)
        pathway_data = db_ops.get_disease_pathway_data_for_csv(disease_name.lower())
        if not pathway_data:
            print(f"DEBUG: No database data found for '{disease_name}'")
            return ""

        context_summary = f"Pathway Data for {disease_name}:\n"
        rows = 0
        MAX_ROWS = 40  # REDUCED from 200 to prevent LLM hallucinating past context limits

        for stage_name, stage in pathway_data.get('stages', {}).items():
            context_summary += f"Stage: {stage.get('name', stage_name)}; Overview: {stage.get('overview','')}\n"
            for pp in stage.get('pain_points', []):
                if rows >= MAX_ROWS:
                    break
                rows += 1
                context_summary += f"- PainPoint: {pp.get('description','')}\n"

        if rows >= MAX_ROWS:
            context_summary += f"...truncated to fit LLM memory limit...\n"

        return context_summary
    except Exception as e:
        print(f"Error generating DB context for {disease_name}: {e}")
        return ""
    
@app.post("/index-disease/{disease_name}")
async def index_disease(disease_name: str, db: Session = Depends(get_db)):
    """Build (or rebuild) FAISS vector store for a disease from DB data."""
    try:
        db_ops = DatabaseOperations(db)
        pathway = db_ops.get_disease_pathway_data_for_csv(disease_name.lower())
        if not pathway:
            raise HTTPException(status_code=404, detail=f"Disease '{disease_name}' not found or has no data")

        # Build vector store (persisted)
        index_disease_pathway_to_vector_store(disease_name.lower(), pathway, persist=True)

        return {"message": f"Indexed {disease_name} into FAISS vector store", "disease": disease_name}
    except HTTPException:
        raise
    except Exception as e:
        # Print the exact error and line number to the terminal
        print(f"\n--- ERROR INDEXING {disease_name} ---")
        traceback.print_exc()
        print("-----------------------------------\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector-stores")
async def list_vector_stores():
    """List available in-memory and persisted vector stores."""
    try:
        stores = []
        for name, store in VECTOR_STORES.items():
            persisted = os.path.isdir(os.path.join(VECTOR_STORE_DIR, name))
            stores.append({"name": name, "in_memory": True, "persisted": persisted})

        # Also include persisted-only stores
        for entry in os.listdir(VECTOR_STORE_DIR):
            if entry not in VECTOR_STORES:
                stores.append({"name": entry, "in_memory": False, "persisted": True})

        return {"vector_stores": stores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diseases/{disease_name}/upload-document")
async def upload_document(
    disease_name: str,
    file: UploadFile = File(...),
    admin: AdminResponse = Depends(require_admin)
):
    """
    Upload a text document (.txt) to augment the FAISS vector store for a specific disease - ADMIN ONLY
    Requires JWT token with admin privileges.
    """
    try:
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are allowed for local ingestion")

        content = await file.read()
        text_content = content.decode('utf-8')

        folder_name = disease_name.lower().strip().replace(" ", "_")
        
        # Split text into chunks
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(text_content)
        
        # Add metadata
        metadatas = [{"source": file.filename, "disease": disease_name.lower()} for _ in chunks]

        # Get existing vector store or create new one
        if folder_name in VECTOR_STORES:
            vs = VECTOR_STORES[folder_name]
            vs.add_texts(texts=chunks, metadatas=metadatas)
        else:
            vs = FAISS.from_texts(texts=chunks, embedding=embeddings, metadatas=metadatas)
            VECTOR_STORES[folder_name] = vs
            
        # Persist
        dest = os.path.join(VECTOR_STORE_DIR, folder_name)
        Path(dest).mkdir(parents=True, exist_ok=True)
        vs.save_local(dest)

        return {"message": f"Document '{file.filename}' successfully ingested into FAISS for '{disease_name}'", "chunks_added": len(chunks)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
# Import LangChain tools and LangGraph
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mcp_server import search_pathway_vectors, get_full_disease_context, generate_pathway_csv, list_available_diseases, get_disease_statistics

# Define LangChain wrappers for our MCP-like tools
@tool
async def vector_search_tool(query: str, disease_name: str) -> str:
    """Search the vector store for specific information about a disease."""
    return await search_pathway_vectors(query, disease_name)

@tool
async def full_context_tool(disease_name: str) -> str:
    """Get the full, comprehensive disease pathway context. Use for summaries."""
    return await get_full_disease_context(disease_name)

@tool
async def csv_export_tool(disease_name: str) -> str:
    """Generate or retrieve a full CSV export of the disease data."""
    return await generate_pathway_csv(disease_name)

@tool
async def list_diseases_tool() -> str:
    """List all available diseases in the database."""
    return await list_available_diseases()

@tool
async def get_stats_tool(disease_name: str) -> str:
    """Get statistics about a disease like number of stages and pain points."""
    return await get_disease_statistics(disease_name)

@tool
def graph_search_tool(query: str) -> str:
    """Search the Neo4j Knowledge Graph for structural questions about diseases, stages, pain points, and solutions."""
    from rag_tools import GraphRAG
    graph_rag = GraphRAG()
    return graph_rag.query(query)

agent_tools = [vector_search_tool, full_context_tool, csv_export_tool, list_diseases_tool, get_stats_tool, graph_search_tool]

@app.post("/chat")
async def chat_with_model(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        ollama_model = MODEL_MAPPING.get(request.model)
        if ollama_model is None:
            raise HTTPException(status_code=400, detail="Only the Llama3 model is available for chat")
        disease_name = (request.disease_name or "").strip().lower()

        user_message = (request.message or "").strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="`message` is required")

        db_ops = DatabaseOperations(db)
        all_disease_names = [d.name for d in db_ops.get_all_diseases() if d.name]
        if not disease_name:
            detected = detect_disease_from_message(user_message, all_disease_names)
            if detected:
                disease_name = detected

        # 1. Retrieve or Initialize Conversational History
        session_id = request.session_id
        if session_id not in MEMORY_STORES:
            MEMORY_STORES[session_id] = []

        # Fast-path for greetings: avoid tool overhead and avoid robotic self-intros.
        if is_greeting_message(user_message):
            disease_names = [format_disease_display_name(n) for n in all_disease_names]
            if disease_name:
                focus_name = format_disease_display_name(disease_name)
                greeting_response = (
                    f"Hi, I can help with {focus_name} pathway questions across stages, pain points, and solutions.\n\n"
                    "You can ask things like:\n"
                    "- Top pain points in diagnosis\n"
                    "- Key stakeholders in treatment\n"
                    "- Summarize this pathway"
                )
            else:
                greeting_response = (
                    "Hi, I can help across disease pathways (diagnosis, treatment, stakeholders, and pain points).\n\n"
                    f"Available diseases: {', '.join(disease_names[:6])}\n\n"
                    "Ask a disease-specific question like:\n"
                    "- Top diagnosis pain points in CAD\n"
                    "- Summarize lung cancer staging pathway\n"
                    "- Key treatment stakeholders in Alzheimer's"
                )

            MEMORY_STORES[session_id].append({"role": "user", "content": user_message})
            MEMORY_STORES[session_id].append({"role": "assistant", "content": greeting_response})

            return {
                "response": greeting_response,
                "disease_name": disease_name or "general",
                "model": ollama_model,
                "agent_used": False,
                "session_id": session_id
            }

        if not disease_name:
            disease_names = [format_disease_display_name(n) for n in all_disease_names]
            clarification = (
                "Please mention a disease so I can provide precise pathway answers.\n\n"
                f"Available diseases: {', '.join(disease_names[:6])}.\n"
                "Example: 'Top pain points in diagnosis for CAD'."
            )
            MEMORY_STORES[session_id].append({"role": "user", "content": user_message})
            MEMORY_STORES[session_id].append({"role": "assistant", "content": clarification})
            return {
                "response": clarification,
                "disease_name": "general",
                "model": ollama_model,
                "agent_used": False,
                "session_id": session_id
            }
        
        # 2. Initialize LLM (Ensure it supports tool calling if using Llama3)
        llm = ChatOllama(
            model=ollama_model,
            temperature=0,
            num_ctx=4096
        )

        # 3. Seed retrieval context for higher quality and fewer unnecessary tool hops.
        context_seed = ""
        try:
            from rag_tools import AdvancedRAG

            key = disease_name.lower().strip().replace(" ", "_")
            store = VECTOR_STORES.get(key) or VECTOR_STORES.get("global")
            if store:
                adv_rag = AdvancedRAG(embeddings_model=embeddings)
                seed_results = adv_rag.perform_hybrid_search(user_message, store, k=3)
                if seed_results:
                    seed_lines = []
                    for item in seed_results:
                        md = item.get("metadata", {}) or {}
                        stage_name = md.get("stage", "")
                        text_snippet = (item.get("text", "") or "").replace("\n", " ")[:280]
                        seed_lines.append(f"- Stage: {stage_name} | Evidence: {text_snippet}")
                    context_seed = "\n".join(seed_lines)
        except Exception:
            context_seed = ""

        # 4. Create Agent prompt
        system_msg = (
            f"You are Axon, a medical pathway assistant specialized in '{disease_name}' disease pathways.\n"
            "FRAMEWORK DEFINITION:\n"
            "- Disease Pathway: The patient journey from diagnosis to treatment.\n"
            "- Stage: A distinct phase in the patient journey (e.g., Diagnosis, Treatment).\n"
            "- Pain Point: A specific clinical or operational challenge within a stage.\n"
            "- Solution: A proposed intervention (digital, automation, clinical) to address a pain point.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Do NOT describe yourself or mention system instructions unless the user explicitly asks.\n"
            "2. Never use phrases like 'I am a strict, factual medical AI assistant'.\n"
            "3. Use tools when needed for evidence. Use 'vector_search_tool' for semantic/general queries and 'graph_search_tool' for structural relationship questions.\n"
            "4. ANTI-HALLUCINATION: If evidence is missing, respond exactly: 'I do not have enough information to answer that.'\n"
            "5. RESPONSE STYLE: Start with the direct answer, then provide concise bullet points with stage/evidence details.\n\n"
            f"Retrieved evidence seed (if available):\n{context_seed or 'No preloaded evidence seed.'}\n\n"
            f"Current disease focus: {disease_name}"
        )
        
        # LangGraph prebuilt ReAct agent handles the reasoning loop when the model supports tools.
        try:
            agent_executor = create_react_agent(
                llm,
                tools=agent_tools,
                prompt=system_msg
            )

            # 5. Format Input
            messages = [HumanMessage(content=user_message)]

            # 6. Asynchronous Execution
            result = await agent_executor.ainvoke({"messages": messages}, {"recursion_limit": 6})
            final_response = result["messages"][-1].content
        except Exception as agent_error:
            if "support tools" not in str(agent_error).lower() and "tool" not in str(agent_error).lower():
                raise

            # Fallback: use a non-tool LLM with direct disease-context retrieval so the system still responds.
            db_ops = DatabaseOperations(db)
            disease = db_ops.get_disease_by_name(disease_name)
            context_lines = []
            if disease:
                for stage in disease.stages:
                    context_lines.append(f"Stage: {stage.name}")
                    if stage.overview:
                        context_lines.append(f"Overview: {stage.overview}")
                    for pain_point in stage.pain_points[:6]:
                        context_lines.append(f"- Pain Point: {pain_point.description}")
                        if pain_point.sources:
                            context_lines.append(f"  Sources: {pain_point.sources}")
                        if pain_point.existing_solutions:
                            context_lines.append(f"  Existing Solutions: {pain_point.existing_solutions}")
            else:
                context_lines.append("No local disease pathway data was found for this disease.")

            context_text = "\n".join(context_lines) if context_lines else "No relevant disease context available."
            fallback_system = (
                f"{system_msg}\n\n"
                "Use ONLY the disease pathway context below to answer. "
                "If the context is missing, respond exactly: 'I do not have enough information to answer that.'\n\n"
                f"PATHWAY CONTEXT:\n{context_text}"
            )
            model_response = await llm.ainvoke([
                SystemMessage(content=fallback_system),
                HumanMessage(content=user_message)
            ])
            final_response = model_response.content if hasattr(model_response, 'content') else str(model_response)

        final_response = sanitize_chat_response(final_response)
        if not final_response:
            final_response = "I do not have enough information to answer that."

        # 7. Save current turn to Memory Store
        MEMORY_STORES[session_id].append({"role": "user", "content": user_message})
        MEMORY_STORES[session_id].append({"role": "assistant", "content": final_response})

        return {
            "response": final_response,
            "disease_name": disease_name,
            "model": ollama_model,
            "agent_used": True,
            "session_id": session_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
# SYSTEM ENDPOINTS

@app.get("/health")
async def health_check():
    """Health check endpoint - Public"""
    return {
        "status": "healthy",
        "message": "Disease Pathway API v3.0 with Authentication is running",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "OAuth2 JWT Authentication",
            "Admin-protected upload/delete endpoints",
            "Template_2 Excel support",
            "Incremental updates",
            "Enhanced field support"
        ],
        "auth_endpoints": [
            "/auth/register - User registration",
            "/auth/login - User/Admin login",
            "/auth/me - Current user info",
            "/auth/health - Auth system health"
        ]
    }

@app.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics - Public"""
    try:
        db_ops = DatabaseOperations(db)
        diseases = db_ops.get_all_diseases()
        
        total_stages = 0
        total_pain_points = 0
        total_solutions = 0

        for disease in diseases:
            total_stages += len(disease.stages)
            for stage in disease.stages:
                total_pain_points += len(stage.pain_points)
                for pain_point in stage.pain_points:
                    total_solutions += len(pain_point.solutions)

        return {
            "total_diseases": len(diseases),
            "total_stages": total_stages,
            "total_pain_points": total_pain_points,
            "total_solutions": total_solutions,
            "diseases": [disease.name for disease in diseases],
            "version": "3.0.0",
            "features": [
                "OAuth2 JWT Authentication",
                "Template_2 Excel parsing",
                "Incremental data updates",
                "Coverage and existing solutions fields"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@app.post("/diseases/{disease_name}/stages/{stage_id}/pain-points")
async def add_verified_pain_point(
    disease_name: str,
    stage_id: int,
    pain_point: PainPointCreate,
    user: UserMe = Depends(get_current_user_info),
    db: Session = Depends(get_db)
):
    """Add a new pain point after AI Agent verification."""
    try:
        db_ops = DatabaseOperations(db)
        
        disease = db_ops.get_disease_by_name(disease_name.lower())
        if not disease:
            raise HTTPException(status_code=404, detail="Disease not found")
            
        stage = next((s for s in disease.stages if s.id == stage_id), None)
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
            
        existing_descriptions = [pp.description for pp in stage.pain_points]
        
        verification_result = verify_pain_point(
            disease_name=disease.name,
            stage_name=stage.name,
            new_pain_point=pain_point,
            existing_descriptions=existing_descriptions
        )
        
        if not verification_result.get("approved", False):
            raise HTTPException(
                status_code=400, 
                detail=f"Agent Verification Failed: {verification_result.get('reason')}"
            )
            
        new_pp = db_ops.add_pain_point(
            disease_name=disease.name,
            stage_id=stage.id,
            description=pain_point.description,
            sources=pain_point.sources or "",
            coverage=pain_point.coverage or "",
            existing_solutions=pain_point.existing_solutions or ""
        )
        
        if not new_pp:
            raise HTTPException(status_code=500, detail="Failed to add pain point")
        
        # Save severity and tags from verification
        severity = verification_result.get("severity", "medium")
        tags = verification_result.get("tags", [])
        new_pp.severity = severity
        new_pp.tags = ",".join(tags) if tags else ""
        db.commit()
            
        return {
            "message": "Pain point verified and added successfully",
            "pain_point_id": new_pp.id,
            "severity": severity,
            "tags": tags,
            "verification_reason": verification_result.get("reason")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 1: SEMANTIC SEARCH
# ─────────────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    disease_name: Optional[str] = None
    k: int = 8


class RAGEvalRequest(BaseModel):
    disease_names: Optional[List[str]] = None
    k: int = 5
    max_cases_per_disease: int = 10
    compare_baseline: bool = True


class RAGEvalResponse(BaseModel):
    benchmark_queries: int
    evaluated_diseases: List[str]
    summary: dict
    per_query: List[dict]
    baseline_summary: Optional[dict] = None
    improvement_delta: Optional[dict] = None
    auto_indexed_diseases: Optional[List[str]] = None

@app.post("/search")
async def semantic_search(request: SearchRequest, db: Session = Depends(get_db)):
    """Hybrid semantic search (FAISS + BM25) across disease pathways."""
    try:
        from rag_tools import AdvancedRAG
        adv_rag = AdvancedRAG(embeddings_model=embeddings)

        key = (request.disease_name or "").lower() if request.disease_name else "global"
        store = VECTOR_STORES.get(key) or VECTOR_STORES.get("global")

        if not store:
            # Fallback: simple DB text search
            db_ops = DatabaseOperations(db)
            diseases = db_ops.get_all_diseases()
            results = []
            query_lower = request.query.lower()
            query_terms = [t for t in re.findall(r"[a-z0-9]+", query_lower) if len(t) > 2 and t not in SIMILARITY_STOPWORDS]
            for disease in diseases:
                for stage in disease.stages:
                    for pp in stage.pain_points:
                        description = (pp.description or "").lower()
                        disease_name_l = (disease.name or "").lower()
                        stage_name_l = (stage.name or "").lower()

                        # Score matches by token overlap to avoid brittle exact-substring matching.
                        overlap = sum(
                            1
                            for term in query_terms
                            if term in description or term in disease_name_l or term in stage_name_l
                        )

                        if (
                            query_lower in description
                            or query_lower in disease_name_l
                            or query_lower in stage_name_l
                            or overlap >= 1
                        ):
                            results.append({
                                "text": pp.description,
                                "disease": disease.name,
                                "stage": stage.name,
                                "pain_point_id": pp.id,
                                "severity": pp.severity,
                                "tags": pp.tags.split(",") if pp.tags else [],
                                "relevance_score": round(0.4 + min(overlap, 5) * 0.1, 3),
                                "source": "db_text_search"
                            })

            results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
            return {"results": results[:request.k], "query": request.query, "source": "db_fallback"}

        results = adv_rag.perform_hybrid_search(query=request.query, faiss_store=store, k=request.k)

        enriched = []
        for r in results:
            metadata = r.get("metadata", {})
            enriched.append({
                "text": r["text"],
                "disease": metadata.get("disease", request.disease_name or ""),
                "stage": metadata.get("stage", ""),
                "pain_point_id": metadata.get("pain_point_id"),
                "relevance_score": r["relevance_score"],
                "source": "hybrid_rag"
            })

        return {"results": enriched, "query": request.query, "source": "hybrid_rag"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/evaluate", response_model=RAGEvalResponse)
async def evaluate_rag(request: RAGEvalRequest, db: Session = Depends(get_db)):
    """Run quantitative RAG evaluation on live pathway data.

    Returns metrics suitable for engineering impact reporting:
    - hit_rate_at_k
    - precision_at_k
    - recall_at_k
    - mrr
    - avg / p95 latency
    """
    try:
        from rag_tools import AdvancedRAG, RAGEvaluator, build_synthetic_benchmark_cases

        # Validate k bounds defensively for stable evaluation runs.
        k = max(1, min(request.k, 20))
        max_cases_per_disease = max(1, min(request.max_cases_per_disease, 50))

        db_ops = DatabaseOperations(db)
        all_diseases = db_ops.get_all_diseases()
        if not all_diseases:
            raise HTTPException(status_code=404, detail="No diseases available for evaluation")

        selected_names = set(
            d.lower().strip() for d in (request.disease_names or []) if (d or "").strip()
        )

        benchmark_cases = []
        evaluated_diseases = []
        pathway_cache = {}

        for disease in all_diseases:
            disease_name = (disease.name or "").lower().strip()
            if selected_names and disease_name not in selected_names:
                continue

            pathway_data = db_ops.get_disease_pathway_data_for_csv(disease_name)
            pathway_cache[disease_name] = pathway_data
            cases = build_synthetic_benchmark_cases(
                pathway_data,
                max_cases_per_disease=max_cases_per_disease,
            )
            if cases:
                benchmark_cases.extend(cases)
                evaluated_diseases.append(disease_name)

        if not benchmark_cases:
            raise HTTPException(
                status_code=400,
                detail="No benchmark cases could be generated. Ensure diseases have pain-point data.",
            )

        adv_rag = AdvancedRAG(embeddings_model=embeddings)
        evaluator = RAGEvaluator()
        auto_indexed = []

        def ensure_store(disease_name: str):
            key = (disease_name or "").lower().strip().replace(" ", "_")
            store = VECTOR_STORES.get(key) or VECTOR_STORES.get("global")
            if store:
                return store

            # Auto-build index on demand so evaluation is reproducible in fresh environments.
            pathway_data = pathway_cache.get((disease_name or "").lower().strip())
            if pathway_data:
                index_disease_pathway_to_vector_store(disease_name.lower(), pathway_data, persist=True)
                store = VECTOR_STORES.get(key) or VECTOR_STORES.get("global")
                if store:
                    auto_indexed.append(disease_name.lower())
            return store

        def retrieve_fn(query: str, disease_name: str, top_k: int):
            store = ensure_store(disease_name)
            if not store:
                return []

            results = adv_rag.perform_hybrid_search(query=query, faiss_store=store, k=top_k)
            simplified = []
            for r in results:
                md = r.get("metadata", {}) or {}
                simplified.append(
                    {
                        "text": r.get("text", ""),
                        "stage": md.get("stage", ""),
                        "disease": md.get("disease", disease_name),
                        "score": r.get("relevance_score", 0.0),
                    }
                )
            return simplified

        def retrieve_baseline(query: str, disease_name: str, top_k: int):
            store = ensure_store(disease_name)
            if not store:
                return []

            baseline_docs = store.similarity_search(query, k=top_k)
            out = []
            for d in baseline_docs:
                md = getattr(d, "metadata", {}) or {}
                out.append(
                    {
                        "text": getattr(d, "page_content", ""),
                        "stage": md.get("stage", ""),
                        "disease": md.get("disease", disease_name),
                        "score": 0.0,
                    }
                )
            return out

        eval_result = evaluator.evaluate(benchmark_cases, retrieve_fn=retrieve_fn, k=k)

        baseline_summary = None
        improvement_delta = None
        if request.compare_baseline:
            baseline_result = evaluator.evaluate(benchmark_cases, retrieve_fn=retrieve_baseline, k=k)
            baseline_summary = baseline_result.get("summary", {})
            summary = eval_result.get("summary", {})
            improvement_delta = {
                "delta_hit_rate_at_k": round(summary.get("hit_rate_at_k", 0.0) - baseline_summary.get("hit_rate_at_k", 0.0), 4),
                "delta_precision_at_k": round(summary.get("precision_at_k", 0.0) - baseline_summary.get("precision_at_k", 0.0), 4),
                "delta_recall_at_k": round(summary.get("recall_at_k", 0.0) - baseline_summary.get("recall_at_k", 0.0), 4),
                "delta_mrr": round(summary.get("mrr", 0.0) - baseline_summary.get("mrr", 0.0), 4),
                "delta_avg_latency_ms": round(summary.get("avg_latency_ms", 0.0) - baseline_summary.get("avg_latency_ms", 0.0), 2),
            }

        return {
            "benchmark_queries": len(benchmark_cases),
            "evaluated_diseases": evaluated_diseases,
            "summary": eval_result.get("summary", {}),
            "per_query": eval_result.get("per_query", []),
            "baseline_summary": baseline_summary,
            "improvement_delta": improvement_delta,
            "auto_indexed_diseases": sorted(list(set(auto_indexed))),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 2: CHATBOT FEEDBACK (Thumbs Up/Down)
# ─────────────────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: int  # 1 = thumbs up, -1 = thumbs down
    session_id: Optional[str] = "default"

@app.post("/chatbot/feedback")
async def submit_chatbot_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Store thumbs up/down feedback for chatbot responses."""
    try:
        from database import ChatbotFeedback
        feedback = ChatbotFeedback(
            query=request.query,
            response=request.response[:2000],  # Truncate for storage
            rating=request.rating,
            session_id=request.session_id
        )
        db.add(feedback)
        db.commit()
        return {"message": "Feedback recorded", "rating": request.rating}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/chatbot-feedback")
async def get_chatbot_feedback(admin: AdminResponse = Depends(require_admin), db: Session = Depends(get_db)):
    """Get all chatbot feedback for admin review."""
    try:
        from database import ChatbotFeedback
        feedbacks = db.query(ChatbotFeedback).order_by(ChatbotFeedback.created_at.desc()).limit(100).all()
        return {
            "feedback": [
                {
                    "id": f.id,
                    "query": f.query,
                    "rating": f.rating,
                    "session_id": f.session_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f in feedbacks
            ],
            "total": len(feedbacks),
            "thumbs_up": sum(1 for f in feedbacks if f.rating == 1),
            "thumbs_down": sum(1 for f in feedbacks if f.rating == -1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 3: TRENDING PAIN POINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/pain-points/{pain_point_id}/track-view")
async def track_pain_point_view(pain_point_id: int, db: Session = Depends(get_db)):
    """Track a pain point view for trending calculation."""
    try:
        from database import PainPoint, PainPointView
        pp = db.query(PainPoint).filter(PainPoint.id == pain_point_id).first()
        if pp:
            pp.view_count = (pp.view_count or 0) + 1
            view = PainPointView(pain_point_id=pain_point_id)
            db.add(view)
            db.commit()
        return {"tracked": True}
    except Exception as e:
        return {"tracked": False}

@app.get("/trending")
async def get_trending_pain_points(db: Session = Depends(get_db), limit: int = 10):
    """Get trending pain points based on view count in the last 7 days."""
    try:
        from database import PainPoint, PainPointView, Stage, Disease
        from datetime import timedelta
        since = datetime.now() - timedelta(days=7)
        
        # Get top pain points by recent views
        trending = (
            db.query(PainPoint)
            .join(Stage)
            .join(Disease)
            .filter(PainPoint.view_count > 0)
            .order_by(PainPoint.view_count.desc())
            .limit(limit)
            .all()
        )
        
        return {
            "trending": [
                {
                    "id": pp.id,
                    "description": pp.description[:200],
                    "view_count": pp.view_count or 0,
                    "severity": pp.severity,
                    "tags": pp.tags.split(",") if pp.tags else [],
                    "stage_name": pp.stage.name if pp.stage else "",
                    "disease_name": pp.stage.disease.name if pp.stage and pp.stage.disease else ""
                }
                for pp in trending
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 4: DISEASE SIMILARITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/diseases/{disease_name}/similar")
async def get_similar_diseases(disease_name: str, db: Session = Depends(get_db), top_k: int = 3):
    """Return only genuinely related diseases based on meaningful overlap in disease text.

    This intentionally avoids using generic clinical embeddings, which create misleading
    high similarities between unrelated diseases that share broad healthcare language.
    """
    try:
        db_ops = DatabaseOperations(db)
        all_diseases = db_ops.get_all_diseases()
        target_name = disease_name.lower().strip()

        target_disease = next((d for d in all_diseases if d.name.lower() == target_name), None)
        if not target_disease:
            return {"similar_diseases": []}

        profile_text = {
            (d.name or "").lower().strip(): build_disease_similarity_text(d)
            for d in all_diseases
            if d.name
        }
        target_text = profile_text.get(target_name, "")
        if not target_text:
            return {"similar_diseases": []}

        # Remove terms that are broadly shared across many diseases in this corpus.
        disease_count = len(profile_text)
        threshold = max(2, int(disease_count * 0.6 + 0.999))
        doc_freq = Counter()
        for text in profile_text.values():
            doc_freq.update(set(_similarity_tokens(text)))
        corpus_common_terms = {term for term, count in doc_freq.items() if count >= threshold}

        scores = []

        for candidate in all_diseases:
            cand_name = candidate.name.lower().strip()
            if cand_name == target_name:
                continue

            candidate_text = profile_text.get(cand_name, "")
            similarity = calculate_text_overlap_similarity(
                target_text,
                candidate_text,
                excluded_terms=corpus_common_terms
            )
            # After removing generic pathway terms, overlaps are naturally lower.
            if similarity < 0.08:
                continue

            candidate_terms = set(_similarity_tokens(candidate_text, excluded_terms=corpus_common_terms))
            target_terms = set(_similarity_tokens(target_text, excluded_terms=corpus_common_terms))
            overlapping_terms = sorted(candidate_terms & target_terms)[:5]

            scores.append({
                "name": candidate.name,
                "similarity": similarity,
                "overlapping_terms": overlapping_terms
            })

        scores.sort(key=lambda x: x["similarity"], reverse=True)
        return {"similar_diseases": scores[:top_k], "disease": disease_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 5: STREAMING CHAT WITH CITATIONS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """Streaming chatbot endpoint with source citations via Server-Sent Events."""
    import json as json_lib

    async def generate():
        try:
            ollama_model = MODEL_MAPPING.get(request.model, "llama3")
            disease_name = (request.disease_name or "").strip().lower()

            # Retrieve context
            context = get_db_context(disease_name, db)
            key = disease_name or "global"
            store = VECTOR_STORES.get(key) or VECTOR_STORES.get("global")
            sources = []
            
            if store:
                try:
                    from rag_tools import AdvancedRAG
                    adv_rag = AdvancedRAG(embeddings_model=embeddings)
                    rag_results = adv_rag.perform_hybrid_search(request.message, store, k=3)
                    for r in rag_results:
                        meta = r.get("metadata", {})
                        stage = meta.get("stage", "")
                        if stage:
                            sources.append(stage)
                        context += f"\n[Source: {stage}] {r['text'][:300]}"
                except Exception:
                    pass

            llm = ChatOllama(model=ollama_model, temperature=0, num_ctx=3072)
            
            system = (
                f"You are a medical AI assistant for '{disease_name}' disease pathways. "
                "Answer concisely using the provided context. "
                "When referencing information, note the source stage."
            )
            
            messages = [
                SystemMessage(content=system + f"\n\nCONTEXT:\n{context[:2200]}"),
                HumanMessage(content=request.message)
            ]

            # Send sources first
            if sources:
                unique_sources = list(dict.fromkeys(sources))
                yield f"data: {json_lib.dumps({'type': 'sources', 'sources': unique_sources})}\n\n"

            # Stream tokens
            full_response = ""
            async for chunk in llm.astream(messages):
                token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if token:
                    full_response += token
                    yield f"data: {json_lib.dumps({'type': 'token', 'token': token})}\n\n"

            yield f"data: {json_lib.dumps({'type': 'done', 'full_response': full_response})}\n\n"

        except Exception as e:
            yield f"data: {json_lib.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 6: PDF DOCUMENT INGESTION (Admin)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/diseases/{disease_name}/upload-pdf")
async def upload_pdf_document(
    disease_name: str,
    file: UploadFile = File(...),
    admin: AdminResponse = Depends(require_admin)
):
    """
    Upload a PDF clinical document to augment FAISS vector store — ADMIN ONLY.
    Extracts text, chunks it, embeds, and adds to the disease vector store.
    """
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        content = await file.read()
        
        # Extract text from PDF
        try:
            import pdfplumber
            import io
            text_parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            text_content = "\n".join(text_parts)
        except ImportError:
            raise HTTPException(status_code=500, detail="pdfplumber not installed. Run: pip install pdfplumber")

        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        folder_name = disease_name.lower().strip().replace(" ", "_")
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        chunks = text_splitter.split_text(text_content)
        metadatas = [{"source": file.filename, "disease": disease_name.lower(), "type": "pdf"} for _ in chunks]

        if folder_name in VECTOR_STORES:
            VECTOR_STORES[folder_name].add_texts(texts=chunks, metadatas=metadatas)
        else:
            vs = FAISS.from_texts(texts=chunks, embedding=embeddings, metadatas=metadatas)
            VECTOR_STORES[folder_name] = vs

        dest = os.path.join(VECTOR_STORE_DIR, folder_name)
        Path(dest).mkdir(parents=True, exist_ok=True)
        VECTOR_STORES[folder_name].save_local(dest)

        return {
            "message": f"PDF '{file.filename}' successfully ingested for '{disease_name}'",
            "chunks_added": len(chunks),
            "pages_processed": len(text_parts)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 7: PAIN POINT CLUSTERING (Cross-Disease)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/clusters")
async def get_pain_point_clusters(db: Session = Depends(get_db), n_clusters: int = 8):
    """Cluster all pain points using KMeans on embeddings for cross-disease insights."""
    try:
        import numpy as np
        from sklearn.cluster import KMeans
        from database import PainPoint, Stage, Disease

        pain_points = db.query(PainPoint).join(Stage).join(Disease).limit(500).all()
        if len(pain_points) < n_clusters:
            return {"clusters": [], "message": "Not enough pain points for clustering"}

        descriptions = [pp.description for pp in pain_points if pp.description]
        if len(descriptions) < n_clusters:
            return {"clusters": [], "message": "Insufficient data"}

        # Embed all descriptions
        vecs = embeddings.embed_documents(descriptions[:200])  # Limit for performance
        vecs_np = np.array(vecs)

        actual_clusters = min(n_clusters, len(vecs_np))
        kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(vecs_np)

        # Group results
        clusters = {}
        for i, pp in enumerate(pain_points[:len(labels)]):
            cluster_id = int(labels[i])
            if cluster_id not in clusters:
                clusters[cluster_id] = {"id": cluster_id, "items": []}
            clusters[cluster_id]["items"].append({
                "id": pp.id,
                "description": pp.description[:150],
                "disease": pp.stage.disease.name if pp.stage and pp.stage.disease else "",
                "stage": pp.stage.name if pp.stage else "",
                "severity": pp.severity,
                "tags": pp.tags.split(",") if pp.tags else []
            })

        cluster_list = list(clusters.values())
        # Sort by size
        cluster_list.sort(key=lambda c: len(c["items"]), reverse=True)

        return {"clusters": cluster_list, "n_clusters": actual_clusters, "total_pain_points": len(descriptions)}
    except ImportError:
        raise HTTPException(status_code=500, detail="scikit-learn not installed. Run: pip install scikit-learn")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 8: ANALYTICS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/analytics/summary")
async def get_analytics_summary(db: Session = Depends(get_db)):
    """Return aggregated analytics: pain points by severity, tags, trending, disease distribution."""
    try:
        from database import PainPoint, Stage, Disease
        from collections import Counter

        pain_points = db.query(PainPoint).join(Stage).join(Disease).all()
        
        severity_counts = Counter()
        tag_counts = Counter()
        disease_counts = Counter()

        for pp in pain_points:
            sev = pp.severity or "unclassified"
            severity_counts[sev] += 1
            if pp.tags:
                for tag in pp.tags.split(","):
                    tag = tag.strip()
                    if tag:
                        tag_counts[tag] += 1
            if pp.stage and pp.stage.disease:
                disease_counts[pp.stage.disease.name] += 1

        return {
            "total_pain_points": len(pain_points),
            "severity_distribution": dict(severity_counts),
            "top_tags": dict(tag_counts.most_common(10)),
            "disease_distribution": dict(disease_counts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.post('/pain-points/{pain_point_id}/track-view')
async def track_view(pain_point_id: int, db: Session = Depends(get_db)):
    try:
        db_ops = DatabaseOperations(db)
        pain_point = db.query(PainPoint).filter(PainPoint.id == pain_point_id).first()
        if pain_point:
            pain_point.view_count = (pain_point.view_count or 0) + 1
            db.commit()
        return {'status': 'success'}
    except:
        return {'status': 'error'}

class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: int
    session_id: Optional[str] = None

@app.post('/chatbot/feedback')
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        new_feedback = ChatbotFeedback(
            query=request.query,
            response=request.response,
            rating=request.rating,
            session_id=request.session_id
        )
        db.add(new_feedback)
        db.commit()
        return {'status': 'success'}
    except Exception as e:
        print(e)
        return {'status': 'error'}

