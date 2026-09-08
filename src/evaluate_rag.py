import os
import sys
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
from conversational_rag import ConversationalRAGEngine

os.makedirs("outputs", exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Test Set
TEST_SET = [
    {
        "id": "test_1",
        "question": "What is the diagnostic troubleshooting procedure for DTC P0300?",
        "expected_sources": ["sample_manual.txt"],
        "expected_answer_keywords": ["random misfire", "Bank 1 ignition coils", "0.4 to 0.6 ohms"]
    },
    {
        "id": "test_2",
        "question": "What connector should I inspect for misfire issues?",
        "expected_sources": ["tsb_notice.md"],
        "expected_answer_keywords": ["C102", "bulkhead wiring harness"]
    },
    {
        "id": "test_3",
        "question": "What is the recall notice for false thermal management warnings on the 2023 SUV Model X?",
        "expected_sources": ["recall_report.html"],
        "expected_answer_keywords": ["RCL-23-088B", "v1.0.0"]
    },
    {
        "id": "test_4",
        "question": "How do I bake a chocolate cake?",
        "expected_sources": [],
        "expected_answer_keywords": ["don't have enough", "cannot answer"]
    }
]

class RAGEvaluator:
    def __init__(self):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.eval_model = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
        self.rag_engine = ConversationalRAGEngine(min_top_score=0.50)

    def score_answer_with_llm(self, question, answer, context, expected_keywords):
        system_prompt = (
            "You are an expert judge evaluating a RAG (Retrieval-Augmented Generation) system. "
            "You will be given a Question, a Generated Answer, Retrieved Context, and a list of Expected Keywords. "
            "You must score the Generated Answer on two dimensions: Correctness and Grounding, each on a scale of 1 to 5.\n\n"
            "1. Correctness (1-5): Does the answer correctly address the question and include the expected keywords? (5 = perfect match, 1 = completely wrong or missing key facts).\n"
            "2. Grounding (1-5): Is the answer fully supported by the provided Context? (5 = fully supported with no hallucinations, 1 = major hallucinations or statements not in context).\n\n"
            "Respond in pure JSON format: {\"correctness\": <int>, \"grounding\": <int>, \"reasoning\": \"<string>\"}"
        )
        
        user_prompt = (
            f"Question: {question}\n\n"
            f"Expected Keywords: {expected_keywords}\n\n"
            f"Retrieved Context:\n{context}\n\n"
            f"Generated Answer:\n{answer}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.eval_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logging.error(f"LLM Evaluation failed: {e}")
            return {"correctness": 0, "grounding": 0, "reasoning": f"Error: {str(e)}"}

    def run_evaluation(self):
        results = []
        
        for test in TEST_SET:
            logging.info(f"Evaluating: {test['id']} - {test['question']}")
            
            # 1. Run RAG
            history = []
            response = self.rag_engine.conversational_answer(history, test["question"])
            
            answer = response["answer"]
            generated_sources = response["sources"]
            
            # Re-fetch chunks just for context string (ConversationalRAGEngine doesn't return raw text)
            chunks = self.rag_engine.retrieve_chunks(test["question"])
            strong_chunks = [c for c in chunks if c["score"] >= self.rag_engine.min_top_score]
            context_str = "\n".join([c["text"] for c in strong_chunks])
            
            # 2. Score Citation Accuracy
            expected_sources = set(test["expected_sources"])
            actual_sources = set(generated_sources)
            citation_pass = True
            if expected_sources:
                citation_pass = expected_sources.issubset(actual_sources)
            elif actual_sources: # if we expected no sources (out of domain), but got some, it's a fail
                 # Exception: If the model refused, sources might be empty anyway.
                 citation_pass = len(actual_sources) == 0
                 
            # 3. Score Correctness and Grounding with LLM
            # For out-of-domain questions, we expect refusal.
            if not expected_sources:
                # If refused correctly, correctness = 5, grounding = 5
                if "don't have enough" in answer.lower() or "cannot answer" in answer.lower():
                    llm_eval = {"correctness": 5, "grounding": 5, "reasoning": "Correctly refused to answer out of domain question."}
                else:
                    llm_eval = {"correctness": 1, "grounding": 1, "reasoning": "Failed to refuse out of domain question."}
            else:
                llm_eval = self.score_answer_with_llm(test["question"], answer, context_str, test["expected_answer_keywords"])

            results.append({
                "test_id": test["id"],
                "question": test["question"],
                "answer": answer,
                "correctness": llm_eval.get("correctness", 0),
                "grounding": llm_eval.get("grounding", 0),
                "citation_pass": citation_pass,
                "reasoning": llm_eval.get("reasoning", "")
            })

        return results

    def summarize_results(self, results):
        total_tests = len(results)
        avg_correctness = sum(r["correctness"] for r in results) / total_tests
        avg_grounding = sum(r["grounding"] for r in results) / total_tests
        citation_accuracy = sum(1 for r in results if r["citation_pass"]) / total_tests * 100

        summary = (
            "RAG Evaluation Summary\n"
            "======================\n"
            f"Total Tests: {total_tests}\n"
            f"Average Correctness: {avg_correctness:.2f} / 5.0\n"
            f"Average Grounding: {avg_grounding:.2f} / 5.0\n"
            f"Citation Accuracy: {citation_accuracy:.1f}%\n\n"
        )

        summary += "Detailed Results:\n"
        summary += "-----------------\n"
        failures = []
        for r in results:
            summary += f"Test ID: {r['test_id']}\n"
            summary += f"Q: {r['question']}\n"
            summary += f"Correctness: {r['correctness']} | Grounding: {r['grounding']} | Citation Pass: {r['citation_pass']}\n"
            summary += f"Reasoning: {r['reasoning']}\n\n"
            
            if r["correctness"] < 4 or r["grounding"] < 4 or not r["citation_pass"]:
                failures.append(r)

        if failures:
            summary += "Notable Failures:\n"
            summary += "-----------------\n"
            for f in failures:
                summary += f"Test ID: {f['test_id']} failed. Likely Cause: {f['reasoning']}\n"
        else:
            summary += "No notable failures detected. All systems nominal.\n"

        with open(os.path.join(os.path.dirname(__file__), "..", "outputs", "evaluation_summary.txt"), "w") as f:
            f.write(summary)
            
        print(summary)

if __name__ == "__main__":
    evaluator = RAGEvaluator()
    print("Starting Evaluation...")
    results = evaluator.run_evaluation()
    evaluator.summarize_results(results)
    print("Evaluation complete. Results saved to outputs/evaluation_summary.txt")
