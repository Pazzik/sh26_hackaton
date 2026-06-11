from app.data.executor import run_query, QueryResult

def test_select_ok(data_dir):
    res = run_query("SELECT category, COUNT(*) n FROM product_lines GROUP BY 1", data_dir=data_dir)
    assert isinstance(res, QueryResult)
    assert res.error is None
    assert res.row_count >= 1
    assert "category" in res.columns

def test_ddl_blocked(data_dir):
    res = run_query("DROP VIEW orders", data_dir=data_dir)
    assert res.error is not None
    assert res.rows == []

def test_limit_applied(data_dir):
    res = run_query("SELECT * FROM orders", data_dir=data_dir, row_limit=10)
    assert res.row_count == 10
    assert res.truncated is True

def test_sql_error_is_structured(data_dir):
    res = run_query("SELECT nonexistent_col FROM orders", data_dir=data_dir)
    assert res.error is not None and res.rows == []

def test_timeout_interrupts_heavy_query(data_dir):
    # cross join orders×orders не должен съесть дедлайн всего запроса
    res = run_query("SELECT COUNT(*) FROM orders o1, orders o2",
                    data_dir=data_dir, timeout_sec=0.5)
    assert res.error is not None and "время" in res.error.lower()
