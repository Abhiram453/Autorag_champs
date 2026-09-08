# Sample API Request and Response

To interact with the RAG service, you can send a POST request to the `/api/v1/query` endpoint with your question.

## Sample Request
Using `curl` from the terminal:

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{
           "question": "What is the diagnostic troubleshooting procedure for DTC P0300 on 2023 SUV Model X?",
           "history": []
         }'
```

## Sample Response
The backend will validate the request, run the RAG pipeline, and return a structured JSON response containing the grounded answer and sources:

```json
{
  "original_question": "What is the diagnostic troubleshooting procedure for DTC P0300 on 2023 SUV Model X?",
  "rewritten_query": "What is the diagnostic troubleshooting procedure for DTC P0300 on 2023 SUV Model X?",
  "answer": "The diagnostic troubleshooting procedure for DTC P0300 (random misfire) indicates you should inspect the Bank 1 ignition coils. The primary resistance specification must measure between 0.4 to 0.6 ohms across terminals 1 and 2 [1].",
  "sources": [
    "sample_manual.txt"
  ],
  "top_score": 0.8521,
  "status": "answered"
}
```

## Error Handling Examples

**1. Bad Request (Missing/Empty Question)**
Request:
```bash
curl -X POST "http://localhost:8000/api/v1/query" -H "Content-Type: application/json" -d '{"question": ""}'
```
Response (`400 Bad Request` or `422 Unprocessable Entity`):
```json
{
  "detail": "Question cannot be empty or whitespace."
}
```

**2. Out of Domain Query (No Context)**
Request:
```bash
curl -X POST "http://localhost:8000/api/v1/query" -H "Content-Type: application/json" -d '{"question": "How do I bake a cake?"}'
```
Response (`200 OK` but gracefully refused):
```json
{
  "original_question": "How do I bake a cake?",
  "rewritten_query": "How do I bake a cake?",
  "answer": "I don't have enough reliable context in the service manuals to answer that.",
  "sources": [],
  "top_score": 0.0,
  "status": "refused_weak_context"
}
```
