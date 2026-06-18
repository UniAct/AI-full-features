# RAG Application Endpoints

This document outlines all the available API endpoints for the RAG application, designed to help set up a Postman collection.

## Base URL
Assuming the app is running locally on port 5000:
`http://localhost:5000`

---

## 1. Base Endpoint

### Welcome
*   **Method**: `GET`
*   **Endpoint**: `{{api}}/api/v1/`
*   **Description**: Checks if the API is up and returns basic application information.
*   **Payload**: None
*   **Successful Output (HTTP 200)**:
    ```json
    {
      "app_name": "rag-app",
      "app_version": "0.1"
    }
    ```

---

## 2. Data Endpoints

### Upload File
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/data/upload/{project_id}`
*   **Description**: Uploads a document (e.g., PDF, TXT) to be associated with a specific project.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (form-data)**:
    *   `file`: The file to upload.
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "File uploaded successfully.",
        "file_id": "651a2b3c4d5e..."
    }
    ```
*   **Error Output (HTTP 400)**: returns appropriate `signal` message (e.g. invalid type, size exceeded, upload failed).

### Process Files
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/data/process/{project_id}`
*   **Description**: Parses and chunks either a specific file or all files in a project, preparing them for vectorization.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (JSON)**:
    ```json
    {
        "file_id": "string",  // Optional. If null, processes all files in project
        "chunk_size": 100,    // Optional. Default 100
        "chunk_overlap": 20,  // Optional. Default 20
        "do_reset": 0         // Optional. 1 to reset chunks & vectors, 0 to append (default)
    }
    ```
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "Processing successfully.",
        "inserted_chunks": 54,
        "processed_files": 1
    }
    ```
*   **Error Output (HTTP 400)**: returns appropriate `signal` message.

---

### List Project Files
*   **Method**: `GET`
*   **Endpoint**: `{{api}}/api/v1/data/files/{project_id}`
*   **Description**: Returns a listing of files associated with a project from both the database assets table and the project filesystem directory. This is intended as a debugging/help endpoint to verify uploaded assets and stored files match.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "Project files retrieved.",
        "assets": [
            {"asset_id": "651a2b3c4d5e...", "asset_name": "file.pdf", "asset_size": 12345}
        ],
        "filesystem": [
            {"name": "file.pdf", "size": 12345}
        ]
    }
    ```
*   **Error Output (HTTP 500)**: returns a logged error if filesystem cannot be read.
---

## 3. NLP Endpoints

### Push to Vector DB
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/nlp/index/push/{project_id}`
*   **Description**: Embeds the processed text chunks and indexes them into the vector database.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (JSON)**:
    ```json
    {
        "do_reset": 0  // Optional. 1 to recreate collection, 0 to append (default)
    }
    ```
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "Successfully inserted into vector database.",
        "inserted_items_count": 54
    }
    ```
*   **Error Output (HTTP 400)**: returns appropriate `signal` message.

### Get Index Info
*   **Method**: `GET`
*   **Endpoint**: `{{api}}/api/v1/nlp/index/info/{project_id}`
*   **Description**: Retrieves statistics and metadata about the project's vector collection.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload**: None
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "Vector database collection retrieved.",
        "collection_info": {
            // ... detailed DB specific stats
        }
    }
    ```

### Search Index
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/nlp/index/search/{project_id}`
*   **Description**: Performs semantic search against the indexed documents.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (JSON)**:
    ```json
    {
        "text": "Your search query here", // Required
        "limit": 5,                     // Optional. Default is 5
        "chapters": ["Chapter 1", "Chapter 2"], // Optional. Filter by specific chapter titles across all files
        "file_chapter_filters": [               // Optional. Filter precisely by book/file ID AND chapter title
            {"file_id": "fileA_uuid", "chapter_title": "Chapter 1"},
            {"file_id": "fileB_uuid", "chapter_title": "Chapter 5"}
        ]
    }
    ```
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "Vector database search successful.",
        "results": [
            {
                "text": "The relevant chunk text...",
                "score": 0.893
            },
            // ... more results
        ]
    }
    ```
*   **Error Output (HTTP 400)**: returns appropriate `signal` message if search errors occur.

