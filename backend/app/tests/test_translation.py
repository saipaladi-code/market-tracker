import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_translation_languages():
    response = client.get("/api/translate/languages")
    assert response.status_code == 200
    langs = response.json()
    assert "en" in langs
    assert "te" in langs
    assert "hi" in langs
    assert "ta" in langs
    assert "kn" in langs
    assert "mr" in langs
    assert "ur" in langs
    assert "ar" in langs
    assert "es" in langs
    assert "zh-CN" in langs
    assert langs["ur"]["dir"] == "rtl"
    assert langs["ar"]["dir"] == "rtl"
    assert langs["te"]["native"] == "తెలుగు"
    assert langs["hi"]["native"] == "हिन्दी"

def test_translate_english_passthrough():
    response = client.post("/api/translate", json={"text": "Gold market trends", "target_lang": "en"})
    assert response.status_code == 200
    data = response.json()
    assert data["translated_text"] == "Gold market trends"
    assert data["status"] == "success"

def test_translate_telugu_and_hindi():
    # Telugu
    res_te = client.post("/api/translate", json={"text": "Gold prices rise", "target_lang": "te"})
    assert res_te.status_code == 200
    data_te = res_te.json()
    assert len(data_te["translated_text"]) > 0

    # Hindi
    res_hi = client.post("/api/translate", json={"text": "Silver demand increases", "target_lang": "hi"})
    assert res_hi.status_code == 200
    data_hi = res_hi.json()
    assert len(data_hi["translated_text"]) > 0

def test_translate_caching():
    payload = {"text": "Central bank gold purchases hit record highs", "target_lang": "te"}
    res1 = client.post("/api/translate", json=payload)
    assert res1.status_code == 200

    # Second call should be served from cache
    res2 = client.post("/api/translate", json=payload)
    assert res2.status_code == 200
    assert res2.json()["cached"] is True
