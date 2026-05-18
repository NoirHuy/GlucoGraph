"""
api_client.py — Reusable UMLS REST API client.

Handles:
  - API-key authentication (appended to every request)
  - Automatic pagination (pageNumber / pageSize)
  - Exponential back-off on 429 / 5xx
  - Transparent disk caching via DiskCache
"""

import time
from typing import Any, Generator, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from utils import DiskCache, get_logger, retry_sleep

logger = get_logger(__name__)


class UMLSApiError(Exception):
    """Raised when the UMLS API returns an unrecoverable error."""


class UMLSClient:
    """
    Low-level UMLS REST client.

    Usage
    -----
    client = UMLSClient(api_key="…")
    concept = client.get_concept("C0011849")
    relations = list(client.get_relations("C0011849"))
    """

    PAGE_SIZE = 25   # UMLS default max per page

    def __init__(
        self,
        api_key: str = config.UMLS_API_KEY,
        base_url: str = config.UMLS_BASE_URL,
        version: str = config.UMLS_VERSION,
        cache: Optional[DiskCache] = None,
    ):
        if not api_key:
            raise UMLSApiError(
                "UMLS_API_KEY is not set. "
                "Export it with: export UMLS_API_KEY=your_key_here"
            )
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._version = version
        self._cache = cache or DiskCache()
        self._session = self._build_session()

    # ──────────────────────────────────────────
    # Session / HTTP plumbing
    # ──────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=config.RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get(self, url: str, params: dict | None = None) -> Any:
        """
        Perform a single GET, with cache check, auth injection, and
        manual retry loop for 429s that slip past urllib3.
        """
        params = params or {}
        params["apiKey"] = self._key

        # Check cache first (excluding apiKey so we don't store the key)
        cache_params = {k: v for k, v in params.items() if k != "apiKey"}
        cached = self._cache.get(url, cache_params)
        if cached is not None:
            return cached

        for attempt in range(config.MAX_RETRIES):
            try:
                time.sleep(config.RATE_LIMIT_SLEEP)
                resp = self._session.get(url, params=params, timeout=config.REQUEST_TIMEOUT)

                if resp.status_code == 429:
                    retry_sleep(attempt)
                    continue

                if resp.status_code == 404:
                    logger.debug("404 Not Found: %s", url)
                    return None

                resp.raise_for_status()
                data = resp.json()
                self._cache.set(url, cache_params, data)
                return data

            except requests.exceptions.Timeout:
                logger.warning("Timeout on attempt %d for %s", attempt + 1, url)
                retry_sleep(attempt)
            except requests.exceptions.ConnectionError as exc:
                logger.warning("Connection error on attempt %d: %s", attempt + 1, exc)
                retry_sleep(attempt)
            except requests.exceptions.HTTPError as exc:
                logger.error("HTTP error: %s", exc)
                raise UMLSApiError(str(exc)) from exc

        raise UMLSApiError(f"Exhausted retries for {url}")

    # ──────────────────────────────────────────
    # Pagination helper
    # ──────────────────────────────────────────

    def _paginate(self, url: str, params: dict | None = None) -> Generator[dict, None, None]:
        """
        Auto-paginate a UMLS endpoint and yield every result item.
        UMLS paginates with ?pageNumber=N&pageSize=K.
        Stops when result.results is empty.
        """
        params = dict(params or {})
        params["pageSize"] = self.PAGE_SIZE
        page = 1

        while True:
            params["pageNumber"] = page
            data = self._get(url, params)

            if data is None:
                break

            result_node = data.get("result")
            if isinstance(result_node, list):
                results = result_node
            elif isinstance(result_node, dict):
                results = result_node.get("results") or result_node
            else:
                results = []

            # Some endpoints wrap in {"result": {...}} not a list
            if isinstance(results, dict):
                yield results
                break

            if not results:
                break

            for item in results:
                yield item

            # Stop if we got fewer items than a full page → last page
            if len(results) < self.PAGE_SIZE:
                break

            page += 1

    # ──────────────────────────────────────────
    # Public API methods
    # ──────────────────────────────────────────

    def search(self, query: str, search_type: str = "words") -> list[dict]:
        """Search UMLS by string. Returns list of concept dicts."""
        url = f"{self._base}/search/{self._version}"
        params = {"string": query, "searchType": search_type, "returnIdType": "concept"}
        results = list(self._paginate(url, params))
        logger.info("Search '%s' → %d results", query, len(results))
        return results

    def get_concept(self, cui: str) -> Optional[dict]:
        """Fetch basic concept metadata (name, semantic types, definition)."""
        url = f"{self._base}/content/{self._version}/CUI/{cui}"
        data = self._get(url)
        if data is None:
            logger.warning("Concept not found: %s", cui)
            return None
        result = data.get("result", data)
        logger.debug("Fetched concept: %s (%s)", result.get("name"), cui)
        return result

    def get_definitions(self, cui: str) -> list[dict]:
        """Fetch definitions for a concept."""
        url = f"{self._base}/content/{self._version}/CUI/{cui}/definitions"
        results = list(self._paginate(url))
        logger.debug("Fetched %d definitions for %s", len(results), cui)
        return results

    def get_atoms(self, cui: str, max_atoms: int = config.MAX_ATOMS_PER_CUI) -> list[dict]:
        """
        Fetch atoms (synonymous terms / source-asserted names) for a concept.
        Atoms are the source of synonym strings.
        """
        url = f"{self._base}/content/{self._version}/CUI/{cui}/atoms"
        atoms: list[dict] = []
        for atom in self._paginate(url):
            atoms.append(atom)
            if len(atoms) >= max_atoms:
                break
        logger.debug("Fetched %d atoms for %s", len(atoms), cui)
        return atoms

    def get_relations(self, cui: str, max_relations: int = config.MAX_RELATIONS_PER_CUI) -> list[dict]:
        """
        Fetch relationships for a concept.
        Each relation dict contains: relationLabel, relatedId, relatedIdName, etc.
        """
        url = f"{self._base}/content/{self._version}/CUI/{cui}/relations"
        relations: list[dict] = []
        for rel in self._paginate(url):
            relations.append(rel)
            if len(relations) >= max_relations:
                break
        logger.info("Fetched %d relations for %s", len(relations), cui)
        return relations

    def get_semantic_types(self, cui: str) -> list[str]:
        """Extract semantic type names from the concept record."""
        concept = self.get_concept(cui)
        if not concept:
            return []
        sem_types = concept.get("semanticTypes", [])
        return [st.get("name", "") for st in sem_types if st.get("name")]