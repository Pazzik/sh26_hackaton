from app.data.db import get_connection, TABLES

def test_all_tables_registered(data_dir):
    con = get_connection(data_dir=data_dir)
    names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    for t in TABLES:
        assert t in names, f"таблица {t} не зарегистрирована"

def test_orders_has_rows(data_dir):
    con = get_connection(data_dir=data_dir)
    (n,) = con.execute("SELECT count(*) FROM orders").fetchone()
    assert n > 100_000

def test_connection_cached(data_dir):
    # CSV материализуются один раз: повторный вызов возвращает то же соединение
    assert get_connection(data_dir=data_dir) is get_connection(data_dir=data_dir)
