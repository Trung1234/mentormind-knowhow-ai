"""Settings read from ``KNOWHOW_*`` environment variables (spec 01 FR-03).

Sources, later wins: ``.env`` at the repo root (gitignored; ``.env.example`` is the template),
then the real process environment. ``.env`` holds the vendor API keys too — ``.secrets/README.md``
is only the guide for obtaining them. Every module reads configuration through
:func:`get_settings` — never ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
#: The one dotenv file: ``KNOWHOW_*`` settings and the vendor API keys live side by side.
ENV_FILE = REPO_ROOT / ".env"

JsonMode = Literal["auto", "json_schema", "json_object", "off"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWHOW_",
        env_file=(ENV_FILE,),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Knowledge base (spec 01 §4, spec 05) ---------------------------------------------
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("change-me")
    vector_backend: Literal["pgvector", "memory"] = "pgvector"
    pg_dsn: str = "postgresql://knowhow:change-me@localhost:5432/knowhow"
    vector_table: str = "knowhow_chunks"
    embed_dim: int = 1024
    embed_model: str = "BAAI/bge-m3"
    # "hashing" is a no-model stand-in for dev; it must not fill a table that bge-m3 will later use.
    embedder: Literal["bge-m3", "hashing"] = "bge-m3"

    # --- Document ingest (spec 02) ----------------------------------------------------------
    process_id_regex: str = r"\b[A-Z]{3,5}\d{2}\b"
    # Default matches DENSO-style numbers (AA123456-7890); confirm against the samples (spec 02b §4.4).
    part_number_regex: str = r"\b[A-Z]{2}\d{6}-\d{4}\b"
    # Matches of process_id_regex that are not processes (ISO27, REV01...).
    process_id_stoplist: list[str] = []
    # Command of the mmore install used as the degraded PDF fallback (not a project extra).
    mmore_bin: str = "mmore"
    # bge-m3 matches the embedder; "whitespace" is for offline runs and undercounts CJK.
    token_counter: Literal["bge-m3", "whitespace"] = "bge-m3"
    chunk_min_tokens: int = 300
    chunk_max_tokens: int = 800
    chunk_overlap_tokens: int = 50
    # Share of IPA/Greek letters above which a page's text layer is reported as mis-encoded (FR-02b).
    text_quality_max_odd_ratio: float = 0.05

    # --- VLM (spec 04) ----------------------------------------------------------------------
    # Registry name of the provider (``knowhow vlm providers`` lists them).
    vlm_provider: str = "local_openai"
    # Empty = the provider's default endpoint / default Qwen3-VL-8B model id.
    vlm_base_url: str | None = None
    vlm_model: str | None = None
    # Empty = the provider's own key variable (e.g. OPENROUTER_API_KEY in .env).
    vlm_api_key: SecretStr | None = None
    vlm_fps: float = 4.0
    vlm_max_frames: int = 48
    vlm_timeout_s: float = 90.0  # FR-07
    vlm_max_retries: int = 3  # FR-07
    vlm_json_mode: JsonMode = "auto"
    vlm_max_tokens: int = 2048
    # JSON merged into every request body: vendor sampling knobs (e.g. {"presence_penalty": 1.5},
    # which stops Qwen3-VL from looping step lists — see 3rdparty/vlm_server/README.md).
    vlm_extra_body: dict[str, Any] = {}

    # --- LLM (spec 06; also spec 04 pass C / propose-reasons) ---------------------------------
    llm_provider: str = "qwen_api"
    # Empty = the provider's default (qwen_api: qwen-plus, local_openai: the Qwen3-VL server).
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    llm_timeout_s: float = 90.0
    llm_max_retries: int = 3
    llm_json_mode: JsonMode = "auto"
    llm_max_tokens: int = 1024
    llm_extra_body: dict[str, Any] = {}

    # --- Outbound guard for cloud calls (spec 01 FR-09b, spec 04 FR-02c) ---------------------
    # Mask PII in text sent to cloud providers. False = refuse instead (LeakGuard always runs).
    guard_mask_text: bool = True
    # Pixelate faces in frames sent to cloud VLMs (YuNet model fetched once, SHA-256 pinned).
    guard_blur_faces: bool = True
    guard_face_model: Path = REPO_ROOT / "data" / "work" / "models" / "face_detection_yunet_2023mar.onnx"
    # One JSON line per cloud call, counts only. Empty = no audit log.
    guard_audit_dir: Path | None = REPO_ROOT / "data" / "work" / "audit"
    # Site-specific codes to mask, entity -> regex, e.g. {"EQUIPMENT": "SIGMA-EQ-\\d+"}.
    guard_extra_patterns: dict[str, str] = {}

    # --- REST API (spec 08) -----------------------------------------------------------------
    app_name: str = "MentorMind Know-How API"
    # Spec 08 FR-05: only the UI's origin (Vite dev server by default).
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Stores & adapters (spec 07, 08) ----------------------------------------------------
    profile_db: Path = Path("data/work/profiles.sqlite")
    # Where `vlm describe` keeps drafts: auto = spec 08 store if present, else JSON file.
    profile_sink: Literal["auto", "store", "file"] = "auto"
    sigma_adapter: str = "csv"
    sigma_csv_dir: Path = Path("data/mock_sigma")
    work_dir: Path = Path("data/work")
    samples_dir: Path = Path("data/samples")

    # Where provider-specific API keys are looked up after the process environment.
    secrets_file: Path = ENV_FILE


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings (cached; tests build ``Settings`` directly)."""
    return Settings()
