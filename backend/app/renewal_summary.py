from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.phase2 import SYNTHETIC_DATA_DISCLAIMER
from app.renewal_current import R01_CANDIDATE_ID
from app.renewal_kpis import get_r01_scenario_comparison, get_r01_scenario_kpis
from app.renewal_scenarios import get_r01_scenario, normalize_scenario_id

BENEFIT_KPI_IDS = {
    "resilience_score",
    "renewal_opportunity_score",
    "residential_units",
    "resident_population",
    "daytime_population",
    "parking_supply",
    "park_area_m2",
    "park_service_population",
    "green_ratio",
    "open_space_ratio",
    "bus_access_score",
    "bike_access_score",
    "walkability_score",
    "shelter_service_population",
    "emergency_access_score",
    "commercial_activity_score",
}

RISK_KPI_IDS = {
    "parking_demand",
}

ACTION_RULES = [
    {
        "trigger": "parking_gap",
        "related": ["parking_gap", "parking_supply", "parking_demand"],
        "text": "停車缺口仍為負值，建議檢討共享停車、地下停車或需求管理配置。",
    },
    {
        "trigger": "resident_population",
        "related": ["resident_population", "residential_units"],
        "text": "居住人口或住宅戶數下降時，建議補充安置、分期施工與居住供給檢核。",
    },
    {
        "trigger": "daytime_population",
        "related": ["daytime_population", "commercial_activity_score"],
        "text": "日間人口下降時，建議檢討商業與公共服務量體是否符合方案目標。",
    },
    {
        "trigger": "green_ratio",
        "related": ["green_ratio", "open_space_ratio", "park_area_m2"],
        "text": "綠覆與開放空間提升幅度有限時，建議優先補強可使用綠地及開放空間。",
    },
    {
        "trigger": "emergency_access_score",
        "related": ["emergency_access_score", "walkability_score"],
        "text": "救災或步行可及性仍偏低時，建議檢討道路拓寬、人行空間與消防動線。",
    },
]


@dataclass(frozen=True)
class DecisionSummaryInput:
    current_scenario: dict[str, Any]
    target_scenario: dict[str, Any]
    kpi_results: dict[str, Any]
    assumptions: list[str]
    confidence_levels: dict[str, str]
    identified_tradeoffs: list[dict[str, Any]]


class DecisionSummaryProvider(Protocol):
    def summarize(self, summary_input: DecisionSummaryInput) -> dict[str, Any]:
        """Return a structured decision summary from calculated backend values."""


