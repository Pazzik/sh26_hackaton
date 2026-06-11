from typing import Literal
from pydantic import BaseModel

# ambiguous — вопрос понят, но допускает несколько толкований: полный путь,
# выбранное толкование обязано попасть в assumptions; отказ — только для trap
QuestionKind = Literal["simple", "analytical", "ambiguous", "trap", "chitchat"]

class RouterDecision(BaseModel):
    kind: QuestionKind
    needs_chart: bool = False
    rationale: str = ""

class ExtractionResult(BaseModel):
    sql: str = ""
    columns: list[str] = []
    rows: list[dict] = []
    row_count: int = 0
    truncated: bool = False
    insufficient: bool = False
    note: str | None = None

class AnalysisResult(BaseModel):
    findings: list[str] = []
    numbers: dict[str, float] = {}
    assumptions: list[str] = []
    caveats: list[str] = []

class CritiqueVerdict(BaseModel):
    approved: bool = True
    issues: list[str] = []
    must_retry: bool = False
    # extractor — если неверен сам срез/SQL: повтор analyst на том же датасете бесполезен
    retry_target: Literal["analyst", "extractor"] = "analyst"

class ChartSpec(BaseModel):
    type: Literal["line", "bar", "grouped_bar", "area", "scatter", "none"] = "none"
    x: str = ""
    y: str = ""
    series: str | None = None
    reason: str = ""

class TraceStep(BaseModel):
    agent: str
    summary: str
    sql: str | None = None
    rows: int | None = None
    verdict: str | None = None
    elapsed_ms: int = 0

class PipelineState(BaseModel):
    message: str
    session_id: str | None = None
    history: list[dict] = []
    route: RouterDecision | None = None
    extraction: ExtractionResult | None = None
    analysis: AnalysisResult | None = None
    critique: CritiqueVerdict | None = None
    chart: ChartSpec | None = None
    trace: list[TraceStep] = []
    retries_used: int = 0
    deadline_ts: float = 0.0
