import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
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

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok", "rag_engine_loaded": rag_engine is not None}

if __name__ == "__main__":
    import uvicorn
    # When running this script directly, start the uvicorn server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
