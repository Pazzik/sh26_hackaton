from pathlib import Path
import threading
import duckdb

TABLES = [
    "financials_monthly", "unit_economics_monthly", "customers", "orders",
    "product_lines", "nps_responses", "customer_activity_monthly", "churn_reasons",
]

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "meridian_dwh"

# одно соединение на data_dir: CSV парсятся ОДИН РАЗ при старте (orders ≈ 680k строк),
# дальше все запросы работают с in-memory таблицами через con.cursor()
_connections: dict[Path, duckdb.DuckDBPyConnection] = {}
_lock = threading.Lock()

def _materialize_csvs(con, data_dir: Path) -> None:
    for t in TABLES:
        csv = data_dir / f"{t}.csv"
        con.execute(
            f"CREATE OR REPLACE TABLE {t} AS "
            f"SELECT * FROM read_csv_auto('{csv.as_posix()}', header=true)"
        )

def _apply_views(con) -> None:
    ddl = (Path(__file__).parent / "views.sql").read_text(encoding="utf-8")
    con.execute(ddl)

def get_connection(data_dir: Path | None = None):
    """Общее in-memory соединение с материализованными CSV и вьюхами (кэш по data_dir).

    Защита от DDL/DML пользовательских запросов — статический фильтр в executor;
    конкурентные запросы берут con.cursor() (потокобезопасно в DuckDB)."""
    data_dir = (data_dir or DEFAULT_DATA_DIR).resolve()
    with _lock:
        if data_dir not in _connections:
            con = duckdb.connect(database=":memory:")
            _materialize_csvs(con, data_dir)
            _apply_views(con)
            _connections[data_dir] = con
        return _connections[data_dir]
