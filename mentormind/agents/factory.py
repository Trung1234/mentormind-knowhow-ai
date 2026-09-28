"""Wire the agents to the real spec 05 / spec 07 components (spec 06 FR-03).

Each component is looked up by module and factory name when a command runs. Until the owning spec
lands, the command stops with the exact module/factory it is waiting for.
"""

from __future__ import annotations

import importlib
from typing import Any

from mentormind.agents.rca import RcaAgent
from mentormind.agents.trace import TraceLog
from mentormind.agents.work_assistant import WorkAssistant
from mentormind.core.config import Settings
from mentormind.core.providers.llm import get_llm_provider
from mentormind.core.schemas import DataClassification

#: (module, factory taking Settings, owning spec) of every component the agents need.
RETRIEVER = ("mentormind.knowledge_base.retrieval.hybrid", "get_retriever", "spec 05 (Trung)")
GRAPH = ("mentormind.knowledge_base.kg.templates", "get_graph_templates", "spec 05 (Trung)")
SIGMA = ("mentormind.knowledge_base.sigma.adapter", "get_sigma_adapter", "spec 07 (Vinh)")


class AgentWiringError(RuntimeError):
    """A component the agent needs does not exist yet."""


def build_work_assistant(settings: Settings) -> WorkAssistant:
    graph = _component(GRAPH, settings)
    return WorkAssistant(
        _component(RETRIEVER, settings),
        get_llm_provider(settings),
        experts=graph if hasattr(graph, "top_contributor") else None,
        min_score=settings.assist_min_score,
        trace=TraceLog(settings.trace_dir),
    )


def build_rca_agent(settings: Settings) -> RcaAgent:
    # The CSV adapter reads the synthetic mock of spec 07 §3; any real Sigma is factory data.
    mock = settings.sigma_adapter == "csv"
    return RcaAgent(
        get_llm_provider(settings),
        _component(GRAPH, settings),
        _component(RETRIEVER, settings),
        _component(SIGMA, settings),
        sigma_classification=(
            DataClassification.SYNTHETIC if mock else DataClassification.FACTORY_CONFIDENTIAL
        ),
        trace=TraceLog(settings.trace_dir),
    )


def _component(where: tuple[str, str, str], settings: Settings) -> Any:
    module_name, factory, owner = where
    try:
        module = importlib.import_module(module_name)
        build = getattr(module, factory)
    except (ImportError, AttributeError) as exc:
        raise AgentWiringError(
            f"Chưa có {module_name}.{factory}(settings) — phần của {owner}."
        ) from exc
    return build(settings)
