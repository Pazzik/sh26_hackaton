import pytest
from app.api.parsing import extract_question, BadRequest

def test_message_field():
    assert extract_question({"message": "привет"}) == "привет"

def test_query_field():
    assert extract_question({"query": "вопрос"}) == "вопрос"

def test_messages_list():
    body = {"messages": [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]}
    assert extract_question(body) == "b"

def test_empty_body_raises_400():
    with pytest.raises(BadRequest) as e:
        extract_question({})
    assert e.value.status == 400

def test_non_string_raises_422():
    with pytest.raises(BadRequest) as e:
        extract_question({"message": 123})
    assert e.value.status == 422

def test_blank_string_raises_400():
    with pytest.raises(BadRequest) as e:
        extract_question({"message": "   "})
    assert e.value.status == 400

def test_oversize_truncated():
    big = "a" * 20000
    out = extract_question({"message": big})
    assert len(out) <= 8000
