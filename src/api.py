import os
import logging
import re
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, UploadFile, File
import pathlib
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Ensure the conversational_rag module can be imported
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from conversational_rag import ConversationalRAGEngine

# Load configuration from environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title="Autorag_champs RAG API",
    description="Backend API for the RAG Service",
    version="1.0.0"
)

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".html", ".htm"}

# Initialize RAG Engine globally
try:
    rag_engine = ConversationalRAGEngine(min_top_score=0.50)
except Exception as e:
    logging.error(f"Failed to initialize RAG Engine: {e}")
    rag_engine = None


# --- Pydantic Models for Input Validation and Output Structure ---

class HistoryTurn(BaseModel):
    role: str = Field(..., description="Role of the participant, typically 'user' or 'assistant'")
    content: str = Field(..., description="The content of the message")

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question to be answered by the RAG system")
    history: Optional[List[HistoryTurn]] = Field(default=[], description="Optional conversation history")

class QueryResponse(BaseModel):
    original_question: str
    rewritten_query: str
    answer: str
    sources: List[str]
    top_score: float
    status: str


@app.post("/api/v1/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_rag_endpoint(request: QueryRequest):
    """
    Accepts a user question (and optional history) and returns a grounded answer with sources.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty or whitespace.")

    if not rag_engine:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG Engine failed to initialize properly. Check API keys and configuration."
        )

    # Convert Pydantic history objects to dictionaries
    history_dicts = [{"role": turn.role, "content": turn.content} for turn in request.history]

    try:
        # Call the conversational RAG engine
        result = rag_engine.conversational_answer(history_dicts, request.question)
        
        return QueryResponse(
            original_question=result.get("original_question", request.question),
            rewritten_query=result.get("rewritten_query", ""),
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            top_score=result.get("top_score", 0.0),
            status=result.get("status", "unknown")
        )

    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the query: {str(e)}"
        )

@app.post("/api/v1/upload", status_code=status.HTTP_200_OK)
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a document, ingests it, chunks it, generates embeddings, and adds it to the runtime index.
    """
    if not rag_engine:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG Engine is not initialized."
        )

    original_name = pathlib.Path(file.filename or "").name
    suffix = pathlib.Path(original_name).suffix.lower()
    if not original_name or suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
        )

    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 10 MB limit.",
        )

    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", pathlib.Path(original_name).stem).strip("._") or "document"
    stored_name = f"{uuid.uuid4().hex}_{safe_stem}{suffix}"
    stored_path = UPLOAD_DIR / stored_name
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(content)
        import document_loader
        text = document_loader.load_text(stored_path)

    except Exception as e:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from document: {str(e)}",
        )

    import text_cleaning
    text = text_cleaning.clean_text(text)

    if not text.strip():
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No readable text found in document.")

    try:
        result = rag_engine.ingest_and_index_document(text, original_name)
    except Exception as e:
        logging.exception("Failed to process uploaded document '%s'", original_name)
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )

    if result.get("status") == "error":
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("message", "Document embedding or indexing failed."),
        )

    return {
        "filename": original_name,
        "stored_filename": stored_name,
        "status": "success",
        "characters_indexed": len(text),
        "chunks_indexed": result.get("chunks_added", 0),
        "vector_dimensions": result.get("vector_dimensions", 0),
        "index_status": "searchable immediately",
    }

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok", "rag_engine_loaded": rag_engine is not None}

if __name__ == "__main__":
    import uvicorn
    # When running this script directly, start the uvicorn server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