### Answer Question (RAG)
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/nlp/index/answer/{project_id}`
*   **Description**: Queries the system using Retrieval-Augmented Generation to get a generated answer based on retrieved documents.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (JSON)**:
    ```json
    {
        "text": "Your factual question here", // Required
        "limit": 5,                         // Optional. Default is 5
        "chapters": ["Chapter 1", "Chapter 2"], // Optional. Filter by specific chapter titles across all files
        "file_chapter_filters": [               // Optional. Filter precisely by book/file ID AND chapter title
            {"file_id": "fileA_uuid", "chapter_title": "Chapter 1"},
            {"file_id": "fileB_uuid", "chapter_title": "Chapter 5"}
        ]
    }
    ```
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "RAG answer generated successfully.",
        "answer": "The generated answer from the LLM.",
        "full_prompt": "The complete prompt sent to the LLM (including retrieved context)",
        "chat_history": [
            // List of message dictionaries sent to the LLM
        ]
    }
    ```
*   **Error Output (HTTP 400)**: returns appropriate `signal` message if answering fails.

### Generate Exam from Context (RAG)
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/nlp/index/exam/{project_id}`
*   **Description**: Generates an exam from indexed content using retrieval-augmented generation. The endpoint can filter by `file_id`, `chapters`, or both, and returns MCQ + written questions based only on the selected context.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (JSON)**:
    ```json
    {
        "content": "Topic or content query for the exam.",
        "difficulty": "medium",          // Optional. Could be easy, medium, hard.
        "num_mcq": 3,                    // Optional. Number of MCQ questions.
        "num_written": 2,                // Optional. Number of written questions.
        "chapters": ["Chapter 5"],      // Optional. Filter by chapter titles across all files.
        "file_chapter_filters": [
            {
                "file_id": "fileA_uuid",
                "chapter_title": "Chapter 5"
            }
        ]
    }
    ```
*   **Note**: `chapters` is a broad chapter-only filter. `file_chapter_filters` is more specific and can target both a file and a chapter in the same request. You can use either field alone or both together if you want to narrow results further.
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "RAG exam generated successfully.",
        "exam": {
            "file_id": "fileA_uuid",
            "chapters": ["Chapter 5"],
            "difficulty": "medium",
            "mcq_questions": [
                {
                    "question": "What is ...?",
                    "choices": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "answer_explanation": "Because ..."
                }
            ],
            "written_questions": [
                {
                    "question": "Explain ...",
                    "answer": "..."
                }
            ]
        }
    }
    ```
*   **Error Output (HTTP 400)**: returns an error signal if exam generation fails, or if the requested content is not available in the selected context.

---

## 4. Evaluation Endpoints

### Evaluate RAG Pipeline (RAGAS)
*   **Method**: `POST`
*   **Endpoint**: `{{api}}/api/v1/nlp/index/evaluate/{project_id}`
*   **Description**: Evaluates the RAG pipeline using RAGAS across faithfulness, answer relevancy, context precision, and context recall.
*   **Path Variables**:
    *   `project_id` (string): The identifier for your project.
*   **Payload (JSON)**:
    ```json
    {
        "questions": [
            {
                "question": "What is the primary objective of ...?",
                "reference": "The primary objective is to ..."
            },
            {
                "question": "Who is ...?",
                "reference": null
            }
        ]
    }
    ```
*   **Successful Output (HTTP 200)**:
    ```json
    {
        "signal": "RAGAS evaluation successful.",
        "avg_scores": {
            "faithfulness": 0.892,
            "answer_relevancy": 0.915,
            "context_precision": 0.850,
            "context_recall": 0.880
        },
        "per_question_scores": [
            {
                "question": "What is the primary objective of ...?",
                "answer": "The primary objective is to ...",
                "contexts": [
                    "Context chunk 1 ...",
                    "Context chunk 2 ..."
                ],
                "ground_truth": "The primary objective is to ...",
                "scores": {
                    "faithfulness": 1.0,
                    "answer_relevancy": 0.95,
                    "context_precision": 1.0,
                    "context_recall": 1.0
                }
            }
        ]
    }
    ```
*   **Error Output (HTTP 400)**: returns an error signal if the evaluation fails or if the OpenAI key is missing.

