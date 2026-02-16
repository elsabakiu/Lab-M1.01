import random
import re
import time

from openai import OpenAI, RateLimitError

from lab2_rag_openai.config import get_chat_model, get_embedding_model, get_required_env


class OpenAIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=get_required_env("OPENAI_API_KEY"))
        self.embedding_model = get_embedding_model()
        self.chat_model = get_chat_model()

    def _extract_retry_seconds(self, error_message: str) -> float | None:
        ms_match = re.search(r"try again in\s+(\d+)ms", error_message, re.IGNORECASE)
        if ms_match:
            return max(0.1, int(ms_match.group(1)) / 1000.0)

        sec_match = re.search(r"try again in\s+(\d+(?:\.\d+)?)s", error_message, re.IGNORECASE)
        if sec_match:
            return max(0.1, float(sec_match.group(1)))

        return None

    def _create_embeddings_with_retry(self, model: str, input_batch: list[str], max_retries: int = 6):
        for attempt in range(max_retries + 1):
            try:
                return self.client.embeddings.create(model=model, input=input_batch)
            except RateLimitError as exc:
                if attempt >= max_retries:
                    raise

                suggested = self._extract_retry_seconds(str(exc))
                base_wait = suggested if suggested is not None else min(10.0, 0.5 * (2**attempt))
                jitter = random.uniform(0, 0.25)
                time.sleep(base_wait + jitter)

        # This is unreachable, but keeps type checkers satisfied.
        return self.client.embeddings.create(model=model, input=input_batch)

    def get_embeddings_batch(
        self,
        texts: list[str],
        model: str | None = None,
        batch_size: int = 100,
        log_progress: bool = True,
    ) -> list[list[float]]:
        """
        Generate embeddings in batches.

        `batch_size` controls count-based batching, while an additional
        conservative token estimate (chars / 4) keeps each request under
        OpenAI per-request limits.
        """
        if not texts:
            return []

        embedding_model = model or self.embedding_model
        max_estimated_tokens_per_request = 200_000
        embeddings: list[list[float]] = []

        def est_tokens(value: str) -> int:
            return max(1, len(value) // 4)

        total = len(texts)
        processed = 0

        for i in range(0, total, batch_size):
            raw_batch = texts[i : i + batch_size]

            # Secondary split to avoid token cap in one embeddings request.
            safe_batch: list[str] = []
            safe_batch_tokens = 0
            request_batches: list[list[str]] = []

            for text in raw_batch:
                text_tokens = est_tokens(text)
                if safe_batch and safe_batch_tokens + text_tokens > max_estimated_tokens_per_request:
                    request_batches.append(safe_batch)
                    safe_batch = []
                    safe_batch_tokens = 0

                safe_batch.append(text)
                safe_batch_tokens += text_tokens

            if safe_batch:
                request_batches.append(safe_batch)

            for request_batch in request_batches:
                response = self._create_embeddings_with_retry(model=embedding_model, input_batch=request_batch)
                embeddings.extend(row.embedding for row in response.data)
                processed += len(request_batch)
                if log_progress:
                    print(f"Processed {processed}/{total} chunks")

        return embeddings

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Backward-compatible helper that uses default model and batching."""
        return self.get_embeddings_batch(texts=texts, model=None, batch_size=100, log_progress=False)

    def answer_with_context(self, question: str, context_chunks: list[str]) -> str:
        context = "\n\n".join(context_chunks)
        prompt = (
            "You are a helpful assistant. Use ONLY the provided context to answer. "
            "If the answer is not in context, say you don't have enough information.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}"
        )
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": "You answer based on retrieved documents."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""
