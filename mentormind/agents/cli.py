"""``knowhow agent ask`` and ``knowhow agent rca`` (spec 06 FR-03)."""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(help="Work Assistant và RCA Agent (spec 06).", no_args_is_help=True)


@app.command("ask", help="Hỏi trợ lý về một bước thao tác; trả lời có trích nguồn hoặc từ chối.")
def ask_cmd(
    question: Annotated[str, typer.Argument(help="Câu hỏi.")],
    process: Annotated[str | None, typer.Option("--process", help="Mã công đoạn.")] = None,
) -> None:
    from mentormind.agents.factory import AgentWiringError, build_work_assistant
    from mentormind.core.config import get_settings
    from mentormind.core.guard import ConfidentialDataError
    from mentormind.core.providers.errors import ProviderError
    from mentormind.core.schemas import AskRequest

    try:
        answer = build_work_assistant(get_settings()).ask(
            AskRequest(question=question, process_id=process)
        )
    except (AgentWiringError, ProviderError, ConfidentialDataError) as exc:
        typer.secho(f"Lỗi: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.echo(answer.answer)
    if answer.refused:
        if answer.suggested_contact:
            typer.echo(f"Hỏi chuyên gia: {answer.suggested_contact}")
        return
    for i, c in enumerate(answer.citations, start=1):
        typer.echo(f"[{i}] {c.source_type} {c.ref_id}: {c.snippet}")
    typer.echo(f"độ tin cậy: {answer.confidence:.2f}")


@app.command("rca", help="Truy nguyên nhân lỗi theo lot (Sigma) hoặc triệu chứng; in báo cáo JSON.")
def rca_cmd(
    lot: Annotated[str | None, typer.Option("--lot", help="Mã lot trong Sigma.")] = None,
    symptom: Annotated[str | None, typer.Option("--symptom", help="Mô tả triệu chứng.")] = None,
    process: Annotated[str | None, typer.Option("--process", help="Mã công đoạn.")] = None,
) -> None:
    from pydantic import ValidationError

    from mentormind.agents.factory import AgentWiringError, build_rca_agent
    from mentormind.core.config import get_settings
    from mentormind.core.guard import ConfidentialDataError
    from mentormind.core.providers.errors import ProviderError
    from mentormind.core.schemas import LotNotFound, RcaRequest

    try:
        request = RcaRequest(lot_id=lot, symptom_text=symptom, process_id=process)
        report = build_rca_agent(get_settings()).investigate(request)
    except ValidationError as exc:
        typer.secho("Lỗi: cần --lot hoặc --symptom.", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except (AgentWiringError, LotNotFound, ProviderError, ConfidentialDataError) as exc:
        typer.secho(f"Lỗi: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.echo(report.model_dump_json(indent=2))
