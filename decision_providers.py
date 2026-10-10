"""Standard-library clients for the router's selectable decision makers."""
from __future__ import annotations

import json
import http.client
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

DEFAULT_MODELS = {"jev": "jev-latest", "perplexity": "pplx-decider-v1.1-27b"}
ENDPOINTS = {"jev": "https://api.typesafe.ai/v1/systemone",
             "perplexity": "https://api.perplexity.ai/v1/decisions"}
MODEL_ENV = {"jev": "JEV_MODEL", "perplexity": "PERPLEXITY_DECISION_MODEL"}
KEY_ENV = {"jev": "TYPESAFE_API_KEY", "perplexity": "PERPLEXITY_API_KEY"}
KEY_FILE = Path.home() / ".config" / "jev-loop" / "typesafe_api_key"
MAX_QUESTIONS = 128
MAX_RETRY_DELAY = 30.0
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
REQUEST_ID = re.compile(r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")


class ProviderError(RuntimeError):
    """A sanitized provider failure; never includes a prompt or response body."""


def provider_key(provider: str) -> str:
    if provider not in KEY_ENV:
        raise ProviderError("Unknown decision provider.")
    key = os.environ.get(KEY_ENV[provider], "").strip()
    if not key and provider == "jev":
        try:
            if KEY_FILE.exists():
                key = KEY_FILE.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            raise ProviderError("Cannot read the Jev key file.") from None
    if not key:
        hint = f" or use {KEY_FILE}" if provider == "jev" else ""
        raise ProviderError(f"Missing {provider} key: set {KEY_ENV[provider]}{hint}.")
    if "\r" in key or "\n" in key:
        raise ProviderError(f"Invalid {provider} key format.")
    return key


def resolve_model(provider: str, override: str | None = None) -> str:
    if provider not in DEFAULT_MODELS:
        raise ProviderError("Unknown decision provider.")
    model = override if override is not None else os.environ.get(MODEL_ENV[provider], DEFAULT_MODELS[provider])
    if not isinstance(model, str) or not model.strip() or len(model) > 200 or any(ord(c) < 32 for c in model):
        raise ProviderError(f"Invalid {provider} model setting.")
    return model.strip()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A provider must not forward this request's bearer credential elsewhere.
        return None


def _open(request, *, timeout):
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


def _request_id(headers) -> str | None:
    value = headers.get("x-request-id", "") if headers is not None else ""
    return value if isinstance(value, str) and REQUEST_ID.fullmatch(value) else None


def _retry_delay(headers, attempt: int) -> float:
    value = headers.get("Retry-After") if headers is not None else None
    if value is not None:
        try:
            seconds = float(value)
            if math.isfinite(seconds) and seconds >= 0:
                return seconds
        except (TypeError, ValueError):
            pass
    return min(0.5 * 2 ** attempt, 4.0)


def decision_call(provider: str, state: dict, questions: dict, retries: int = 3,
                  model: str | None = None) -> dict:
    """Call one provider, failing permanent errors without retrying paid requests.

    Perplexity contract: https://docs.perplexity.ai/docs/decisions/quickstart
    Jev contract: https://docs.typesafe.ai/api
    """
    selected = resolve_model(provider, model)
    key = provider_key(provider)
    if not isinstance(questions, dict) or not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ProviderError(f"A provider request needs 1 to {MAX_QUESTIONS} questions.")
    if not isinstance(retries, int) or isinstance(retries, bool) or not 0 <= retries <= 3:
        raise ProviderError("Retries must be an integer from 0 to 3.")
    try:
        body = json.dumps({"model": selected, "state": state, "questions": questions},
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise ProviderError("The decision request must contain finite JSON data.") from None
    if len(body) > 32 * 1024 * 1024:
        raise ProviderError("The decision request exceeds 32 MiB.")
    request = urllib.request.Request(ENDPOINTS[provider], data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    timeout = 30 if provider == "perplexity" else 180
    for attempt in range(retries + 1):
        try:
            with _open(request, timeout=timeout) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                request_id = _request_id(getattr(response, "headers", None))
        except urllib.error.HTTPError as error:
            request_id = _request_id(error.headers)
            suffix = f"; request ID {request_id}" if request_id else ""
            message = f"{provider} request failed (HTTP {error.code}{suffix})."
            delay = _retry_delay(error.headers, attempt)
            error.close()
            if error.code != 429 and not 500 <= error.code <= 599:
                raise ProviderError(message) from None
            if attempt == retries or delay > MAX_RETRY_DELAY:
                raise ProviderError(message + " Retry later.") from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
            if attempt == retries:
                raise ProviderError(f"{provider} request failed (network or timeout).") from None
            delay = _retry_delay(None, attempt)
        else:
            # Parsing and contract failures must not retry an already billed response.
            if len(payload) > MAX_RESPONSE_BYTES:
                raise ProviderError(f"{provider} response exceeds the size limit.")
            try:
                result = json.loads(payload)
            except (ValueError, UnicodeError, RecursionError):
                raise ProviderError(f"{provider} returned invalid JSON.") from None
            if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
                raise ProviderError(f"{provider} returned an invalid answers envelope.")
            result.pop("_request_id", None)
            if request_id:
                result["_request_id"] = request_id
            return result
        time.sleep(delay)
    raise ProviderError(f"{provider} request failed.")
