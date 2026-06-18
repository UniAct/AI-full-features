"""
NLP controller module for handling vector database operations, embedding, and RAG logic.
"""

from .BaseController import BaseController
from models.db_schemes import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypeEnum
from typing import List, Tuple, Optional
import logging
import json
import asyncio
import requests


class NLPController(BaseController):
    """
    Controller for managing NLP-related operations, including interaction with
    VectorDB, LLMs, and template parsing for RAG.
    """

    def __init__(
        self, vectordb_client, generation_client, embedding_client, template_parser
    ):
        """
        Initializes the NLP controller with necessary clients and parsers.
        """
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.logger = logging.getLogger(__name__)

    def create_collection_name(self, project_id: str) -> str:
        """
        Generates a consistent collection name for a project in the vector database.
        """
        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()

    async def reset_vector_db_collection(self, project: Project):
        """
        Deletes the vector database collection associated with a project.
        """
        collection_name = self.create_collection_name(project_id=project.project_id)
        return await self.vectordb_client.delete_collection(
            collection_name=collection_name
        )

    async def get_vector_db_collection_info(self, project: Project) -> dict:
        """
        Retrieves detailed information about a project's vector database collection.
        """
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = await self.vectordb_client.get_collection_info(
            collection_name=collection_name
        )

        # Convert complex objects to JSON-serializable dictionary
        return json.loads(
            json.dumps(
                collection_info, default=lambda x: getattr(x, "__dict__", str(x))
            )
        )

    async def index_into_vector_db(
        self,
        project: Project,
        chunks: List[DataChunk],
        chunks_ids: List[int],
        do_reset: bool = False,
    ) -> bool:
        """
        Embeds and indexes data chunks into the vector database.

        Args:
            project (Project): The project context.
            chunks (List[DataChunk]): List of data chunks to index.
            chunks_ids (List[int]): List of database IDs for the chunks.
            do_reset (bool): Whether to reset the collection before indexing.

        Returns:
            bool: True if indexing was successful.
        """
        collection_name = self.create_collection_name(project_id=project.project_id)

        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]

        # Batch embedding of texts
        vectors = self.embedding_client.embed_text(
            text=texts, document_type=DocumentTypeEnum.DOCUMENT.value
        )

        if not vectors:
            return False

        # Ensure collection exists
        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # Perform batch insertion
        await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids,
        )

        return True

    def _clean_keyword_query(self, query: str) -> str:
        """
        Preprocesses natural language queries to extract meaningful keyword terms,
        filtering out common English stop words and punctuation.
        This prevents Qdrant MatchText (which uses AND-matching) from returning
        zero results due to stop words.
        """
        if not query:
            return ""

        # Common English stop words
        stop_words = {
            "a",
            "about",
            "above",
            "after",
            "again",
            "against",
            "all",
            "am",
            "an",
            "and",
            "any",
            "are",
            "aren't",
            "as",
            "at",
            "be",
            "because",
            "been",
            "before",
            "being",
            "below",
            "between",
            "both",
            "but",
            "by",
            "can",
            "can't",
            "cannot",
            "could",
            "couldn't",
            "did",
            "didn't",
            "do",
            "does",
            "doesn't",
            "doing",
            "don't",
            "down",
            "during",
            "each",
            "few",
            "for",
            "from",
            "further",
            "had",
            "hadn't",
            "has",
            "hasn't",
            "have",
            "haven't",
            "having",
            "he",
            "he'd",
            "he'll",
            "he's",
            "her",
            "here",
            "here's",
            "hers",
            "herself",
            "him",
            "himself",
            "his",
            "how",
            "how's",
            "i",
            "i'd",
            "i'll",
            "i'm",
            "i've",
            "if",
            "in",
            "into",
            "is",
            "isn't",
            "it",
            "it's",
            "its",
            "itself",
            "let's",
            "me",
            "more",
            "most",
            "mustn't",
            "my",
            "myself",
            "no",
            "nor",
            "not",
            "of",
            "off",
            "on",
            "once",
            "only",
            "or",
            "other",
            "ought",
            "our",
            "ours",
            "ourselves",
            "out",
            "over",
            "own",
            "same",
            "shan't",
            "she",
            "she'd",
            "she'll",
            "she's",
            "should",
            "shouldn't",
            "so",
            "some",
            "such",
            "than",
            "that",
            "that's",
            "the",
            "their",
            "theirs",
            "them",
            "themselves",
            "then",
            "there",
            "there's",
            "these",
            "they",
            "they'd",
            "they'll",
            "they're",
            "they've",
            "this",
            "those",
            "through",
            "to",
            "too",
            "under",
            "until",
            "up",
            "very",
            "was",
            "wasn't",
            "we",
            "we'd",
            "we'll",
            "we're",
            "we've",
            "were",
            "weren't",
            "what",
            "what's",
            "when",
            "when's",
            "where",
            "where's",
            "which",
            "while",
            "who",
            "who's",
            "whom",
            "why",
            "why's",
            "with",
            "won't",
            "would",
            "wouldn't",
            "you",
            "you'd",
            "you'll",
            "you're",
            "you've",
            "your",
            "yours",
            "yourself",
            "yourselves",
        }

        # Lowercase and replace non-alphanumeric chars with spaces to simplify splitting
        processed = "".join(c.lower() if c.isalnum() else " " for c in query)
        words = processed.split()

        # Filter out stop words and empty strings
        meaningful_words = [w for w in words if w not in stop_words]

        # If no meaningful words are left, fall back to the original non-empty words
        if not meaningful_words:
            meaningful_words = words

        return " ".join(meaningful_words)

    async def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 10,
        chapters: list = None,
        file_chapter_filters: list = None,
    ):
        """
        Performs hybrid search (dense semantic + keyword) and fuses results with
        Reciprocal Rank Fusion (RRF). The keyword query is automatically derived
        from the user's natural language text — no separate parameter is needed.

        Args:
            project (Project): The project context.
            text (str): The user's natural language search query.
            limit (int): Maximum number of results to return after fusion.
            chapters (list): Optional list of chapter titles to restrict search.
            file_chapter_filters (list): Optional list of dicts mapping file_id to chapter_title.

        Returns:
            List or bool: Fused list of RetrievedDocument or False if search failed.
        """
        collection_name = self.create_collection_name(project_id=project.project_id)
        logger = logging.getLogger("uvicorn.error")
        logger.info(
            f"search_vector_db_collection called: collection={collection_name}; "
            f"limit={limit}; hybrid=True"
        )

        # --- Handle empty text: Just fetch random documents matching the filters ---
        if not text or not text.strip():
            logger.info(
                "Empty search query provided. Fetching random documents matching filters."
            )
            docs = await self.vectordb_client.get_random_documents(
                collection_name=collection_name,
                limit=limit,
                chapters=chapters,
                file_chapter_filters=file_chapter_filters,
            )
            return docs if docs is not None else []

        # --- Step 1: Embed the user query for semantic search ---
        vectors = self.embedding_client.embed_text(
            text=text, document_type=DocumentTypeEnum.QUERY.value
        )
        if not vectors:
            logger.error("Embedding client returned no vectors for query")
            return False

        query_vector = vectors[0] if isinstance(vectors, list) and vectors else None
        if not query_vector:
            return False

        # --- Step 2: Run semantic + keyword searches concurrently ---
        # Over-fetch per retriever leg to give RRF a larger/healthier pool of candidates to fuse.
        # This is a standard production practice (fetching 2-3x limit, minimum 20).
        retriever_limit = max(limit * 3, 20)

        # Preprocess the query to extract meaningful keywords and strip stop words
        # to avoid empty/strict AND matches on full-text indices.
        keyword_query = self._clean_keyword_query(text)

        semantic_task = self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=retriever_limit,
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )
        keyword_task = self.vectordb_client.search_by_keyword(
            collection_name=collection_name,
            keyword_query=keyword_query,
            limit=retriever_limit,
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )
        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )

        logger.info(
            f"Hybrid search: semantic={len(semantic_results or [])}; "
            f"keyword={len(keyword_results or [])}"
        )

        # --- Step 3: Fuse with Reciprocal Rank Fusion ---
        results = self._rrf_rerank(
            [semantic_results or [], keyword_results or []],
            limit=limit,
        )
        logger.info(f"RRF fused results: count={len(results)}")

        return results if results is not None else False

    def _rrf_rerank(self, result_sets: list, limit: int = 10, k: int = 60):
        """
        Fuses multiple ranked result lists using Reciprocal Rank Fusion (RRF).

        RRF score = sum(1 / (k + rank)) across all lists where the document appears.
        k=60 is the standard constant from the original RRF paper (Cormack et al., 2009).

        Args:
            result_sets (list): A list of RetrievedDocument lists from different retrievers.
            limit (int): Maximum number of final results to return.
            k (int): RRF dampening constant (default 60 per the original paper).

        Returns:
            list: Deduplicated, fused, and reranked document list.
        """
        ranked_scores = {}

        for result_set in result_sets:
            if not result_set:
                continue
            for rank, document in enumerate(result_set, start=1):
                # Prefer stable document_id for dedup; fall back to text hash only
                # when document_id is missing (e.g., PGVector returns no id).
                doc_id = getattr(document, "document_id", None)
                document_key = doc_id if doc_id else hash(document.text)

                if document_key not in ranked_scores:
                    ranked_scores[document_key] = {
                        "document": document,
                        "score": 0.0,
                    }
                ranked_scores[document_key]["score"] += 1.0 / (k + rank)

        fused = sorted(
            ranked_scores.values(),
            key=lambda item: item["score"],
            reverse=True,
        )
        return [item["document"] for item in fused][:limit]

    async def answer_rag_question(
        self,
        project: Project,
        query: str,
        limit: int = 10,
        chapters: list = None,
        file_chapter_filters: list = None,
        inject_history: list = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[list]]:
        """
        Generates an answer to a question using the Retrieval-Augmented Generation (RAG) pipeline.

        Args:
            project (Project): The project context.
            query (str): The user's question.
            limit (int): Number of documents to retrieve for context.
            chapters (list): Optional list of chapter titles to restrict search.
            file_chapter_filters (list): Optional list of dictionaries tying file_id explicitly to chapter_title.
            inject_history (list): Optional structured history array bridging past conversation state.

        Returns:
            Tuple: (answer, full_prompt, chat_history)
        """
        answer, full_prompt, chat_history = None, None, None

        # Step 1: Retrieve relevant documents via hybrid search
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )

        # Log retrieval diagnostics for debugging hybrid search behavior
        try:
            logger = logging.getLogger("uvicorn.error")
            docs_count = len(retrieved_documents) if retrieved_documents else 0
            first_preview = (
                (retrieved_documents[0].text[:200] + "...")
                if docs_count > 0
                else "<no-docs>"
            )
            logger.info(
                f"RAG retrieval: docs_count={docs_count}; first_preview={first_preview}"
            )
        except Exception:
            pass

        if not retrieved_documents:
            retrieved_documents = []

        # Step 2: Construct the LLM prompt using templates
        system_prompt = self.template_parser.get("rag", "system_prompt")

        documents_prompts = "\n".join(
            [
                self.template_parser.get(
                    "rag",
                    "document_prompt",
                    {
                        "doc_num": idx + 1,
                        "chunk_text": self.generation_client.process_text(doc.text),
                    },
                )
                for idx, doc in enumerate(retrieved_documents)
            ]
        )

        footer_prompt = self.template_parser.get(
            "rag", "footer_prompt", {"query": query}
        )

        # Step 3: Prepare the generation context
        if inject_history:
            chat_history = inject_history
        else:
            chat_history = [
                self.generation_client.construct_prompt(
                    prompt=system_prompt,
                    role=self.generation_client.enums.SYSTEM.value,
                )
            ]

        full_prompt = "\n\n".join([documents_prompts, footer_prompt])

        # Step 4: Generate the answer
        answer = self.generation_client.generate_text(
            prompt=full_prompt, chat_history=chat_history
        )

        if not answer:
            # Ensure provider exposes a helpful diagnostic when it returns no content.
            try:
                docs_count = len(retrieved_documents) if retrieved_documents else 0
                first_preview = (
                    (retrieved_documents[0].text[:300] + "...")
                    if docs_count > 0
                    else "<no-docs>"
                )
                existing = getattr(self.generation_client, "last_error", None)
                diag = f"LLM returned no content. retrieved_docs={docs_count}; first_doc_preview={first_preview}"
                if existing:
                    diag = existing + " | " + diag
                try:
                    setattr(self.generation_client, "last_error", diag)
                except Exception:
                    pass
            except Exception:
                pass

        return answer, full_prompt, chat_history

    async def summarize_document(self, text: str) -> dict:
        """
        Generates a summary using the configured Summarization API,
        or falls back to the local generation LLM if the URL is not set.
        """
        url = self.app_settings.SUMMARIZATION_API_URL

        if url:
            # The Modal summarization endpoint is a generation API
            # Build a summarization prompt and send it
            summarize_prompt = (
                "Please provide a clear and concise summary of the following text. "
                "Focus on the key points and main ideas.\n\n"
                f"Text to summarize:\n{text}\n\n"
                "Summary:"
            )
            try:
                # Try {"prompt": ...} first (Modal generation endpoint format)
                response = requests.post(url, json={"prompt": summarize_prompt}, timeout=120)
                response.raise_for_status()
                data = response.json()
                result = (
                    data.get("summary")
                    or data.get("response")
                    or data.get("text")
                    or data.get("content")
                    or ""
                )
                if result:
                    return {"summary": result}
            except Exception as e:
                self.logger.warning(f"Summarization API (prompt format) failed: {e}")

            # Fallback: try {"text": ...} format
            try:
                response = requests.post(url, json={"text": text}, timeout=120)
                response.raise_for_status()
                data = response.json()
                result = data.get("summary") or data.get("response") or ""
                if result:
                    return {"summary": result}
            except Exception as e:
                self.logger.error(f"Summarization API (text format) also failed: {e}")
                return {"error": "Failed to generate summary.", "detail": str(e)}

        # Fallback: use the local generation client with a summarization prompt
        self.logger.warning(
            "SUMMARIZATION_API_URL is not set — falling back to local generation LLM."
        )
        try:
            max_chars = getattr(self.app_settings, "INPUT_DAFAULT_MAX_CHARACTERS", 3000) or 3000
            truncated_text = text[:max_chars]

            prompt = (
                "Please provide a clear and concise summary of the following text. "
                "Focus on the key points and main ideas.\n\n"
                f"Text to summarize:\n{truncated_text}\n\n"
                "Summary:"
            )
            chat_history = [
                self.generation_client.construct_prompt(
                    prompt="You are a helpful assistant that creates clear, accurate summaries.",
                    role=self.generation_client.enums.SYSTEM.value,
                )
            ]
            summary = self.generation_client.generate_text(
                prompt=prompt, chat_history=chat_history
            )
            if not summary:
                return {"error": "LLM returned no content for summarization."}
            return {"summary": summary}
        except Exception as e:
            self.logger.error(f"Local summarization fallback failed: {e}")
            return {"error": "Failed to generate summary.", "detail": str(e)}

    async def generate_exam_from_context(
        self,
        project: Project,
        content: str,
        difficulty: str = "medium",
        num_mcq: int = 3,
        num_written: int = 2,
        chapters: list = None,
        file_chapter_filters: list = None,
    ):
        import re as _re

        # ── 1. Build search query ──────────────────────────────────────────────
        chapter_hint = ""
        if chapters:
            chapter_hint = " ".join(chapters)
        elif file_chapter_filters:
            chapter_hint = " ".join(
                f.get("chapter_title", "") for f in file_chapter_filters if f.get("chapter_title")
            )

        search_query = content.strip() if content and content.strip() else chapter_hint.strip()

        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=search_query,
            limit=max(10, num_mcq * 3),
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )

        if not retrieved_documents:
            return {"error": "No relevant context found for the requested exam."}

        # ── 2. Build context (keep it compact) ────────────────────────────────
        context_text = "\n".join(
            [self.generation_client.process_text(doc.text) for doc in retrieved_documents]
        )
        # Keep context under 1500 chars so the model has room to respond
        ctx = context_text[:1500]

        # ── 3. Reliable generation helper: uses Summarization API ─────────────
        summ_url = self.app_settings.SUMMARIZATION_API_URL
        mcq_url  = self.app_settings.MCQ_API_URL
        generation_url = self.app_settings.GENERATION_API_URL

        def call_api(prompt_text: str, max_tokens: int = 400, urls_to_try: list = None) -> str | None:
            """Try the provided API URLs in order, then fallback to generation client."""
            if urls_to_try is None:
                urls_to_try = [summ_url, mcq_url]
                
            for url in urls_to_try:
                if not url:
                    continue
                try:
                    resp = requests.post(
                        url,
                        json={"prompt": prompt_text, "max_tokens": max_tokens},
                        timeout=300,
                    )
                    if resp.ok:
                        data = resp.json()
                        result = data.get("response") or data.get("mcq") or data.get("text")
                        if result and len(result.strip()) > 10:
                            return result
                except Exception as e:
                    self.logger.warning(f"API call to {url} failed: {e}")
            # Last resort: generation client
            return self.generation_client.generate_text(prompt=prompt_text)

        # ── 4. Parse a single-question JSON object from raw text ──────────────
        def extract_json_object(raw: str) -> dict | None:
            if not raw:
                return None
            text = raw.strip()
            # Strip <think> blocks
            text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL).strip()
            # Strip markdown fences
            text = _re.sub(r'^```(?:json)?\s*', '', text, flags=_re.MULTILINE)
            text = _re.sub(r'\s*```$', '', text, flags=_re.MULTILINE)
            text = text.strip()

            # Direct parse
            try:
                return json.loads(text)
            except Exception:
                pass

            # Find first {...} block
            start = text.find('{')
            if start != -1:
                depth = 0
                for i, ch in enumerate(text[start:], start):
                    if ch == '{': depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start:i+1])
                            except Exception:
                                break
            return None

        # ── 5. Generate MCQ questions via fine-tuned LoRA model ─────────────────
        async def generate_mcqs():
            mcq_prompt = (
                f"You are an expert exam creator. Read the text below carefully and create "
                f"EXACTLY {num_mcq} multiple-choice questions.\n"
                f"Difficulty Level: {difficulty}\n\n"
                f"TEXT:\n{ctx}\n\n"
                f"INSTRUCTIONS:\n"
                f"- Each question must test a DIFFERENT concept from the text.\n"
                f"- Each question must have exactly 4 distinct answer options labeled A, B, C, D.\n"
                f"- Only one option should be correct.\n"
                f"- Provide a brief explanation of why the answer is correct.\n\n"
                f"Respond with ONLY a valid JSON array of {num_mcq} questions:\n"
                f'[{{"question":"...", "options":["A. ...","B. ...","C. ...","D. ..."], "answer":"A. ...", "answer_explanation":"..."}}]'
            )
            raw = await asyncio.to_thread(call_api, mcq_prompt, 1200, [mcq_url])
            if not raw:
                return []
            # Try to parse as array first, then as object with "mcq" key
            text = raw.strip()
            import re as _re2
            text = _re2.sub(r'<think>.*?</think>', '', text, flags=_re2.DOTALL).strip()
            text = _re2.sub(r'^```(?:json)?\s*', '', text, flags=_re2.MULTILINE)
            text = _re2.sub(r'\s*```$', '', text, flags=_re2.MULTILINE)
            text = text.strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [q for q in parsed if isinstance(q, dict) and q.get("question")]
                elif isinstance(parsed, dict):
                    arr = parsed.get("mcq", parsed.get("questions", []))
                    return [q for q in arr if isinstance(q, dict) and q.get("question")]
            except Exception:
                pass
            # Fallback: extract first JSON object/array
            obj = extract_json_object(raw)
            if isinstance(obj, dict) and obj.get("question"):
                return [obj]
            if isinstance(obj, dict):
                arr = obj.get("mcq", obj.get("questions", []))
                return [q for q in arr if isinstance(q, dict) and q.get("question")]
            return []

        # ── 6. Generate written questions via summarization model ──────────────
        async def generate_written():
            written_prompt = (
                f"You are an expert exam creator. Read the text below carefully and create "
                f"EXACTLY {num_written} short-answer questions.\n"
                f"Difficulty Level: {difficulty}\n\n"
                f"TEXT:\n{ctx}\n\n"
                f"INSTRUCTIONS:\n"
                f"- Each question must test a DIFFERENT concept from the text.\n"
                f"- Provide a clear question and a comprehensive model answer.\n\n"
                f"Respond with ONLY a valid JSON array of {num_written} questions:\n"
                f'[{{"question":"...", "answer":"..."}}]'
            )
            raw = await asyncio.to_thread(call_api, written_prompt, 800, [summ_url, generation_url])
            if not raw:
                return []
            text = raw.strip()
            import re as _re2
            text = _re2.sub(r'<think>.*?</think>', '', text, flags=_re2.DOTALL).strip()
            text = _re2.sub(r'^```(?:json)?\s*', '', text, flags=_re2.MULTILINE)
            text = _re2.sub(r'\s*```$', '', text, flags=_re2.MULTILINE)
            text = text.strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [q for q in parsed if isinstance(q, dict) and q.get("question")]
                elif isinstance(parsed, dict):
                    arr = parsed.get("written", parsed.get("questions", []))
                    return [q for q in arr if isinstance(q, dict) and q.get("question")]
            except Exception:
                pass
            obj = extract_json_object(raw)
            if isinstance(obj, dict) and obj.get("question"):
                return [obj]
            if isinstance(obj, dict):
                arr = obj.get("written", obj.get("questions", []))
                return [q for q in arr if isinstance(q, dict) and q.get("question")]
            return []

        # ── 7. Run MCQ and Written generation in parallel ──────────────────────
        mcq_questions, written_questions = await asyncio.gather(
            generate_mcqs(), generate_written()
        )

        # ── 7. Assemble result ────────────────────────────────────────────────
        if not mcq_questions and not written_questions:
            return {"error": "All question generation attempts failed. Please try again."}

        return {
            "file_id": project.project_id,
            "chapters": ", ".join(chapters) if chapters else chapter_hint,
            "difficulty": difficulty,
            "mcq_questions": mcq_questions,
            "written_questions": written_questions,
        }



    async def summarize_from_context(
        self,
        project: Project,
        content: str = "",
        chapters: list = None,
        file_chapter_filters: list = None,
    ) -> dict:
        """
        Summarizes chapters/content from the project by retrieving from VectorDB.
        """
        # 1. Retrieve relevant documents from VectorDB
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=content or "Summarize the key points of the selected chapters.",
            limit=20,
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )

        if not retrieved_documents:
            return {"error": "No relevant context found to summarize for the requested filters."}

        # 2. Build context string
        context_text = "\n".join(
            [self.generation_client.process_text(doc.text) for doc in retrieved_documents]
        )

        # 3. Generate summary using the configured Summarization API
        url = self.app_settings.SUMMARIZATION_API_URL
        if url:
            summarize_prompt = (
                "Please provide a clear, comprehensive, and well-structured summary of the following text.\n"
                "Focus on the main ideas, key concepts, and important details.\n\n"
                f"Text to summarize:\n{context_text}\n\n"
                "Summary:"
            )
            try:
                response = requests.post(url, json={"prompt": summarize_prompt}, timeout=300)
                response.raise_for_status()
                data = response.json()
                result = (
                    data.get("summary")
                    or data.get("response")
                    or data.get("text")
                    or data.get("content")
                    or ""
                )
                if result:
                    return {"summary": result}
            except Exception as e:
                self.logger.warning(f"Summarization API (prompt format) failed: {e}")
        
        # Fallback to general text generation if Modal summarize fails or is unset
        prompt = (
            "Please provide a clear and concise summary of the following text.\n\n"
            f"Text:\n{context_text}"
        )
        answer = self.generation_client.generate_text(
            prompt=prompt,
            chat_history=[
                self.generation_client.construct_prompt(
                    prompt=prompt,
                    role=self.generation_client.enums.USER.value,
                )
            ],
        )
        if not answer:
            return {"error": "Failed to generate summary from the LLM backend."}
            
        return {"summary": answer}


    # async def evaluate_rag(
    #     self,
    #     project: Project,
    #     questions: list,
    # ) -> dict:
    #     """
    #     Runs RAGAS evaluation on a set of questions for a project.
    #     """
    #     from datasets import Dataset
    #     from ragas import evaluate
    #     from ragas.metrics import (
    #         faithfulness,
    #         answer_relevancy,
    #         context_precision,
    #         context_recall,
    #     )
    #     from ragas.llms import LangchainLLMWrapper
    #     from ragas.embeddings import LangchainEmbeddingsWrapper
    #     from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    #     import pandas as pd
    #     import os

    #     # Collect data
    #     eval_data = []
    #     for q_item in questions:
    #         question = q_item.get("question")
    #         reference = q_item.get("reference") or ""

    #         # Retrieve contexts
    #         retrieved_documents = await self.search_vector_db_collection(
    #             project=project,
    #             text=question,
    #             limit=5,
    #         )
    #         contexts = (
    #             [doc.text for doc in retrieved_documents] if retrieved_documents else []
    #         )

    #         # Get generated answer
    #         answer, _, _ = await self.answer_rag_question(
    #             project=project,
    #             query=question,
    #             limit=5,
    #         )
    #         if not answer:
    #             answer = ""

    #         eval_data.append(
    #             {
    #                 "question": question,
    #                 "contexts": contexts,
    #                 "answer": answer,
    #                 "ground_truth": reference,
    #             }
    #         )

    #     # Convert to HuggingFace Dataset
    #     dataset = Dataset.from_dict(
    #         {
    #             "question": [x["question"] for x in eval_data],
    #             "contexts": [x["contexts"] for x in eval_data],
    #             "answer": [x["answer"] for x in eval_data],
    #             "ground_truth": [x["ground_truth"] for x in eval_data],
    #         }
    #     )

    #     # Load OpenAI API Key from app env
    #     openai_api_key = os.getenv("OPENAI_API_KEY")
    #     if not openai_api_key:
    #         return {"error": "OPENAI_API_KEY not found in environment."}

    #     # Initialize LLM & Embeddings
    #     lc_llm = ChatOpenAI(model="gpt-5-nano", api_key=openai_api_key)
    #     lc_embeddings = OpenAIEmbeddings(
    #         model="text-embedding-3-small", api_key=openai_api_key
    #     )

    #     evaluator_llm = LangchainLLMWrapper(lc_llm)
    #     evaluator_embeddings = LangchainEmbeddingsWrapper(lc_embeddings)

    #     # Run evaluation
    #     result = evaluate(
    #         dataset=dataset,
    #         metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    #         llm=evaluator_llm,
    #         embeddings=evaluator_embeddings,
    #     )

    #     # Format scores
    #     avg_scores = {k: float(v) for k, v in result.items()}
    #     per_question_scores = []
    #     df_res = result.to_pandas()
    #     for _, row in df_res.iterrows():
    #         per_question_scores.append(
    #             {
    #                 "question": row["question"],
    #                 "answer": row["answer"],
    #                 "contexts": row["contexts"],
    #                 "ground_truth": row["ground_truth"],
    #                 "scores": {
    #                     "faithfulness": float(row["faithfulness"])
    #                     if not pd.isna(row["faithfulness"])
    #                     else None,
    #                     "answer_relevancy": float(row["answer_relevancy"])
    #                     if not pd.isna(row["answer_relevancy"])
    #                     else None,
    #                     "context_precision": float(row["context_precision"])
    #                     if not pd.isna(row["context_precision"])
    #                     else None,
    #                     "context_recall": float(row["context_recall"])
    #                     if not pd.isna(row["context_recall"])
    #                     else None,
    #                 },
    #             }
    #         )

    #     return {"avg_scores": avg_scores, "per_question_scores": per_question_scores}
