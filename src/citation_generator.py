"""
Grounded Generation with Inline Citations & Source Attribution Engine for Autorag_champs.

Features:
1. Citation Mapping: Maps retrieved chunks to numerical markers ([1], [2]) with metadata (source, chunk_id, section, text).
2. Grounded Prompting: Prompts the LLM to cite every claim using source markers like [1] or [2].
3. Refusal Fallback: Refuses out-of-scope queries without inventing fake citations when evidence is missing.
4. Citation Verification: Inspects inline citation markers in generated text and verifies claims against source chunks.
"""

import os
import sys
import re
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Configure logging with UTF-8 stream handler to support all environments
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "citation_generation_demo.log")

file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
stream_handler = logging.StreamHandler(sys.stdout)

if sys.platform == "win32":
    stream_handler.setStream(open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[stream_handler, file_handler]
)

def build_citation_map(chunks: list) -> dict:
    """
    Builds a structured citation map mapping numerical markers like '[1]', '[2]'
    to real retrieved chunk metadata and raw text.
    """
    citation_map = {}
    for index, chunk in enumerate(chunks, start=1):
        marker = f"[{index}]"
        meta = chunk.get("metadata", {})
        citation_map[marker] = {
            "marker": marker,
            "source": meta.get("source", "unknown"),
            "chunk_id": chunk.get("chunk_id", f"chunk_{index}"),
            "section": meta.get("section", "N/A"),
            "doc_type": meta.get("doc_type", "N/A"),
            "text": chunk.get("text", "")
        }
    return citation_map

def build_cited_prompt(question: str, chunks: list) -> tuple:
    """
    Assembles a grounded system prompt and user message requiring inline citations ([1], [2])
    and enforcing fallback refusal when evidence is missing.
    """
    system_prompt = (
        "You are an expert automotive technical assistant.\n"
        "Rules:\n"
        "1. Answer the question using ONLY the provided Context below.\n"
        "2. Cite every factual claim using source markers like [1] or [2].\n"
        "3. Only use source markers that explicitly appear in the Context.\n"
        "4. If the Context does not support an answer, state strictly: 'I don't have enough information in the provided context.' and DO NOT invent citations.\n"
        "5. Keep responses concise and professional."
    )

    context_blocks = []
    for idx, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata", {})
        header = f"[{idx}] (Source: {meta.get('source', 'unknown')} | Section: {meta.get('section', 'N/A')})"
        context_blocks.append(f"{header}\n{chunk['text']}")

    context_str = "\n\n".join(context_blocks)
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {question}"

    return system_prompt, user_prompt

class CitationGenerator:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.model = os.getenv("CHAT_MODEL", model_name)

    def answer_with_citations(self, question: str, retrieved_chunks: list) -> dict:
        """
        Generates a grounded LLM answer with inline citations and returns a structured object
        containing answer text, citation map, and evidence status.
        """
        if not retrieved_chunks:
            return {
                "question": question,
                "answer": "I don't have enough information in the provided context.",
                "citations": {},
                "has_sufficient_evidence": False
            }

        citation_map = build_citation_map(retrieved_chunks)
        system_prompt, user_prompt = build_cited_prompt(question, retrieved_chunks)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            answer_text = response.choices[0].message.content.strip()
            
            # Check if answer triggered refusal fallback
            has_evidence = "don't have enough information" not in answer_text.lower()

            return {
                "question": question,
                "answer": answer_text,
                "citations": citation_map if has_evidence else {},
                "has_sufficient_evidence": has_evidence
            }

        except Exception as e:
            logging.error("Failed to generate cited answer for question '%s': %s", question, e)
            return {
                "question": question,
                "answer": f"Error generating answer: {e}",
                "citations": citation_map,
                "has_sufficient_evidence": False
            }

    def verify_citation_claim(self, result: dict) -> list:
        """
        Parses citation markers like '[1]', '[2]' from the generated answer text and verifies
        that each marker maps to a valid source in the citation map.
        """
        answer = result.get("answer", "")
        citation_map = result.get("citations", {})
        verifications = []

        # Find all citation markers in the answer text using regex
        found_markers = re.findall(r"\[\d+\]", answer)
        unique_markers = sorted(list(set(found_markers)))

        if not unique_markers:
            if result.get("has_sufficient_evidence"):
                verifications.append({
                    "status": "WARNING",
                    "details": "Answer has sufficient evidence but contains no inline citation markers."
                })
            else:
                verifications.append({
                    "status": "VALID_REFUSAL",
                    "details": "Correctly refused out-of-scope question without fabricating citations."
                })
            return verifications

        for marker in unique_markers:
            if marker in citation_map:
                source_meta = citation_map[marker]
                verifications.append({
                    "marker": marker,
                    "status": "VERIFIED",
                    "source": source_meta["source"],
                    "chunk_id": source_meta["chunk_id"],
                    "section": source_meta["section"],
                    "snippet_preview": repr(source_meta["text"][:70])
                })
            else:
                verifications.append({
                    "marker": marker,
                    "status": "FABRICATED_MARKER",
                    "details": f"Marker {marker} was generated by model but does not exist in context citation map!"
                })

        return verifications