class RuleBasedDecisionSummaryProvider:
    def summarize(self, summary_input: DecisionSummaryInput) -> dict[str, Any]:
        target = summary_input.target_scenario
        kpis = _kpi_records(summary_input.kpi_results)
        benefits = _rank_changes(kpis, "benefit", 3)
        risks = _rank_changes(kpis, "risk", 3)
        tradeoffs = summary_input.identified_tradeoffs[:3]
        actions = _recommended_actions(kpis, risks)
        uncertain_items = _uncertain_items(kpis, summary_input.assumptions)

        return {
            "scenario_id": target["scenario_id"],
            "executive_summary": _executive_summary(target, kpis, benefits, risks),
            "main_benefits": benefits,
            "main_risks": risks,
            "tradeoffs": tradeoffs,
            "recommended_actions": actions,
            "uncertain_items": uncertain_items,
            "data_disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        }


def get_decision_summary_provider() -> DecisionSummaryProvider:
    # Future LLM integration can return another provider that consumes the same input.
    return RuleBasedDecisionSummaryProvider()


def get_r01_scenario_summary(scenario_id: str) -> dict[str, Any] | None:
    normalized = normalize_scenario_id(scenario_id)
    if normalized is None:
        return None
    current = get_r01_scenario("0")
    target = get_r01_scenario(normalized)
    kpis = get_r01_scenario_kpis(normalized)
    if current is None or target is None or kpis is None:
        return None
    return build_r01_decision_summary(target, kpis)


def build_r01_decision_summary(target_scenario: dict[str, Any], kpi_results: dict[str, Any]) -> dict[str, Any] | None:
    current = get_r01_scenario("0")
    if current is None:
        return None
    summary_input = build_decision_summary_input(current, target_scenario, kpi_results)
    return get_decision_summary_provider().summarize(summary_input)


def get_r01_recommendation() -> dict[str, Any]:
    comparison = get_r01_scenario_comparison()
    summaries: list[dict[str, Any]] = []
    for scenario in comparison["scenarios"]:
        summary = get_r01_scenario_summary(str(scenario["scenario_id"]))
        if summary is not None:
            summaries.append(summary)

    review_order = sorted(
        [
            {
                "scenario_id": scenario["scenario_id"],
                "scenario_name": scenario["scenario_name"],
                "simulated_resilience_score": scenario["kpis"]["resilience_score"]["value"],
                "simulated_renewal_opportunity_score": scenario["kpis"]["renewal_opportunity_score"]["value"],
            }
            for scenario in comparison["scenarios"]
        ],
        key=lambda item: (
            float(item["simulated_resilience_score"] or 0),
            float(item["simulated_renewal_opportunity_score"] or 0),
        ),
        reverse=True,
    )

    return {
        "candidate_id": R01_CANDIDATE_ID,
        "method": "rule_based_poc_summary",
        "review_order": review_order,
        "summaries": summaries,
        "data_disclaimer": SYNTHETIC_DATA_DISCLAIMER,
        "llm_interface_reserved": True,
        "recommendation_note": "依本POC模擬結果排序，僅供方案討論，不代表正式最佳政策方案。",
    }


def build_decision_summary_input(
    current_scenario: dict[str, Any],
    target_scenario: dict[str, Any],
    kpi_results: dict[str, Any],
) -> DecisionSummaryInput:
    kpis = _kpi_records(kpi_results)
    return DecisionSummaryInput(
        current_scenario=current_scenario,
        target_scenario=target_scenario,
        kpi_results=kpi_results,
        assumptions=list(target_scenario.get("assumptions", [])),
        confidence_levels={record["kpi_id"]: record["confidence_level"] for record in kpis},
        identified_tradeoffs=_identified_tradeoffs(kpis),
    )


def _kpi_records(kpi_results: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(record) for record in kpi_results.get("records", [])]


def _rank_changes(records: list[dict[str, Any]], direction: str, limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for record in records:
        change = record.get("absolute_change")
        if not isinstance(change, (int, float)) or change == 0:
            continue
        kpi_id = str(record["kpi_id"])
        is_benefit = (change > 0 and kpi_id in BENEFIT_KPI_IDS) or (change < 0 and kpi_id in RISK_KPI_IDS)
        if direction == "benefit" and is_benefit:
            selected.append(_change_item(record, "改善"))
        if direction == "risk" and not is_benefit:
            selected.append(_change_item(record, "惡化"))
    selected.sort(key=lambda item: abs(float(item["absolute_change"])), reverse=True)
    return selected[:limit]


def _identified_tradeoffs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    benefits = _rank_changes(records, "benefit", 4)
    risks = _rank_changes(records, "risk", 4)
    tradeoffs: list[dict[str, Any]] = []
    for benefit, risk in zip(benefits, risks, strict=False):
        tradeoffs.append(
            {
                "benefit_kpi_id": benefit["kpi_id"],
                "risk_kpi_id": risk["kpi_id"],
                "summary": f"{benefit['name']}改善，但{risk['name']}出現不利變化。",
                "evidence_kpi_ids": [benefit["kpi_id"], risk["kpi_id"]],
            }
        )
    return tradeoffs


def _recommended_actions(records: list[dict[str, Any]], risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(record["kpi_id"]): record for record in records}
    actions: list[dict[str, Any]] = []
    risk_ids = {str(risk["kpi_id"]) for risk in risks}
    for rule in ACTION_RULES:
        trigger = rule["trigger"]
        trigger_record = by_id.get(trigger)
        if trigger_record is None:
            continue
        value = trigger_record.get("value")
        change = trigger_record.get("absolute_change")
        should_add = trigger in risk_ids or (trigger == "parking_gap" and isinstance(value, (int, float)) and value < 0)
        if trigger in {"green_ratio", "emergency_access_score"} and isinstance(change, (int, float)) and change <= 0:
            should_add = True
        if should_add:
            actions.append(
                {
                    "action": rule["text"],
                    "evidence_kpi_ids": [kpi_id for kpi_id in rule["related"] if kpi_id in by_id],
                }
            )
    if not actions and "resilience_score" in by_id:
        actions.append(
            {
                "action": "建議將本方案作為進一步工程、財務及地方溝通檢核的討論版本。",
                "evidence_kpi_ids": ["resilience_score"],
            }
        )
    return actions[:3]


def _uncertain_items(records: list[dict[str, Any]], assumptions: list[str]) -> list[dict[str, Any]]:
    uncertain = [
        {
            "item": f"{record['name']}信心水準為{record['confidence_level']}，需以後續調查或實測資料校核。",
            "evidence_kpi_ids": [record["kpi_id"]],
        }
        for record in records
        if record.get("confidence_level") == "low"
    ][:3]
    if assumptions:
        uncertain.append(
            {
                "item": "Scenario 假設會影響模擬結果，應於後續設計階段重新檢核。",
                "evidence_kpi_ids": ["resilience_score"],
                "assumptions": assumptions[:3],
            }
        )
    return uncertain[:4]


def _executive_summary(
    target_scenario: dict[str, Any],
    records: list[dict[str, Any]],
    benefits: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> str:
    scenario_id = target_scenario["scenario_id"]
    resilience = next((record for record in records if record["kpi_id"] == "resilience_score"), None)
    base = f"依本POC模擬結果，Scenario {scenario_id} "
    if resilience is not None and resilience.get("value") is not None:
        base += f"都市韌性健康度為{_format_value(resilience['value'], resilience['unit'])}"
        if resilience.get("absolute_change") is not None:
            base += f"，相較現況{_format_change(resilience['absolute_change'], resilience['unit'])}"
        base += "。"
    else:
        base += "部分核心KPI無法計算。"
    if benefits:
        base += f"主要改善包含{benefits[0]['name']}。"
    if risks:
        base += f"同時需注意{risks[0]['name']}的不利變化。"
    base += "本摘要不宣稱該方案為正式最佳政策方案。"
    return base


def _change_item(record: dict[str, Any], direction_label: str) -> dict[str, Any]:
    return {
        "kpi_id": record["kpi_id"],
        "name": record["name"],
        "direction": direction_label,
        "value": record["value"],
        "unit": record["unit"],
        "baseline_value": record["baseline_value"],
        "absolute_change": record["absolute_change"],
        "summary": f"{record['name']}為{_format_value(record['value'], record['unit'])}，相較現況{_format_change(record['absolute_change'], record['unit'])}。",
        "confidence_level": record["confidence_level"],
    }


def _format_value(value: Any, unit: str) -> str:
    if value is None:
        return "無法計算"
    number = float(value)
    if unit == "比例":
        return f"{number * 100:.1f}%"
    if unit == "分":
        return f"{number:.1f}分"
    if unit == "m2":
        return f"{number:,.0f} m2"
    return f"{number:,.0f}{unit}"


def _format_change(value: Any, unit: str) -> str:
    if value is None:
        return "變化量無法計算"
    number = float(value)
    sign = "+" if number > 0 else ""
    if unit == "比例":
        return f"{sign}{number * 100:.1f}個百分點"
    if unit == "分":
        return f"{sign}{number:.1f}分"
    if unit == "m2":
        return f"{sign}{number:,.0f} m2"
    return f"{sign}{number:,.0f}{unit}"
