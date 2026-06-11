from pathlib import Path
from dataclasses import dataclass, field
import re
import threading
from app.data.db import get_connection
from app.config import settings

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|copy|pragma|"
    r"read_csv|read_parquet|install|load|export)\b",
    re.IGNORECASE,
)

@dataclass
class QueryResult:
    sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    error: str | None = None

def _is_safe(sql: str) -> bool:
    s = sql.strip().rstrip(";")
    if ";" in s:                       # запрет нескольких стейтментов
        return False
    if not re.match(r"^\s*(select|with)\b", s, re.IGNORECASE):
        return False
    if _FORBIDDEN.search(s):
        return False
    return True

def run_query(sql: str, data_dir: Path | None = None, row_limit: int | None = None,
              timeout_sec: float | None = None) -> QueryResult:
    row_limit = row_limit or settings.sql_row_limit
    timeout_sec = timeout_sec or settings.sql_timeout_sec
    if not _is_safe(sql):
        return QueryResult(sql=sql, error="запрос отклонён: разрешён только один SELECT/WITH без DDL/DML")
    # курсор общего соединения: CSV уже материализованы при старте, парсинга нет;
    # cursor() — потокобезопасный способ конкурентного чтения в DuckDB
    cur = get_connection(data_dir=data_dir).cursor()
    timed_out = threading.Event()

    def _interrupt():
        timed_out.set()
        cur.interrupt()                # DuckDB прерывает текущий запрос

    timer = threading.Timer(timeout_sec, _interrupt)
    timer.start()
    try:
        res = cur.execute(sql)
        columns = [d[0] for d in res.description]
        fetched = res.fetchmany(row_limit + 1)
        truncated = len(fetched) > row_limit
        fetched = fetched[:row_limit]
        rows = [dict(zip(columns, r)) for r in fetched]
        return QueryResult(sql=sql, columns=columns, rows=rows,
                           row_count=len(rows), truncated=truncated)
    except Exception as e:  # любая SQL-ошибка — структурно, без краша
        if timed_out.is_set():
            return QueryResult(sql=sql, error=f"превышено время выполнения запроса ({timeout_sec} c) — упрости его или агрегируй сильнее")
        return QueryResult(sql=sql, error=str(e))
    finally:
        timer.cancel()
        cur.close()