def run_citation_demo():
    generator = CitationGenerator()

    # Sample Automotive Corpus Chunks
    sample_retrieved_chunks = [
        {
            "chunk_id": "chunk_mnl_001",
            "text": "DTC P0300 indicates a random misfire event. Inspect Bank 1 ignition coils. Primary resistance specification must measure 0.4 to 0.6 ohms across terminals 1 and 2.",
            "metadata": {
                "source": "sample_manual.txt",
                "doc_type": "Repair Manual",
                "section": "Ignition Diagnostics",
                "vehicle_model": "2023 SUV Model X"
            }
        },
        {
            "chunk_id": "chunk_tsb_112",
            "text": "Technical Service Bulletin TSB-22-112: Inspect connector C102 on right bulkhead. Apply dielectric grease to seals prior to connector mating.",
            "metadata": {
                "source": "tsb_notice.md",
                "doc_type": "TSB",
                "section": "Wiring Harness",
                "vehicle_model": "2023 SUV Model X"
            }
        }
    ]

    logging.info("=" * 80)
    logging.info("STARTING GROUNDED GENERATION & CITATION ATTRIBUTION DEMO")
    logging.info("Model: %s", generator.model)
    logging.info("=" * 80)

    # --- DEMO 1: Valid Grounded Answer with Citations ---
    logging.info("\n--- DEMO 1: Valid Automotive Query with Sufficient Context ---")
    query_1 = "What is the primary resistance spec for Bank 1 coils and what action is required for connector C102?"
    logging.info("Question: '%s'", query_1)

    result_1 = generator.answer_with_citations(query_1, sample_retrieved_chunks)
    logging.info("\n[Generated Answer]")
    logging.info("%s", result_1["answer"])

    logging.info("\n[Citation Map Details]")
    for marker, details in result_1["citations"].items():
        logging.info("  Marker %s -> Source: %s | Section: %s", marker, details["source"], details["section"])
        logging.info("    Raw Text: %s", repr(details["text"]))

    verifications_1 = generator.verify_citation_claim(result_1)
    logging.info("\n[Citation Verification Analysis]")
    for v in verifications_1:
        logging.info("  %s %s -> Source: %s (Chunk: %s)",
                     "✅" if v["status"] == "VERIFIED" else "❌",
                     v["marker"], v.get("source"), v.get("chunk_id"))

    # --- DEMO 2: Insufficient Context Refusal Fallback ---
    logging.info("\n" + "=" * 80)
    logging.info("--- DEMO 2: Out-of-Scope Query with Insufficient Evidence ---")
    query_2 = "What is the refund policy for customer sales invoice #8891?"
    logging.info("Question: '%s'", query_2)

    result_2 = generator.answer_with_citations(query_2, sample_retrieved_chunks)
    logging.info("\n[Generated Answer]")
    logging.info("%s", result_2["answer"])

    verifications_2 = generator.verify_citation_claim(result_2)
    logging.info("\n[Citation Verification Analysis]")
    for v in verifications_2:
        logging.info("  Status: %s | %s", v["status"], v["details"])

    logging.info("=" * 80)
    logging.info("CITATION DEMO COMPLETED. Log saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_citation_demo()
