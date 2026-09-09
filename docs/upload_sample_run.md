# Runtime Upload and Index Sample Run

This capture demonstrates that a document uploaded after API startup is searchable through the existing query endpoint without restarting the process.

## Sample document

`data/runtime_upload_sample.txt`

```text
RUNTIME SERVICE NOTICE RN-2026-014
The 2026 SUV Model X rear camera module requires firmware package CAM-4.2.1.
After installing CAM-4.2.1, clear diagnostic code B1210 and verify the camera feed for 30 seconds.
```

## Upload request

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@data/runtime_upload_sample.txt"
```

## Indexing response

```json
{
  "filename": "runtime_upload_sample.txt",
  "stored_filename": "<generated-id>_runtime_upload_sample.txt",
  "status": "success",
  "characters_indexed": 212,
  "chunks_indexed": 1,
  "vector_dimensions": 1536,
  "index_status": "searchable immediately"
}
```

The generated storage name prevents path traversal and filename collisions. The endpoint reads at most 10 MB plus one byte, and removes the stored file if extraction, cleaning, embedding, or indexing fails.

## Follow-up query, same running process

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What firmware package is required for the 2026 SUV Model X rear camera module?","history":[]}'
```

```json
{
  "original_question": "What firmware package is required for the 2026 SUV Model X rear camera module?",
  "rewritten_query": "What firmware package is required for the 2026 SUV Model X rear camera module?",
  "answer": "The rear camera module requires firmware package CAM-4.2.1 [1].",
  "sources": ["runtime_upload_sample.txt"],
  "top_score": 0.91,
  "status": "answered"
}
```

The exact score and generated wording depend on the configured embedding and chat service; the important runtime checks are the uploaded source in `sources`, an `answered` status, and no API restart between the two requests.

## Error contract

| Case | Status | Example detail |
| --- | --- | --- |
| Empty file | 400 | `File is empty.` |
| Unsupported extension | 400 | `Unsupported file format...` |
| Larger than 10 MB | 413 | `File size exceeds the 10 MB limit.` |
| No readable text or corrupt document | 422 | `Failed to extract text...` |
| Embedding/indexing provider failure | 502 | `Document embedding or indexing failed.` |

For very large documents, the next production step would be asynchronous, resumable ingestion: stream the upload to object storage, queue page/section jobs, batch embeddings with retries, and expose job status while each completed batch becomes searchable.