"""Thin OpenRouter client (OpenAI-compatible) with friendly error mapping.

Every failure is raised as `AIServiceError` with a user-readable message and a
machine-readable `kind`. Nothing here ever fabricates a response.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import FALLBACK_FREE_MODELS, OPENROUTER_BASE_URL, REQUEST_TIMEOUT_SECONDS


class AIServiceError(Exception):
    """Raised for every API failure. `kind` is one of:
    missing_key, invalid_key, rate_limit, network, model_unavailable,
    invalid_json, bad_request, unknown."""

    def __init__(self, kind: str, message: str, detail: str = ""):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.detail = detail


@dataclass
class AIResponse:
    text: str          # raw, unedited model output
    model: str         # model that actually answered (OpenRouter may route)
    usage: dict


ERROR_HELP = {
    "missing_key": "No OpenRouter API key found. Add OPENROUTER_API_KEY to your .env file "
                   "or Streamlit secrets, or paste a key in Settings. You can also switch on "
                   "Demo mode in Settings.",
    "invalid_key": "OpenRouter rejected the API key (401/403). Check the key in Settings or .env.",
    "rate_limit": "Rate limit reached (429). Free models have tight limits – wait a minute and "
                  "retry, or choose another model in Settings.",
    "network": "Could not reach OpenRouter. Check your internet connection and try again.",
    "model_unavailable": "The selected model is unavailable or does not exist. Choose another "
                         "model in Settings.",
    "invalid_json": "The model returned a response that could not be read as valid structured "
                    "data, even after a retry. Try again or choose a stronger model.",
    "bad_request": "OpenRouter rejected the request (400). The model may not support this input.",
    "unknown": "Unexpected error while contacting the AI service.",
}


class OpenRouterClient:
    def __init__(self, api_key: str | None, model: str):
        if not api_key:
            raise AIServiceError("missing_key", ERROR_HELP["missing_key"])
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise AIServiceError("unknown", "The 'openai' package is not installed. "
                                            "Run: pip install -r requirements.txt") from exc
        self.model = model
        self._client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
            default_headers={
                # Optional OpenRouter attribution headers
                "HTTP-Referer": "https://localhost/nyayamate",
                "X-Title": "NyayaMate AI",
            },
        )

    def complete(self, system: str, messages: list[dict], *, temperature: float = 0.2,
                 json_mode: bool = False, max_tokens: int = 1800) -> AIResponse:
        import openai

        payload = [{"role": "system", "content": system}] + messages
        kwargs = dict(model=self.model, messages=payload, temperature=temperature,
                      max_tokens=max_tokens)
        if json_mode:
            # Not every free model supports response_format; we retry without it.
            kwargs["response_format"] = {"type": "json_object"}
        if self.model.endswith(":free"):
            # OpenRouter model fallbacks: if the chosen free model is busy/down, try the next.
            fallbacks = [m for m in FALLBACK_FREE_MODELS if m != self.model]
            kwargs["extra_body"] = {"models": [self.model] + fallbacks}
        try:
            try:
                resp = self._client.chat.completions.create(**kwargs)
            except openai.BadRequestError:
                # Drop optional features (JSON mode, fallback list) and try once more.
                if not (json_mode or "extra_body" in kwargs):
                    raise
                kwargs.pop("response_format", None)
                kwargs.pop("extra_body", None)
                resp = self._client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as e:
            raise AIServiceError("invalid_key", ERROR_HELP["invalid_key"], str(e)) from e
        except openai.PermissionDeniedError as e:
            raise AIServiceError("invalid_key", ERROR_HELP["invalid_key"], str(e)) from e
        except openai.RateLimitError as e:
            raise AIServiceError("rate_limit", ERROR_HELP["rate_limit"], str(e)) from e
        except openai.NotFoundError as e:
            raise AIServiceError("model_unavailable", ERROR_HELP["model_unavailable"], str(e)) from e
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            raise AIServiceError("network", ERROR_HELP["network"], str(e)) from e
        except openai.BadRequestError as e:
            raise AIServiceError("bad_request", ERROR_HELP["bad_request"], str(e)) from e
        except openai.APIStatusError as e:
            kind = "model_unavailable" if e.status_code in (502, 503) else "unknown"
            raise AIServiceError(kind, ERROR_HELP[kind], f"HTTP {e.status_code}: {e}") from e
        except Exception as e:  # noqa: BLE001
            raise AIServiceError("unknown", ERROR_HELP["unknown"], repr(e)) from e

        text = self._text_of(resp)
        if not text.strip():
            # Common with openrouter/free: a reasoning model spends the whole token budget on
            # hidden "thinking" and returns empty content, or the model ignores JSON mode.
            # Retry once: no response_format, bigger budget. Still empty -> real error.
            kwargs.pop("response_format", None)
            kwargs["max_tokens"] = max(4000, max_tokens * 3)
            try:
                resp = self._client.chat.completions.create(**kwargs)
                text = self._text_of(resp)
            except openai.RateLimitError as e:
                raise AIServiceError("rate_limit", ERROR_HELP["rate_limit"], str(e)) from e
            except Exception as e:  # noqa: BLE001
                raise AIServiceError("model_unavailable", ERROR_HELP["model_unavailable"],
                                     repr(e)) from e
        if not text.strip():
            raise AIServiceError("model_unavailable",
                                 "The model returned an empty response twice. Free models on "
                                 "openrouter/free change often – pick a specific model in "
                                 "Settings and click Test connection.",
                                 f"routed model: {getattr(resp, 'model', '?')}")
        usage = resp.usage.model_dump() if getattr(resp, "usage", None) else {}
        return AIResponse(text=text, model=getattr(resp, "model", self.model) or self.model,
                          usage=usage)

    @staticmethod
    def _text_of(resp) -> str:
        """Content of the first choice; '' if OpenRouter returned no choices / an error body."""
        if not getattr(resp, "choices", None):
            return ""
        return resp.choices[0].message.content or ""
