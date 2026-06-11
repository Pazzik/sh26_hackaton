from app.memory.sessions import SessionStore

def test_append_and_get():
    store = SessionStore(ttl_sec=1000, now=lambda: 100.0)
    store.append("s1", "user", "вопрос 1")
    store.append("s1", "assistant", "ответ 1")
    hist = store.get("s1")
    assert len(hist) == 2
    assert hist[0]["content"] == "вопрос 1"

def test_ttl_expiry():
    t = {"v": 100.0}
    store = SessionStore(ttl_sec=10, now=lambda: t["v"])
    store.append("s1", "user", "x")
    t["v"] = 200.0  # прошло больше ttl
    assert store.get("s1") == []

def test_unknown_session_empty():
    store = SessionStore(ttl_sec=10, now=lambda: 0.0)
    assert store.get("nope") == []
