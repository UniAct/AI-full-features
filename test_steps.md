# Comprehensive Testing Guide for RAG Application

This guide provides step-by-step instructions for testing the **entire end-to-end capabilities** of the application. It covers infrastructure health checks, database vector visualization, Prometheus/Grafana telemetry, and the complete API pipeline lifecycle.

---

## 1. Prerequisites Setup

Before testing, you must configure the environment parameters correctly to ensure smooth communication between the FastAPI app, the vector databases (PGVector & Qdrant), and the monitoring stack.

1. **Initialize Environment Files**
   Navigate to the `docker/env` directory and duplicate the templates:
   ```bash
   cd docker/env
   cp .env.example.app .env.app
   cp .env.example.postgres .env.postgres
   cp .env.example.grafana .env.grafana
   cp .env.example.postgres-exporter .env.postgres-exporter
   ```
   *Note: Open `.env.app` and ensure your LLM API Keys (e.g., OPENAI_API_KEY, COHERE_API_KEY) are populated.*

2. **Initialize Database Alembic Environments**
   Navigate to the Docker app directory and create the Alembic configuration:
   ```bash
   cd ../ragapp
   cp alembic.example.ini alembic.ini
   cd ../..
   ```

3. **Install Dependencies Locally (Optional but Recommended)**
   Ensure the local Python environment has the synced dependencies via `uv`.
   ```bash
   uv sync
   ```

---

## 2. Infrastructure Deployment & Health Checks

We run 8 interdependent services. You have two distinct ways to run and test the application depending on your goal.

### Option A: Local Development (Testing via Postman)
*Use this option if you want to run the FastAPI application code locally on your Windows machine so you can easily trace and edit code, while databases and monitoring run in Docker.*

1. **Start Infrastructure Services (No App)**
   From the project root directory, run:
   ```bash
   cd docker
   docker compose up pgvector qdrant prometheus grafana node-exporter postgres-exporter -d
   ```
