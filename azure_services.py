"""
azure_services.py
-----------------
Real Azure service integrations for AgentGuard.
Provides singleton wrappers for Azure OpenAI, Cosmos DB, and AI Content Safety.
All methods include error handling and graceful degradation.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Any
from functools import lru_cache
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Simple in-memory cache to avoid redundant Azure OpenAI calls
# ─────────────────────────────────────────────────────────────
_llm_cache: dict[str, str] = {}

def _cache_key(prompt: str) -> str:
    """SHA-256 digest used as cache key so long prompts don't pollute memory."""
    return hashlib.sha256(prompt.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════
# AZURE OPENAI SERVICE
# ═══════════════════════════════════════════════════════════════

class AzureOpenAIService:
    """
    Singleton wrapper around the Azure OpenAI client.
    Uses in-memory caching (ENABLE_CACHING=true) to reduce API costs during demos.
    """

    _instance: Optional["AzureOpenAIService"] = None

    def __new__(cls) -> "AzureOpenAIService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            from openai import AzureOpenAI  # type: ignore

            self.client = AzureOpenAI(
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_KEY"],
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-14"),
            )
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
            self.caching_enabled = os.getenv("ENABLE_CACHING", "true").lower() == "true"
            self._initialized = True
            logger.info("AzureOpenAIService initialized (deployment=%s)", self.deployment)
        except Exception as exc:
            logger.error("Failed to initialize AzureOpenAIService: %s", exc)
            self.client = None
            self._initialized = True  # prevent retry loops

    # ----------------------------------------------------------
    def chat_complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> Optional[str]:
        """
        Call Azure OpenAI chat completion.
        Returns the assistant's message string, or None on failure.
        Caches results keyed on (system_prompt + user_message) to save costs.
        """
        if self.client is None:
            logger.warning("AzureOpenAIService not available; returning None")
            return None

        cache_key = _cache_key(system_prompt + user_message)
        if self.caching_enabled and cache_key in _llm_cache:
            logger.debug("LLM cache hit")
            return _llm_cache[cache_key]

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content or ""
            if self.caching_enabled:
                _llm_cache[cache_key] = result
            return result
        except Exception as exc:
            err_str = str(exc)
            # Content filter triggered — do NOT cache, let caller handle as None
            if "content_filter" in err_str or "ResponsibleAIPolicyViolation" in err_str:
                logger.info("Azure OpenAI content filter triggered (expected for attack scenarios)")
            else:
                logger.error("Azure OpenAI chat_complete error: %s", exc)
            return None

    # ----------------------------------------------------------
    def test_connection(self) -> dict:
        """Quick connectivity test — returns status dict."""
        response = self.chat_complete(
            system_prompt="You are a test assistant.",
            user_message="Reply with exactly: OK",
            max_tokens=10,
        )
        success = response is not None and "OK" in response
        return {"service": "Azure OpenAI", "status": "connected" if success else "error", "response": response}


# ═══════════════════════════════════════════════════════════════
# COSMOS DB SERVICE
# ═══════════════════════════════════════════════════════════════

class CosmosDBService:
    """
    Singleton wrapper around Azure Cosmos DB for NoSQL.
    Handles audit-log writes and query operations.
    Partition key: /session_id
    """

    _instance: Optional["CosmosDBService"] = None

    def __new__(cls) -> "CosmosDBService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            from azure.cosmos import CosmosClient, exceptions as cosmos_exc  # type: ignore

            self._cosmos_exc = cosmos_exc
            endpoint = os.environ["COSMOS_ENDPOINT"]
            key = os.environ["COSMOS_KEY"]
            database_name = os.getenv("COSMOS_DATABASE", "agentguard-db")
            container_name = os.getenv("COSMOS_CONTAINER", "decisions-logs")

            self.client = CosmosClient(endpoint, credential=key)
            self.database = self.client.get_database_client(database_name)
            self.container = self.database.get_container_client(container_name)
            self._initialized = True
            logger.info(
                "CosmosDBService initialized (db=%s, container=%s)",
                database_name,
                container_name,
            )
        except Exception as exc:
            logger.error("Failed to initialize CosmosDBService: %s", exc)
            self.container = None
            self._initialized = True

    # ----------------------------------------------------------
    def log_decision(self, record: dict) -> bool:
        """
        Write a decision audit record to Cosmos DB.
        'record' must include 'id' and 'session_id' (used as partition key).
        Returns True on success, False on failure.
        """
        if self.container is None:
            logger.warning("CosmosDB not available; skipping log")
            return False
        try:
            # Ensure required Cosmos fields are present
            record.setdefault("_ts_utc", datetime.now(timezone.utc).isoformat())
            self.container.upsert_item(record)
            logger.debug("Cosmos upsert OK: id=%s", record.get("id"))
            return True
        except Exception as exc:
            logger.error("CosmosDB log_decision error: %s", exc)
            return False

    # ----------------------------------------------------------
    def count_all_decisions(self) -> int:
        """Return the true total count of audit records via COUNT(1)."""
        if self.container is None:
            return 0
        try:
            results = list(
                self.container.query_items(
                    query="SELECT VALUE COUNT(1) FROM c WHERE IS_DEFINED(c.tier)",
                    enable_cross_partition_query=True,
                )
            )
            return results[0] if results else 0
        except Exception as exc:
            logger.error("CosmosDB count_all_decisions error: %s", exc)
            return 0

    # ----------------------------------------------------------
    def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        """
        Query the most recent audit records, ordered by timestamp descending.
        Returns an empty list on failure.
        """
        if self.container is None:
            return []
        try:
            items = list(
                self.container.query_items(
                    query=f"SELECT TOP {limit} * FROM c WHERE IS_DEFINED(c.tier) ORDER BY c._ts DESC",
                    enable_cross_partition_query=True,
                )
            )
            return items
        except Exception as exc:
            logger.error("CosmosDB get_recent_decisions error: %s", exc)
            return []

    # ----------------------------------------------------------
    def get_reputation(self, agent_id: str) -> dict | None:
        """
        Fetch the persisted reputation document for an agent.
        Returns None if not found or Cosmos is unavailable.
        """
        if self.container is None:
            return None
        try:
            item = self.container.read_item(
                item=f"rep_{agent_id}",
                partition_key="__reputation__",
            )
            return item
        except Exception:
            # NotFoundException or any other error → treat as not found
            return None

    # ----------------------------------------------------------
    def confirm_decision(self, record_id: str, session_id: str, justification: str = "") -> bool:
        """
        Mark an audit decision as human-confirmed.
        Tries a fast direct read first (needs correct partition key = session_id).
        Falls back to a cross-partition query if the session_id doesn't match
        (e.g. record was written by a different session or from the terminal).
        """
        if self.container is None:
            return False
        try:
            # Fast path: direct read when we have the right partition key
            record = None
            if session_id:
                try:
                    record = self.container.read_item(item=record_id, partition_key=session_id)
                except Exception:
                    record = None  # partition key mismatch → fall through

            # Fallback: cross-partition query by document id
            if record is None:
                results = list(self.container.query_items(
                    query="SELECT * FROM c WHERE c.id = @id",
                    parameters=[{"name": "@id", "value": record_id}],
                    enable_cross_partition_query=True,
                ))
                record = results[0] if results else None

            if record is None:
                logger.error("confirm_decision: record %s not found", record_id)
                return False

            record["intervention_confirmed"] = True
            record["intervention_timestamp"] = datetime.now(timezone.utc).isoformat()
            if justification:
                record["justification"] = justification.strip()
            self.container.upsert_item(record)
            logger.debug("Cosmos confirm_decision OK: id=%s", record_id)
            return True
        except Exception as exc:
            logger.error("CosmosDB confirm_decision error: %s", exc)
            return False

    # ----------------------------------------------------------
    def upsert_reputation(self, doc: dict) -> bool:
        """
        Write or update a reputation document.
        Returns True on success, False on failure.
        """
        if self.container is None:
            return False
        try:
            self.container.upsert_item(doc)
            return True
        except Exception as exc:
            logger.error("CosmosDB upsert_reputation error: %s", exc)
            return False

    # ----------------------------------------------------------
    def test_connection(self) -> dict:
        """Quick connectivity test — reads database properties."""
        if self.container is None:
            return {"service": "Cosmos DB", "status": "error", "detail": "not initialized"}
        try:
            props = self.database.read()
            return {"service": "Cosmos DB", "status": "connected", "database": props.get("id")}
        except Exception as exc:
            return {"service": "Cosmos DB", "status": "error", "detail": str(exc)}


# ═══════════════════════════════════════════════════════════════
# AI CONTENT SAFETY SERVICE
# ═══════════════════════════════════════════════════════════════

class ContentSafetyService:
    """
    Wrapper around Azure AI Content Safety.
    Screens text for hate, violence, sexual, and self-harm content.
    Falls back gracefully if the service is unavailable.
    """

    _instance: Optional["ContentSafetyService"] = None

    def __new__(cls) -> "ContentSafetyService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            from azure.ai.contentsafety import ContentSafetyClient  # type: ignore
            from azure.core.credentials import AzureKeyCredential  # type: ignore
            from azure.ai.contentsafety.models import AnalyzeTextOptions  # type: ignore

            self._AnalyzeTextOptions = AnalyzeTextOptions

            endpoint = os.environ.get("CONTENT_SAFETY_ENDPOINT", "")
            key = os.environ.get("CONTENT_SAFETY_KEY", "")
            if not endpoint or not key:
                raise ValueError("Content Safety credentials not set")

            self.client = ContentSafetyClient(endpoint, AzureKeyCredential(key))
            self._initialized = True
            logger.info("ContentSafetyService initialized")
        except Exception as exc:
            logger.warning("ContentSafetyService not available: %s", exc)
            self.client = None
            self._initialized = True

    # ----------------------------------------------------------
    def analyze(self, text: str) -> dict:
        """
        Analyze text for harmful content.
        Returns a dict with severity scores per category and a 'blocked' flag.
        Threshold: block if any category >= 4 (medium).
        """
        if self.client is None:
            return {"available": False, "blocked": False, "scores": {}}

        try:
            request = self._AnalyzeTextOptions(text=text[:5000])  # API limit
            response = self.client.analyze_text(request)

            scores = {}
            for category_result in (response.categories_analysis or []):
                scores[category_result.category] = category_result.severity

            # Block if any single category reaches severity >= 4
            blocked = any(v >= 4 for v in scores.values())
            return {"available": True, "blocked": blocked, "scores": scores}
        except Exception as exc:
            logger.error("ContentSafety analyze error: %s", exc)
            return {"available": False, "blocked": False, "scores": {}, "error": str(exc)}

    # ----------------------------------------------------------
    def test_connection(self) -> dict:
        """Quick connectivity test."""
        if self.client is None:
            return {"service": "Content Safety", "status": "unavailable"}
        result = self.analyze("Hello world")
        if "error" in result:
            return {"service": "Content Safety", "status": "error", "detail": result["error"]}
        return {"service": "Content Safety", "status": "connected", "test_scores": result["scores"]}


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE SINGLETONS (import these elsewhere)
# ═══════════════════════════════════════════════════════════════

def get_openai_service() -> AzureOpenAIService:
    return AzureOpenAIService()

def get_cosmos_service() -> CosmosDBService:
    return CosmosDBService()

def get_content_safety_service() -> ContentSafetyService:
    return ContentSafetyService()
