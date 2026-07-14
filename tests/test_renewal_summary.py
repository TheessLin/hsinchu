from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.renewal_summary import build_decision_summary_input, get_decision_summary_provider
from app.simulation import generate_and_store_simulation


client = TestClient(app)


REQUIRED_SUMMARY_FIELDS = {
    "scenario_id",
    "executive_summary",
    "main_benefits",
    "main_risks",
    "tradeoffs",
    "recommended_actions",
    "uncertain_items",
    "data_disclaimer",
}


def test_r01_scenario_summary_api_returns_structured_rule_based_summary() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/scenarios/B/summary")

    assert response.status_code == 200
    payload = response.json()
    assert REQUIRED_SUMMARY_FIELDS.issubset(payload)
    assert payload["scenario_id"] == "B"
    assert "依本POC模擬結果" in payload["executive_summary"]
    assert "不宣稱" in payload["executive_summary"]
    assert len(payload["main_benefits"]) > 0
    assert len(payload["main_risks"]) > 0
    assert len(payload["tradeoffs"]) > 0
    assert len(payload["uncertain_items"]) > 0


def test_r01_summary_recommended_actions_reference_calculated_kpis() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/B/summary").json()

    assert len(payload["recommended_actions"]) > 0
    for action in payload["recommended_actions"]:
        assert action["evidence_kpi_ids"]
        assert all(isinstance(kpi_id, str) and kpi_id for kpi_id in action["evidence_kpi_ids"])


def test_r01_summary_items_only_use_kpi_values_and_changes() -> None:
    generate_and_store_simulation(seed=42)

    payload = client.get("/api/renewal/R-01/scenarios/C/summary").json()

    for section in ["main_benefits", "main_risks"]:
        for item in payload[section]:
            assert item["kpi_id"]
            assert item["value"] is not None
            assert item["baseline_value"] is not None
            assert item["absolute_change"] is not None
            assert "summary" in item


def test_r01_recommendation_api_returns_review_order_without_official_best_claim() -> None:
    generate_and_store_simulation(seed=42)

    response = client.get("/api/renewal/R-01/recommendation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "R-01"
    assert payload["method"] == "rule_based_poc_summary"
    assert payload["llm_interface_reserved"] is True
    assert len(payload["review_order"]) == 4
    assert len(payload["summaries"]) == 4
    assert "不代表正式最佳政策方案" in payload["recommendation_note"]


def test_r01_summary_returns_404_for_unknown_scenario() -> None:
    response = client.get("/api/renewal/R-01/scenarios/Z/summary")

    assert response.status_code == 404


def test_rule_based_provider_accepts_summary_input_contract() -> None:
    current = {"scenario_id": "0", "assumptions": []}
    target = {"scenario_id": "A", "assumptions": ["Synthetic Data"]}
    kpis = {
        "records": [
            {
                "kpi_id": "resilience_score",
                "name": "都市韌性健康度",
                "value": 52.0,
                "unit": "分",
                "baseline_value": 49.0,
                "absolute_change": 3.0,
                "confidence_level": "medium",
            },
            {
                "kpi_id": "resident_population",
                "name": "居住人口",
                "value": 18000,
                "unit": "人",
                "baseline_value": 19000,
                "absolute_change": -1000,
                "confidence_level": "high",
            },
            {
                "kpi_id": "green_ratio",
                "name": "綠覆率",
                "value": 0.2,
                "unit": "比例",
                "baseline_value": 0.18,
                "absolute_change": 0.02,
                "confidence_level": "low",
            },
        ]
    }

    summary_input = build_decision_summary_input(current, target, kpis)
    summary = get_decision_summary_provider().summarize(summary_input)

    assert summary["scenario_id"] == "A"
    assert summary["main_benefits"]
    assert summary["main_risks"]
    assert summary["recommended_actions"]