2. **Start FastAPI Locally**
   Open a new terminal, navigate to the `src` folder, and run this command. (Note: Because `src/.env` is built for Docker and uses `POSTGRES_HOST="pgvector"`, you must temporarily set your host back to localhost when testing locally, otherwise it won't be able to find the database):
   ```bash
   # Make sure POSTGRES_HOST="localhost" in src/.env for this step to work!
   cd src
   uv run uvicorn main:app --reload --host 0.0.0.0 --port 5000
   ```
   *(Note: The Postman `api` for this method must be `http://localhost:5000` since Nginx is not running).*

### Option B: Full Dockerized Build (Production Paradigm)
*Use this option to fully build the FastAPI application into a Docker image, running the entire ecosystem exclusively through Docker.*

1. **Start the Complete Stack**
   From the project root directory, run:
   ```bash
   cd docker
   docker compose up --build -d
   ```
   *(Note: The Postman `base_url` for this method is `http://localhost/api/v1`, hitting Port 80 via Nginx).*

2. **Verify Docker Container Health**
   Run `docker compose ps` to verify the state of your application. You should see `Up` for all services (`fastapi`, `nginx`, `pgvector`, `qdrant`, `prometheus`, etc).

3. **Check Logs for Connection Errors**
   Ensure FastAPI successfully connected to the databases:
   ```bash
   docker compose logs --tail=50 fastapi
   ```

---

## 3. UI and Monitoring Services Testing

Before hitting the API with payloads, verify that the graphical and telemetry interfaces are responding.

### A. Grafana Dashboards
1. Open up **Grafana** in your browser at [http://localhost:3000](http://localhost:3000).
2. Login securely (default credentials: `admin` / `admin_password` inside `.env.grafana`).
3. Verify that the dashboards (FastAPI, Qdrant, Postgres) are receiving data metrics by selecting them from your loaded dashboards list.

### B. Prometheus Targets
1. Open **Prometheus** at [http://localhost:9090/targets](http://localhost:9090/targets).
2. Ensure that endpoints for `fastapi`, `node-exporter`, `qdrant`, and `postgres-exporter` are present and marked as **UP**.

### C. Qdrant Dashboard
1. Open the **Qdrant visual UI** at [http://localhost:6333/dashboard](http://localhost:6333/dashboard).
2. This is your native view into Qdrant collections. Initially, it will be empty until you push data later.

### D. PostgreSQL Validation (via DBeaver)
1. Open **DBeaver** on your desktop.
2. Create a New Database Connection -> **PostgreSQL**.
3. **Host**: `localhost`, **Port**: `5432`.
4. **Database**: `uniAct` (or whatever you set `POSTGRES_MAIN_DATABASE` to in `.env.app`).
5. **Username**: `postgres`, **Password**: *(matching your `.env.postgres`)*.
6. Click **Test Connection**. Once successful, explore `Schemas -> public -> Tables` to confirm Alembic migrations created tables like `data_chunks` and `assets`.

---

## 4. End-to-End API Pipeline Testing (Postman)

Now we test the full lifecycle of a document entering the system, chunking, embedding, being queried, and passing to the LLM.

### Postman Setup Routine
1. Open **Postman** and create a New Collection: `RAG System Full Tests`.
2. Add Collection Variables:
   *   `api` = `http://localhost:8000` *(Note: hitting the app locally)*
   *   `project_id` = `test_project_alpha`

### Test 1: Service Welcome Status
*Verifies the core FastAPI python logic triggers successfully through Nginx.*
- **Method**: `GET`
- **URL**: `{{api}}/api/v1/`
- **Expected Outcome (200 OK)**:
  ```json
  {
    "app_name": "mini-RAG",
    "app_version": "0.1"
  }
  ```

### Test 2: Upload Document
*Uploads a binary context file directly to the server's storage volume.*
- **Method**: `POST`
- **URL**: `{{api}}/api/v1/data/upload/{{project_id}}`
- **Body**: (form-data)
  *   Key: `file` (Change type to 'File')
  *   Value: *Select a readable PDF or TXT from your computer.*
- **Expected Outcome (200 OK)**: Returns `"signal": "File uploaded successfully."` along with a unique `file_id`.

 - **Expected Outcome (200 OK)**: Returns `"signal": "File uploaded successfully."` along with a unique `file_id`.

### Test 2.5: List Project Files
*   **Method**: `GET`
*   **URL**: `{{api}}/api/v1/data/files/{{project_id}}`
*   **Description**: Verify that the uploaded file is visible both in the database `assets` table and on the project filesystem, and that names/sizes match.
*   **Expected Outcome (200 OK)**:
   ```json
   {
      "signal": "Project files retrieved.",
      "assets": [ {"asset_id":"...", "asset_name":"file.pdf", "asset_size": 12345} ],
      "filesystem": [ {"name":"file.pdf","size":12345} ]
   }
   ```
*   **Validation**: Confirm `asset_name` equals a filename present in `filesystem` and sizes are consistent. If missing, use this to debug `/process` 400 responses.

### Test 3: Data Parsing & Chunking
*Extracts text content and splits it into manageable pieces with defined overlap.*
- **Method**: `POST`
- **URL**: `{{api}}/api/v1/data/process/{{project_id}}`
- **Body**: (JSON)
  ```json
  {
      "chunk_size": 150,
      "chunk_overlap": 20,
      "do_reset": 0
  }
  ```
- **Expected Outcome (200 OK)**: Evaluates file size and returns the `inserted_chunks` count confirming splitting logic.
- **Validation**: Open *DBeaver*, check `data_chunks` table, and visually inspect that `chunk_text` has successfully separated the textual paragraphs.

### Test 4: Encode and Push to Vector DB
*Passes text chunks into the active embedding model and commits them into mathematical Vector Collections.*
- **Method**: `POST`
- **URL**: `{{api}}/api/v1/nlp/index/push/{{project_id}}`
- **Body**: (JSON)
  ```json
  {
      "do_reset": 0
  }
  ```
- **Expected Outcome (200 OK)**: Returns the total `inserted_items_count`.
- **Validation**: 
  *   *If PGVector*: Check the `data_chunks` vector embeddings array column in DBeaver.
  *   *If Qdrant*: Open the [Qdrant Dashboard](http://localhost:6333/dashboard) -> Collections, find your `test_project_alpha`, and inspect the 3D-points and metadata.

### Test 5: Verify Collection Info
*Retrieves real-time metadata statistics directly from the database.*
- **Method**: `GET`
- **URL**: `{{api}}/api/v1/nlp/index/info/{{project_id}}`
- **Expected Outcome (200 OK)**: Returns Vector DB diagnostics specific to your collection.

### Test 6: Semantic Proximity Search
*Tests the backend mathematical retrieval without generating an LLM response.*
- **Method**: `POST`
- **URL**: `{{api}}/api/v1/nlp/index/search/{{project_id}}`
- **Body**: (JSON)
  ```json
  {
      "text": "[Type an explicit factual concept from your uploaded file]",
      "limit": 4,
      "file_chapter_filters": [
          {"file_id": "[Your_File_ID]", "chapter_title": "Chapter 1. Introduction"}
      ]
  }
  ```
- **Expected Outcome (200 OK)**: An array of `results` containing the exact matching contextual chunks and their similarity `score` metrics.

### Test 7: Full Generation Output (RAG)
*Retrieves similar nodes mathematically, mounts a prompt template, and sends sequential history to the LLM to provide a final worded answer.*
- **Method**: `POST`
- **URL**: `{{api}}/api/v1/nlp/index/answer/{{project_id}}`
- **Body**: (JSON)
  ```json
  {
      "text": "Based on the content, explain [the concept]?",
      "limit": 4,
      "file_chapter_filters": [
          {"file_id": "[Book1_File_ID]", "chapter_title": "Chapter 1. Introduction"},
          {"file_id": "[Book2_File_ID]", "chapter_title": "Chapter 5. Methods"}
      ]
  }
  ```
- **Expected Outcome (200 OK)**:
  1.  `answer`: A fully structured and cohesive AI response.
  2.  `full_prompt`: Proof of the context the LLM used.
  3.  `chat_history`: Demonstrating the conversation array builder works.

### Test 8: Generate Exam from Context
*Creates an exam with multiple-choice and written questions using only the selected project context.*
- **Method**: `POST`
- **URL**: `{{api}}/api/v1/nlp/index/exam/{{project_id}}`
- **Body**: (JSON)
  ```json
  {
      "content": "Provide exam questions based on the selected project content.",
      "difficulty": "medium",
      "num_mcq": 3,
      "num_written": 2,
      "chapters": ["Chapter 5"],
      "file_chapter_filters": [
          {"file_id": "[Your_File_ID]", "chapter_title": "Chapter 5"}
      ]
  }
  ```
- **Note**: You do not need to provide both filters. `chapters` filters by chapter title across all files, while `file_chapter_filters` targets a specific file and chapter. Use one or the other unless you want both conditions applied together.
- **Expected Outcome (200 OK)**:
  1.  `signal`: `RAG exam generated successfully.`
  2.  `exam`: JSON containing `file_id`, `chapters`, `difficulty`, `mcq_questions`, and `written_questions`.
  3.  MCQ questions must include 4 answer choices and a correct answer.
  4.  Written questions must include a question and its answer.
  5.  The content should be derived only from the provided context.

---

## 5. Vector Database Swap Testing

The project is highly decoupled, supporting both **QDRANT** and **PGVECTOR**. By default, one is initialized. You must test both to ensure factory implementations are fundamentally robust.

1. **Change the Environment Variable**
   Open `docker/env/.env.app` and locate `VECTOR_DB_BACKEND`.
   *   Switch it (e.g., from `"PGVECTOR"` to `"QDRANT"`).
2. **Reload the FastAPI Application**
   ```bash
   docker compose restart fastapi
   ```
3. **Execute the Push Test Again**
   Use Postman to call `/nlp/index/push/{{project_id}}` again with `do_reset: 1`.
4. **Validation**
   Verify the logs or Qdrant/DBeaver UI to explicitly ensure the secondary vector database caught the data ingestion cleanly.

---

## 6. Real-Time Telemetry & Metric Load Testing

After executing multiple tests via Postman, test the monitoring architecture's feedback loops.

1. **Generate Load:** Rapidly press **Send** on the `Test 6: Semantic Proximity Search` endpoint multiple times to simulate heavy incoming traffic.
2. **View System Exhaust:** Hop back to **Grafana** ([http://localhost:3000](http://localhost:3000)).
3. **Observe Revisions:** 
   *   In the **FastAPI Observability Dashboard**, you should see the `HTTP Request Count` and `Request Rate` spike significantly.
   *   In the **Qdrant/Postgres Dashboards**, query operation latency peaks should manifest, proving that telemetry hooks natively into the Python runtime.

---

## 7. Troubleshooting Common Issues

### Port Allocation Error
**Symptoms:** 
When running `docker compose up`, you receive an error similar to this:
`Error response from daemon: failed to set up container networking... Bind for 0.0.0.0:6333 failed: port is already allocated`

**Cause:**
Another background process (like a native Windows installation of Qdrant, another Docker container, or an orphaned service) is currently using that port (e.g., 6333 for Qdrant, 5432 for Postgres, or 8000 for FastAPI).

**Resolution (Windows):**
You must identify and kill the process holding the port hostage.

1. **Find the Process ID (PID) holding the port:**
   Open Command Prompt or PowerShell as Administrator and run:
   ```cmd
   netstat -ano | findstr :6333
   ```
   *(Replace `6333` with whatever port is conflicting).*
   This will output a line ending in a number (e.g., `LISTENING  12345`). That number `12345` is the PID.

2. **Kill the Process:**
   Force-kill the process using its PID:
   ```cmd
   taskkill /PID 12345 /F
   ```
   *(Replace `12345` with the PID you found).*

3. **Alternative (If it's an orphaned Docker container):**
   If the port is held by an old forgotten Docker container:
   ```bash
   # List all containers (even stopped ones)
   docker ps -a
   
   # Stop and remove any conflicting containers
   docker stop <container_id>
   docker rm <container_id>
   ```

4. **Retry:**
   Run `docker compose up -d` again. The service should now boot properly.

### Docker Engine / Pipe Connection Error
**Symptoms:**
You receive an error resembling:
`error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine... open //./pipe/... The system cannot find the file specified."`

**Cause:**
The Docker Desktop background daemon has unexpectedly crashed or frozen on Windows. It has lost its connection to the Linux subsystem engine. This often happens if you try to bind ports forcefully or during heavy memory spikes.

**Resolution:**
You simply need to restart the Docker Engine.
1. Look at your Windows System Tray (bottom right of your screen).
2. Right-click the **Docker Desktop** whale icon.
3. Click **Restart Docker Desktop** (or click **Quit Docker Desktop**, wait 5 seconds, and open the application again from the Start Menu).
4. Wait until the Docker Desktop interface says **"Engine running"** (usually takes about 30-60 seconds).
5. Run your `docker compose up` command again.

---

## 9. RAG Evaluation with RAGAS (Option 1 — Automatic Testset)

This section walks through how to automatically evaluate the quality of your RAG system using [RAGAS](https://docs.ragas.io/en/stable/).

### Step 1: Create a test dataset
Open and run `notebooks/build_testset.ipynb`. This notebook:
- Extracts raw chunks from the PGVector database via the FastAPI backend search endpoint.
- Uses OpenAI to generate a synthetic Q&A test set of 15 questions, along with the reference answers and source contexts.
- Saves the generated testset to `notebooks/eval_results/testset.csv`.

### Step 2: Run the offline evaluation notebook
Open and run `notebooks/ragas_evaluation.ipynb`. This notebook:
- Loads `notebooks/eval_results/testset.csv`.
- Queries the running FastAPI instance to collect retriever contexts and generated answers for each question.
- Invokes Ragas with four key metrics: **Faithfulness**, **Answer Relevancy**, **Context Precision**, and **Context Recall**.
- Saves the result details to `notebooks/eval_results/results.csv` and outputs a summary.

### Step 3: Run real-time evaluation via API
Alternatively, you can query the `/api/v1/nlp/index/evaluate/{project_id}` endpoint directly.
Send a `POST` request with your questions:
```bash
curl -X POST "http://localhost:8000/api/v1/nlp/index/evaluate/<project_id>" \
     -H "Content-Type: application/json" \
     -d '{
       "questions": [
         {
           "question": "What is the primary objective of ...?",
           "reference": "The primary objective is to ..."
         }
       ]
     }'
```
This returns the average RAGAS scores across all questions and the individual score details per question.



