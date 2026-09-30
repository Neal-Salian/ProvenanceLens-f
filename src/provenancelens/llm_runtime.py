"""Local / open-weight chat model availability and configuration.

Policy:

* No paid inference API is ever required or referenced.
* Ollama is the primary supported runtime, but the extractor only needs a
  LangChain ``BaseChatModel``, so another local runtime can be plugged in
  without touching extraction logic.
* **Nothing is ever pulled.** Availability is probed with a read-only HTTP
  ``/api/tags`` call, and an unavailability report is produced instead of an
  exception when the runtime is missing.
* The default model is a small, CPU-friendly recommendation; the context
  window is bounded so a laptop stays fast.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict

__all__ = [
    "LLMUnavailable",
    "DEFAULT_LLM_MODEL",
    "DEFAULT_LLM_BASE_URL",
    "DEFAULT_LLM_NUM_CTX",
    "LLMAvailability",
    "configured_model",
    "configured_base_url",
    "configured_num_ctx",
    "llm_availability",
    "build_default_chat_model",
    "IMPORT_HINT",
]

#: Small instruct model: ~2 GB, comfortable on an 8 GB M2 Mac.
DEFAULT_LLM_MODEL = "llama3.2:3b"
DEFAULT_LLM_BASE_URL = "http://localhost:11434"
#: Bounded context: enough for one prose chunk, cheap to run.
DEFAULT_LLM_NUM_CTX = 4096

ENV_MODEL = "PROVENANCELENS_LLM_MODEL"
ENV_BASE_URL = "PROVENANCELENS_LLM_BASE_URL"
ENV_NUM_CTX = "PROVENANCELENS_LLM_NUM_CTX"

IMPORT_HINT = (
    "install the optional dependency with: "
    "pip install 'provenancelens[llm]'"
)


class LLMUnavailable(RuntimeError):
    """The configured local chat model cannot be used (dependency or runtime)."""


class LLMAvailability(BaseModel):
    """Result of probing the local runtime (never raises)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    model: str
    reason: str | None = None
    installed_models: tuple[str, ...] = ()
    dependency_available: bool = True
    runtime_reachable: bool = False

    def describe(self) -> str:
        if self.available:
            return f"local model '{self.model}' is available"
        return f"LLM unavailable ({self.model}): {self.reason}"


def configured_model() -> str:
    return os.environ.get(ENV_MODEL) or DEFAULT_LLM_MODEL


def configured_base_url() -> str:
    return os.environ.get(ENV_BASE_URL) or DEFAULT_LLM_BASE_URL


def configured_num_ctx() -> int:
    raw = os.environ.get(ENV_NUM_CTX)
    if not raw:
        return DEFAULT_LLM_NUM_CTX
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LLM_NUM_CTX
    return value if value > 0 else DEFAULT_LLM_NUM_CTX


def _installed_models(base_url: str, timeout: float) -> tuple[list[str], str | None]:
    """Read-only probe of the Ollama runtime. Never pulls anything."""
    import httpx

    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
    except Exception as exc:  # connection refused, DNS, timeout, ...
        return [], f"cannot reach the Ollama runtime at {base_url} ({type(exc).__name__})"
    if response.status_code != 200:
        return [], f"Ollama runtime returned HTTP {response.status_code}"
    try:
        payload = response.json()
    except Exception:
        return [], "Ollama runtime returned a non-JSON response"
    models = [
        str(entry.get("name", ""))
        for entry in payload.get("models", [])
        if isinstance(entry, dict)
    ]
    return [name for name in models if name], None


def llm_availability(
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 2.0,
    require_dependency: bool = True,
) -> LLMAvailability:
    """Probe whether the configured local model can be used right now."""
    model = model or configured_model()
    base_url = base_url or configured_base_url()

    if require_dependency:
        try:
            import langchain_ollama  # noqa: F401
        except ImportError:
            return LLMAvailability(
                available=False,
                model=model,
                reason=f"langchain-ollama is not installed; {IMPORT_HINT}",
                dependency_available=False,
            )

    models, error = _installed_models(base_url, timeout)
    if error is not None:
        return LLMAvailability(
            available=False, model=model, reason=error, runtime_reachable=False
        )

    def _matches(name: str) -> bool:
        return name == model or name.split(":")[0] == model.split(":")[0]

    if not any(_matches(name) for name in models):
        return LLMAvailability(
            available=False,
            model=model,
            reason=(
                f"model '{model}' is not installed locally; install it manually "
                f"with: ollama pull {model} (ProvenanceLens never downloads models)"
            ),
            installed_models=tuple(models),
            runtime_reachable=True,
        )
    return LLMAvailability(
        available=True,
        model=model,
        installed_models=tuple(models),
        runtime_reachable=True,
    )


def build_default_chat_model(
    *,
    model: str | None = None,
    base_url: str | None = None,
    num_ctx: int | None = None,
    temperature: float = 0.0,
) -> Any:
    """Build the default local chat model, or raise :class:`LLMUnavailable`."""
    model = model or configured_model()
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise LLMUnavailable(
            f"langchain-ollama is not installed; {IMPORT_HINT}"
        ) from exc

    return ChatOllama(
        model=model,
        base_url=base_url or configured_base_url(),
        temperature=temperature,
        num_ctx=num_ctx or configured_num_ctx(),
    )
