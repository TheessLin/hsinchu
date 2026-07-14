import type { ReactElement } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type Feature from "ol/Feature";
import type { FeatureLike } from "ol/Feature";
import GeoJSON from "ol/format/GeoJSON";
import VectorLayer from "ol/layer/Vector";
import OlMap from "ol/Map";
import { fromLonLat } from "ol/proj";
import VectorSource from "ol/source/Vector";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style";
import type { StyleFunction } from "ol/style/Style";
import View from "ol/View";
import { apiFetch } from "./api";

type ScenarioId = "0" | "A" | "B" | "C";
type ViewMode = "2d" | "3d";
type CompareMode = "before" | "after" | "overlay";
type BuildingStatus = "before" | "kept" | "added" | "removed";
type RankingObjective = "resilience" | "housing" | "parking" | "green_open_space" | "transport" | "disaster";

type GeoJsonGeometry = {
  type: string;
  coordinates: unknown;
};

type GeoJsonFeature = {
  type: "Feature";
  properties: Record<string, unknown>;
  geometry: GeoJsonGeometry;
};

type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

type Phase2CandidateDetail = {
  candidate_id: string;
  area: number;
  average_resilience_score: number;
  average_renewal_opportunity_score: number;
  primary_issues: string[];
  geometry: GeoJsonGeometry;
  seed: number;
  data_type: "synthetic";
};

type RenewalCurrentPayload = {
  candidate_id: string;
  seed: number;
  data_type: "synthetic";
  disclaimer: string;
  blocks: GeoJsonFeatureCollection;
  buildings: GeoJsonFeatureCollection;
  roads: GeoJsonFeatureCollection;
  facilities: GeoJsonFeatureCollection;
};

type ScenarioRecord = {
  scenario_id: ScenarioId;
  scenario_name: string;
  description: string;
  assumptions: string[];
  removed_building_ids: string[];
  added_buildings: Array<Record<string, unknown> & { geometry: GeoJsonGeometry }>;
  modified_roads: Array<Record<string, unknown> & { geometry: GeoJsonGeometry }>;
  added_facilities: Array<Record<string, unknown> & { geometry: GeoJsonGeometry }>;
  parameter_values: Record<string, number>;
  created_at: string;
  simulation_seed: number;
};

type KpiRecord = {
  kpi_id: string;
  name: string;
  value: number | null;
  unit: string;
  baseline_value: number | null;
  absolute_change: number | null;
  percentage_change: number | null;
  formula_reference: string;
  confidence_level: string;
  assumptions: string[];
  reason: string | null;
};

type KpiPayload = {
  scenario_id: ScenarioId;
  scenario_name: string;
  kpis: Record<string, KpiRecord>;
  records: KpiRecord[];
};

type DecisionSummaryItem = {
  kpi_id?: string;
  name?: string;
  summary?: string;
  action?: string;
  item?: string;
  evidence_kpi_ids?: string[];
};

type DecisionTradeoffItem = {
  summary: string;
  evidence_kpi_ids: string[];
};

type DecisionSummaryPayload = {
  scenario_id: ScenarioId;
  executive_summary: string;
  main_benefits: DecisionSummaryItem[];
  main_risks: DecisionSummaryItem[];
  tradeoffs: DecisionTradeoffItem[];
  recommended_actions: DecisionSummaryItem[];
  uncertain_items: DecisionSummaryItem[];
  data_disclaimer: string;
};

type ComparisonPayload = {
  scenarios: Array<{
    scenario_id: ScenarioId;
    scenario_name: string;
    kpis: Record<string, KpiRecord>;
    records: KpiRecord[];
  }>;
  rankings?: Record<RankingObjective, RankingRow[]>;
};

type RankingRow = {
  rank: number;
  objective_id: RankingObjective;
  objective_label: string;
  scenario_id: ScenarioId;
  scenario_name: string;
  rank_score: number | null;
  kpi_ids: string[];
  evidence: Array<{
    kpi_id: string;
    name: string;
    value: number | null;
    unit: string;
    baseline_value: number | null;
    absolute_change: number | null;
  }>;
};

type ScenarioRunKpisPayload = {
  scenario: ScenarioRecord;
  kpis: KpiPayload;
  summary: DecisionSummaryPayload;
};

type ScenarioUiParams = {
  residential_units: number;
  commercial_floor_area: number;
  parking_spaces: number;
  park_area_m2: number;
  green_ratio: number;
  sidewalk_width_m: number;
  bus_service_level: number;
  bike_station_count: number;
};

type BuildingProperties = {
  building_id: string;
  block_id: string;
  floors: number;
  height_m: number;
  construction_year: number | null;
  age: number | null;
  use_type: string;
  residential_units: number;
  commercial_floor_area: number;
  estimated_population: number;
  parking_spaces: number;
  renewal_status: string;
  status: BuildingStatus;
};

const SCENARIO_LABELS: Record<ScenarioId, string> = {
  "0": "Scenario 0｜現況",
  A: "Scenario A｜住宅導向",
  B: "Scenario B｜韌性導向",
  C: "Scenario C｜交通商業導向",
};

const RANKING_OBJECTIVES: Array<{ id: RankingObjective; label: string }> = [
  { id: "resilience", label: "綜合韌性" },
  { id: "housing", label: "住宅供給" },
  { id: "parking", label: "停車改善" },
  { id: "green_open_space", label: "綠地及開放空間" },
  { id: "transport", label: "交通可達" },
  { id: "disaster", label: "防災避難" },
];

const EXPORT_ITEMS = [
  { label: "Scenario JSON", path: "json", filename: "scenario.json" },
  { label: "建物 GeoJSON", path: "buildings.geojson", filename: "buildings.geojson" },
  { label: "道路 GeoJSON", path: "roads.geojson", filename: "roads.geojson" },
  { label: "設施 GeoJSON", path: "facilities.geojson", filename: "facilities.geojson" },
  { label: "KPI CSV", path: "kpis.csv", filename: "kpis.csv" },
  { label: "Decision Summary JSON", path: "decision-summary.json", filename: "decision-summary.json" },
] as const;

const PARAM_CONFIG: Array<{
  key: keyof ScenarioUiParams;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
}> = [
  { key: "residential_units", label: "住宅戶數", unit: "戶", min: 0, max: 900, step: 10 },
  { key: "commercial_floor_area", label: "商業樓地板面積", unit: "m2", min: 0, max: 60000, step: 500 },
  { key: "parking_spaces", label: "停車席數", unit: "席", min: 0, max: 900, step: 10 },
  { key: "park_area_m2", label: "公園與開放空間", unit: "m2", min: 0, max: 12000, step: 100 },
  { key: "green_ratio", label: "綠覆率", unit: "比例", min: 0, max: 0.8, step: 0.01 },
  { key: "sidewalk_width_m", label: "人行道寬度", unit: "m", min: 0, max: 3.5, step: 0.1 },
  { key: "bus_service_level", label: "公車服務等級", unit: "級", min: 0, max: 4, step: 1 },
  { key: "bike_station_count", label: "自行車站數", unit: "站", min: 0, max: 4, step: 1 },
];

const DEFAULT_PARAMS: Record<ScenarioId, ScenarioUiParams> = {
  "0": {
    residential_units: 0,
    commercial_floor_area: 0,
    parking_spaces: 0,
    park_area_m2: 0,
    green_ratio: 0.18,
    sidewalk_width_m: 0.8,
    bus_service_level: 0,
    bike_station_count: 0,
  },
  A: {
    residential_units: 520,
    commercial_floor_area: 3500,
    parking_spaces: 280,
    park_area_m2: 1500,
    green_ratio: 0.24,
    sidewalk_width_m: 1.2,
    bus_service_level: 0,
    bike_station_count: 0,
  },
  B: {
    residential_units: 90,
    commercial_floor_area: 1200,
    parking_spaces: 90,
    park_area_m2: 4200,
    green_ratio: 0.38,
    sidewalk_width_m: 1.8,
    bus_service_level: 0,
    bike_station_count: 0,
  },
  C: {
    residential_units: 160,
    commercial_floor_area: 36000,
    parking_spaces: 220,
    park_area_m2: 700,
    green_ratio: 0.22,
    sidewalk_width_m: 2.6,
    bus_service_level: 2,
    bike_station_count: 2,
  },
};

const KPI_ORDER = [
  "resilience_score",
  "renewal_opportunity_score",
  "residential_units",
  "resident_population",
  "daytime_population",
  "parking_supply",
  "parking_demand",
  "parking_gap",
  "park_area_m2",
  "green_ratio",
  "open_space_ratio",
  "bus_access_score",
  "bike_access_score",
  "walkability_score",
  "shelter_service_population",
  "emergency_access_score",
  "commercial_activity_score",
];

const layerDefaults = {
  blocks: true,
  roads: true,
  buildings: true,
  facilities: true,
};

const boundaryStyle = new Style({
  stroke: new Stroke({ color: "#be123c", width: 3 }),
  fill: new Fill({ color: "rgba(225, 29, 72, 0.06)" }),
});

const blockStyle = new Style({
  stroke: new Stroke({ color: "rgba(71, 85, 105, 0.58)", width: 1.2 }),
  fill: new Fill({ color: "rgba(226, 232, 240, 0.18)" }),
});

const roadStyle = new Style({
  stroke: new Stroke({ color: "#64748b", width: 2.2 }),
});

const selectedBuildingStyle = new Style({
  stroke: new Stroke({ color: "#111827", width: 2.5 }),
  fill: new Fill({ color: "rgba(17, 24, 39, 0.38)" }),
});

const facilityStyles: Record<string, Style> = {
  park: pointStyle("#16a34a", 8),
  open_space: pointStyle("#65a30d", 8),
  disaster_plaza: pointStyle("#dc2626", 8),
  shelter: pointStyle("#dc2626", 8),
  parking: pointStyle("#2563eb", 7),
  underground_parking: pointStyle("#2563eb", 7),
  shared_parking: pointStyle("#2563eb", 7),
  bus_stop: pointStyle("#f97316", 6),
  bike_station: pointStyle("#0891b2", 6),
  clinic: pointStyle("#9333ea", 6),
  childcare: pointStyle("#db2777", 6),
  elderly_service: pointStyle("#7c3aed", 6),
  market: pointStyle("#ca8a04", 6),
};

export function RenewalCandidatePage({
  candidateId,
  onBack,
}: {
  candidateId: string;
  onBack: () => void;
}): ReactElement {
  const [detail, setDetail] = useState<Phase2CandidateDetail | null>(null);
  const [current, setCurrent] = useState<RenewalCurrentPayload | null>(null);
  const [scenarioRecords, setScenarioRecords] = useState<Record<ScenarioId, ScenarioRecord> | null>(null);
  const [activeScenarioId, setActiveScenarioId] = useState<ScenarioId>("0");
  const [activeScenario, setActiveScenario] = useState<ScenarioRecord | null>(null);
  const [kpiPayload, setKpiPayload] = useState<KpiPayload | null>(null);
  const [summaryPayload, setSummaryPayload] = useState<DecisionSummaryPayload | null>(null);
  const [comparison, setComparison] = useState<ComparisonPayload | null>(null);
  const [draftParams, setDraftParams] = useState<ScenarioUiParams>(DEFAULT_PARAMS["0"]);
  const [appliedParams, setAppliedParams] = useState<ScenarioUiParams>(DEFAULT_PARAMS["0"]);
  const [viewMode, setViewMode] = useState<ViewMode>("2d");
  const [compareMode, setCompareMode] = useState<CompareMode>("after");
  const [rankingObjective, setRankingObjective] = useState<RankingObjective>("resilience");
  const [overlayOpacity, setOverlayOpacity] = useState(0.72);
  const [layers, setLayers] = useState(layerDefaults);
  const [selectedBuilding, setSelectedBuilding] = useState<BuildingProperties | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const selectedBuildingIdRef = useRef<string | null>(null);
  const opacityRef = useRef(overlayOpacity);
  const sourceRefs = useRef({
    boundary: new VectorSource(),
    blocks: new VectorSource(),
    roads: new VectorSource(),
    buildings: new VectorSource(),
    facilities: new VectorSource(),
  });
  const layerRefs = useRef<Partial<Record<keyof typeof sourceRefs.current, VectorLayer<VectorSource>>>>({});

  selectedBuildingIdGetter = () => selectedBuildingIdRef.current;
  opacityGetter = () => opacityRef.current;

  const isDirty = JSON.stringify(draftParams) !== JSON.stringify(appliedParams);
  const displayedBuildings = useMemo(
    () => (current && activeScenario ? buildBuildingCollection(current, activeScenario, compareMode) : emptyCollection()),
    [activeScenario, compareMode, current]
  );
  const displayedRoads = useMemo(
    () => (current && activeScenario ? buildRoadCollection(current, activeScenario, compareMode) : emptyCollection()),
    [activeScenario, compareMode, current]
  );
  const displayedFacilities = useMemo(
    () => (current && activeScenario ? buildFacilityCollection(current, activeScenario, compareMode) : emptyCollection()),
    [activeScenario, compareMode, current]
  );
  const selectedScenarioDescription = activeScenario?.description ?? "讀取中";
  const mainImprovements = useMemo(() => rankedKpiChanges(kpiPayload?.records ?? [], "positive"), [kpiPayload]);
  const mainTradeoffs = useMemo(() => rankedKpiChanges(kpiPayload?.records ?? [], "negative"), [kpiPayload]);
  const rankingRows = useMemo(() => scenarioRanking(comparison, rankingObjective), [comparison, rankingObjective]);
  const comparisonRows = useMemo(() => comparisonTableRows(comparison), [comparison]);

  const setSelectedBuildingFromProperties = useCallback((properties: Record<string, unknown> | null): void => {
    if (!properties?.building_id) {
      selectedBuildingIdRef.current = null;
      setSelectedBuilding(null);
      layerRefs.current.buildings?.changed();
      return;
    }
    const building = toBuildingProperties(properties);
    selectedBuildingIdRef.current = building.building_id;
    setSelectedBuilding(building);
    layerRefs.current.buildings?.changed();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setInitialLoading(true);
    setError(null);
    Promise.all([
      apiFetch(`/api/v1/phase2/candidates/${encodeURIComponent(candidateId)}`, { signal: controller.signal }),
      apiFetch("/api/renewal/R-01/current", { signal: controller.signal }),
      apiFetch("/api/renewal/R-01/scenarios", { signal: controller.signal }),
      apiFetch("/api/renewal/R-01/scenarios/0/kpis", { signal: controller.signal }),
      apiFetch("/api/renewal/R-01/scenarios/0/summary", { signal: controller.signal }),
    ])
      .then(async ([detailResponse, currentResponse, scenariosResponse, kpiResponse, summaryResponse]) => {
        for (const response of [detailResponse, currentResponse, scenariosResponse, kpiResponse, summaryResponse]) {
          if (!response.ok) {
            throw new Error(`資料讀取失敗：HTTP ${response.status}`);
          }
        }
        return {
          detail: (await detailResponse.json()) as Phase2CandidateDetail,
          current: (await currentResponse.json()) as RenewalCurrentPayload,
          scenarios: (await scenariosResponse.json()) as { records: ScenarioRecord[] },
          kpis: (await kpiResponse.json()) as KpiPayload,
          summary: (await summaryResponse.json()) as DecisionSummaryPayload,
        };
      })
      .then((payload) => {
        const records = Object.fromEntries(payload.scenarios.records.map((record) => [record.scenario_id, record])) as Record<
          ScenarioId,
          ScenarioRecord
        >;
        setDetail(payload.detail);
        setCurrent(payload.current);
        setScenarioRecords(records);
        setActiveScenario(records["0"]);
        setKpiPayload(payload.kpis);
        setSummaryPayload(payload.summary);
        void apiFetch("/api/renewal/R-01/comparison", { signal: controller.signal })
          .then(assertJson<ComparisonPayload>("Scenario comparison read failed"))
          .then(setComparison)
          .catch(() => undefined);
      })
      .catch((fetchError: unknown) => {
        if (fetchError instanceof DOMException && fetchError.name === "AbortError") {
          return;
        }
        setError(fetchError instanceof Error ? fetchError.message : "R-01 資料讀取失敗");
      })
      .finally(() => setInitialLoading(false));

    return () => controller.abort();
  }, [candidateId]);

  useEffect(() => {
    if (!mapElementRef.current) {
      return undefined;
    }
    const boundaryLayer = new VectorLayer({ source: sourceRefs.current.boundary, style: boundaryStyle });
    const blocksLayer = new VectorLayer({ source: sourceRefs.current.blocks, style: blockStyle });
    const roadsLayer = new VectorLayer({ source: sourceRefs.current.roads, style: roadStyle });
    const buildingsLayer = new VectorLayer({ source: sourceRefs.current.buildings, style: buildingStyleFunction });
    const facilitiesLayer = new VectorLayer({ source: sourceRefs.current.facilities, style: facilityStyleFunction });
    const map = new OlMap({
      target: mapElementRef.current,
      layers: [boundaryLayer, blocksLayer, roadsLayer, buildingsLayer, facilitiesLayer],
      view: new View({ center: fromLonLat([120.955, 24.79]), zoom: 15 }),
      controls: [],
    });
    mapRef.current = map;
    layerRefs.current = { boundary: boundaryLayer, blocks: blocksLayer, roads: roadsLayer, buildings: buildingsLayer, facilities: facilitiesLayer };

    map.on("singleclick", (event) => {
      const hit = map.forEachFeatureAtPixel(
        event.pixel,
        (feature) => {
          const candidate = feature as Feature;
          return candidate.get("building_id") ? candidate : undefined;
        },
        { layerFilter: (layer) => layer === buildingsLayer }
      ) as Feature | undefined;
      setSelectedBuildingFromProperties(hit?.getProperties() ?? null);
    });

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      layerRefs.current = {};
    };
  }, [setSelectedBuildingFromProperties]);

  useEffect(() => {
    opacityRef.current = overlayOpacity;
    layerRefs.current.buildings?.changed();
  }, [overlayOpacity]);

  useEffect(() => {
    layerRefs.current.blocks?.setVisible(layers.blocks);
    layerRefs.current.roads?.setVisible(layers.roads);
    layerRefs.current.buildings?.setVisible(layers.buildings);
    layerRefs.current.facilities?.setVisible(layers.facilities);
  }, [layers]);

  useEffect(() => {
    if (viewMode !== "2d") {
      return;
    }
    window.setTimeout(() => mapRef.current?.updateSize(), 0);
  }, [viewMode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !detail || !current) {
      return;
    }
    const format = new GeoJSON();
    const sources = sourceRefs.current;
    Object.values(sources).forEach((source) => source.clear());
    sources.boundary.addFeatures(
      format.readFeatures(featureCollectionFromGeometry(detail.geometry, { candidate_id: detail.candidate_id }), {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      })
    );
    sources.blocks.addFeatures(readFeatures(format, current.blocks));
    sources.roads.addFeatures(readFeatures(format, displayedRoads));
    sources.buildings.addFeatures(readFeatures(format, displayedBuildings));
    sources.facilities.addFeatures(readFeatures(format, displayedFacilities));
    const extent = sources.boundary.getExtent();
    if (extent && Number.isFinite(extent[0])) {
      map.getView().fit(extent, { padding: [48, 48, 48, 48], duration: 250, maxZoom: 17 });
    }
  }, [current, detail, displayedBuildings, displayedFacilities, displayedRoads]);

  function handleScenarioSelect(scenarioId: ScenarioId): void {
    const nextDefaults = DEFAULT_PARAMS[scenarioId];
    setActiveScenarioId(scenarioId);
    setDraftParams(nextDefaults);
    setAppliedParams(nextDefaults);
    setCompareMode(scenarioId === "0" ? "before" : "after");
    setSelectedBuildingFromProperties(null);
    if (scenarioRecords?.[scenarioId]) {
      setActiveScenario(scenarioRecords[scenarioId]);
    }
    setError(null);
    setSimulating(true);
    Promise.all([
      apiFetch(`/api/renewal/R-01/scenarios/${scenarioId}/kpis`).then(assertJson<KpiPayload>("KPI 讀取失敗")),
      apiFetch(`/api/renewal/R-01/scenarios/${scenarioId}/summary`).then(assertJson<DecisionSummaryPayload>("摘要讀取失敗")),
    ])
      .then(([nextKpis, nextSummary]) => {
        setKpiPayload(nextKpis);
        setSummaryPayload(nextSummary);
      })
      .catch((fetchError: unknown) => setError(fetchError instanceof Error ? fetchError.message : "Scenario 資料讀取失敗"))
      .finally(() => setSimulating(false));
  }

  async function handleRunSimulation(): Promise<void> {
    setSimulating(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/renewal/R-01/scenarios/${activeScenarioId}/run-kpis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parameter_values: mapUiParamsToApi(activeScenarioId, draftParams, detail?.area ?? 1) }),
      });
      if (!response.ok) {
        throw new Error(`重新模擬失敗：HTTP ${response.status}`);
      }
      const payload = (await response.json()) as ScenarioRunKpisPayload;
      setActiveScenario(payload.scenario);
      setKpiPayload(payload.kpis);
      setSummaryPayload(payload.summary);
      setAppliedParams(draftParams);
      setCompareMode(activeScenarioId === "0" ? "before" : "after");

      const comparisonResponse = await apiFetch("/api/renewal/R-01/comparison");
      if (comparisonResponse.ok) {
        setComparison((await comparisonResponse.json()) as ComparisonPayload);
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "重新模擬失敗");
    } finally {
      setSimulating(false);
    }
  }

  function resetScenarioDefaults(): void {
    setDraftParams(DEFAULT_PARAMS[activeScenarioId]);
  }

  function updateParam(key: keyof ScenarioUiParams, value: number): void {
    setDraftParams((currentParams) => ({ ...currentParams, [key]: value }));
  }

  async function handleExport(item: (typeof EXPORT_ITEMS)[number]): Promise<void> {
    const suffix = item.path === "json" ? ".json" : `/${item.path}`;
    const url = `/api/renewal/R-01/export/scenarios/${activeScenarioId}${suffix}`;
    const filename = `R-01_${activeScenarioId}_${item.filename}`;
    setExporting(item.label);
    setError(null);
    try {
      const response = await apiFetch(url);
      if (!response.ok) {
        throw new Error(`匯出失敗：HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "匯出失敗");
    } finally {
      setExporting(null);
    }
  }

  return (
    <main className="h-screen min-h-[720px] overflow-hidden bg-slate-100 text-slate-900">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-5">
        <div>
          <p className="text-xs font-semibold text-rose-700">R-01 都市更新 Scenario 模擬</p>
          <h1 className="text-xl font-semibold">R-01 都市更新情境模擬</h1>
        </div>
        <div className="flex items-center gap-2">
          <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-50" onClick={onBack} type="button">
            返回全市
          </button>
          <button
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
            disabled={exporting !== null}
            onClick={() => void handleExport(EXPORT_ITEMS[0])}
            type="button"
          >
            匯出
          </button>
          <button
            className="rounded-md bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900 ring-1 ring-amber-300 hover:bg-amber-100"
            onClick={() => setError("本系統使用 POC 模擬資料，不得作為正式政策判斷。")}
            type="button"
          >
            資料聲明
          </button>
        </div>
      </header>

      <section className="grid h-[calc(100vh-64px)] min-h-[656px] grid-cols-[280px_minmax(560px,1fr)_360px] grid-rows-[minmax(0,1fr)_230px] gap-3 p-3">
        <aside className="min-h-0 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-600">Scenario 選擇</h2>
          <div className="mt-3 grid gap-2">
            {(["0", "A", "B", "C"] as ScenarioId[]).map((scenarioId) => (
              <button
                className={`rounded-md border px-3 py-2 text-left text-sm font-semibold ${
                  activeScenarioId === scenarioId
                    ? "border-rose-700 bg-rose-50 text-rose-900"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
                key={scenarioId}
                onClick={() => handleScenarioSelect(scenarioId)}
                type="button"
              >
                {SCENARIO_LABELS[scenarioId]}
              </button>
            ))}
          </div>

          <section className="mt-5 border-t border-slate-200 pt-4">
            <h2 className="text-sm font-semibold text-slate-600">Scenario 說明</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">{selectedScenarioDescription}</p>
            <ul className="mt-3 space-y-2 text-xs text-slate-600">
              {(activeScenario?.assumptions ?? []).slice(0, 3).map((assumption) => (
                <li className="rounded-md bg-slate-50 px-2 py-1" key={assumption}>
                  {assumption}
                </li>
              ))}
            </ul>
          </section>

          <section className="mt-5 border-t border-slate-200 pt-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-600">可調整參數</h2>
              {isDirty ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">尚未套用</span> : null}
            </div>
            <div className="mt-3 space-y-4">
              {PARAM_CONFIG.map((config) => (
                <label className="block text-xs font-medium text-slate-600" key={config.key}>
                  <span className="flex items-center justify-between gap-3">
                    <span>{config.label}</span>
                    <span className="font-semibold text-slate-900">{formatParam(draftParams[config.key], config.unit)}</span>
                  </span>
                  <input
                    className="mt-2 w-full accent-rose-700"
                    disabled={activeScenarioId === "0"}
                    max={config.max}
                    min={config.min}
                    onChange={(event) => updateParam(config.key, Number(event.target.value))}
                    step={config.step}
                    type="range"
                    value={draftParams[config.key]}
                  />
                </label>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold hover:bg-slate-50"
                disabled={simulating}
                onClick={resetScenarioDefaults}
                type="button"
              >
                恢復預設值
              </button>
              <button
                className="rounded-md bg-rose-700 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={simulating}
                onClick={() => void handleRunSimulation()}
                type="button"
              >
                {simulating ? "模擬中" : "重新模擬"}
              </button>
            </div>
            {error ? <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}
          </section>

          <section className="mt-5 border-t border-slate-200 pt-4">
            <h2 className="text-sm font-semibold text-slate-600">資料匯出</h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">匯出目前選取的 Scenario、套用後圖層、KPI 與 AI 摘要。</p>
            <div className="mt-3 grid grid-cols-1 gap-2">
              {EXPORT_ITEMS.map((item) => (
                <button
                  className="rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
                  disabled={exporting !== null}
                  key={item.label}
                  onClick={() => void handleExport(item)}
                  type="button"
                >
                  {exporting === item.label ? "匯出中..." : item.label}
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex h-12 items-center justify-between border-b border-slate-200 px-4">
            <div>
              <h2 className="font-semibold">2D／3D 圖台</h2>
              <p className="text-xs text-slate-500">建物狀態：新增、移除、保留與現況</p>
            </div>
            <div className="flex items-center gap-2">
              <ModeButton active={viewMode === "2d"} label="2D" onClick={() => setViewMode("2d")} />
              <ModeButton active={viewMode === "3d"} label="3D" onClick={() => setViewMode("3d")} />
            </div>
          </div>

          <div className="flex h-11 items-center justify-between border-b border-slate-100 px-4">
            <div className="flex items-center gap-2">
              <ModeButton active={compareMode === "before"} label="更新前" onClick={() => setCompareMode("before")} />
              <ModeButton active={compareMode === "after"} label="更新後" onClick={() => setCompareMode("after")} />
              <ModeButton active={compareMode === "overlay"} label="透明度比較" onClick={() => setCompareMode("overlay")} />
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-600">
              透明度
              <input
                className="w-28 accent-rose-700"
                max={1}
                min={0.25}
                onChange={(event) => setOverlayOpacity(Number(event.target.value))}
                step={0.05}
                type="range"
                value={overlayOpacity}
              />
              {Math.round(overlayOpacity * 100)}%
            </label>
          </div>

          <div className="relative h-[calc(100%-92px)] bg-[#eef4f1]">
            <div className={viewMode === "2d" ? "h-full w-full" : "hidden h-full w-full"} ref={mapElementRef} />
            {viewMode === "3d" && current && activeScenario ? (
              <RenewalScene3D
                buildings={displayedBuildings}
                facilities={displayedFacilities}
                onSelectBuilding={setSelectedBuildingFromProperties}
                roads={displayedRoads}
                selectedBuildingId={selectedBuilding?.building_id ?? null}
              />
            ) : null}
            {(initialLoading || simulating) && <MapNotice>{initialLoading ? "讀取 R-01 資料中" : "重新模擬中"}</MapNotice>}
          </div>
        </section>

        <aside className="min-h-0 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <section>
            <h2 className="text-lg font-semibold">KPI 與影響摘要</h2>
            <p className="mt-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
              本系統使用模擬資料，不得作為正式政策判斷。
            </p>
          </section>

          <section className="mt-4 grid grid-cols-2 gap-3">
            {["resilience_score", "renewal_opportunity_score", "residential_units", "parking_gap"].map((id) => {
              const kpi = kpiPayload?.kpis[id];
              return kpi ? <KpiCard key={id} kpi={kpi} /> : null;
            })}
          </section>

          <DecisionSummaryPanel summary={summaryPayload} />

          <section className="mt-5">
            <h3 className="text-sm font-semibold text-slate-600">韌性雷達圖</h3>
            <EChart className="mt-2 h-[230px]" option={radarOption(kpiPayload)} />
          </section>

          <section className="mt-5">
            <h3 className="text-sm font-semibold text-slate-600">主要改善項目</h3>
            <ChangeList changes={mainImprovements} emptyText="目前沒有明顯正向變化" />
          </section>

          <section className="mt-5">
            <h3 className="text-sm font-semibold text-slate-600">主要負面影響</h3>
            <ChangeList changes={mainTradeoffs} emptyText="目前沒有明顯負向變化" />
          </section>

          <BuildingInfo building={selectedBuilding} />
        </aside>

        <section className="col-span-3 grid min-h-0 grid-cols-[1.2fr_0.9fr_0.85fr] gap-3">
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex h-10 items-center justify-between border-b border-slate-200 px-4">
              <h2 className="font-semibold">Scenario 比較表</h2>
              <span className="text-xs text-slate-500">單位依 KPI 定義顯示</span>
            </div>
            <div className="h-[178px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Scenario</th>
                    <th className="px-3 py-2 text-right">韌性分數</th>
                    <th className="px-3 py-2 text-right">更新機會</th>
                    <th className="px-3 py-2 text-right">住宅戶數</th>
                    <th className="px-3 py-2 text-right">綠覆率</th>
                    <th className="px-3 py-2 text-right">停車缺口</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((row) => (
                    <tr className="border-t border-slate-100" key={row.scenarioId}>
                      <td className="px-3 py-2 font-semibold">{row.label}</td>
                      <td className="px-3 py-2 text-right">{row.resilience}</td>
                      <td className="px-3 py-2 text-right">{row.renewal}</td>
                      <td className="px-3 py-2 text-right">{row.units}</td>
                      <td className="px-3 py-2 text-right">{row.green}</td>
                      <td className="px-3 py-2 text-right">{row.parkingGap}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="font-semibold">Before／After 長條圖</h2>
              <span className="text-xs text-slate-500">{SCENARIO_LABELS[activeScenarioId]}</span>
            </div>
            <EChart className="h-[168px]" option={beforeAfterOption(kpiPayload)} />
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <h2 className="font-semibold">各方案KPI排名</h2>
            <div className="mt-2 flex flex-wrap gap-1">
              {RANKING_OBJECTIVES.map((objective) => (
                <button
                  className={`rounded-md border px-2 py-1 text-xs font-semibold ${
                    rankingObjective === objective.id
                      ? "border-rose-700 bg-rose-50 text-rose-900"
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                  key={objective.id}
                  onClick={() => setRankingObjective(objective.id)}
                  type="button"
                >
                  {objective.label}
                </button>
              ))}
            </div>
            <div className="mt-2 space-y-2">
              {rankingRows.map((row, index) => (
                <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm" key={row.scenarioId}>
                  <span className="font-semibold">
                    {index + 1}. {row.label}
                  </span>
                  <span>{row.scoreLabel}</span>
                </div>
              ))}
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

function RenewalScene3D({
  buildings,
  roads,
  facilities,
  selectedBuildingId,
  onSelectBuilding,
}: {
  buildings: GeoJsonFeatureCollection;
  roads: GeoJsonFeatureCollection;
  facilities: GeoJsonFeatureCollection;
  selectedBuildingId: string | null;
  onSelectBuilding: (properties: Record<string, unknown> | null) => void;
}): ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return undefined;
    }
    const container = containerRef.current;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0xeef4f1);
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / Math.max(container.clientHeight, 1), 1, 6000);
    camera.position.set(0, 850, 1150);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    scene.add(new THREE.AmbientLight(0xffffff, 0.72));
    const directional = new THREE.DirectionalLight(0xffffff, 0.82);
    directional.position.set(450, 900, 500);
    scene.add(directional);

    const center = projectedCenter(buildings);
    const root = new THREE.Group();
    const buildingMeshes: THREE.Mesh[] = [];
    scene.add(root);
    addRoadLines(root, roads, center);
    buildings.features.forEach((feature) => {
      const mesh = buildingMesh(feature, center, selectedBuildingId);
      if (mesh) {
        root.add(mesh);
        buildingMeshes.push(mesh);
      }
    });
    addFacilityMarkers(root, facilities, center);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const handleClick = (event: MouseEvent): void => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(buildingMeshes, false)[0];
      onSelectBuilding(hit?.object.userData.properties ?? null);
    };
    renderer.domElement.addEventListener("click", handleClick);

    let animationFrame = 0;
    const animate = (): void => {
      controls.update();
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(animate);
    };
    animate();

    const resize = (): void => {
      const width = container.clientWidth;
      const height = Math.max(container.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener("resize", resize);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
      renderer.domElement.removeEventListener("click", handleClick);
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [buildings, facilities, onSelectBuilding, roads, selectedBuildingId]);

  return <div className="h-full w-full" ref={containerRef} />;
}

function KpiCard({ kpi }: { kpi: KpiRecord }): ReactElement {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{kpi.name}</div>
      <div className="mt-1 text-xl font-semibold">{formatKpiValue(kpi)}</div>
      <div className={`mt-1 text-xs ${Number(kpi.absolute_change ?? 0) >= 0 ? "text-green-700" : "text-red-700"}`}>
        {formatSigned(kpi.absolute_change, kpi.unit)}
      </div>
    </div>
  );
}

function ChangeList({ changes, emptyText }: { changes: KpiRecord[]; emptyText: string }): ReactElement {
  return (
    <div className="mt-2 space-y-2">
      {changes.length === 0 ? (
        <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">{emptyText}</p>
      ) : (
        changes.map((kpi) => (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-2 text-sm" key={kpi.kpi_id}>
            <div className="flex items-center justify-between gap-3">
              <span>{kpi.name}</span>
              <span className="font-semibold">{formatSigned(kpi.absolute_change, kpi.unit)}</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function DecisionSummaryPanel({ summary }: { summary: DecisionSummaryPayload | null }): ReactElement {
  if (!summary) {
    return (
      <section className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <h3 className="text-sm font-semibold text-slate-600">AI Decision Summary</h3>
        <p className="mt-2 text-sm text-slate-600">摘要讀取中</p>
      </section>
    );
  }

  return (
    <section className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <h3 className="text-sm font-semibold text-slate-700">AI Decision Summary</h3>
      <p className="mt-2 rounded-md bg-white p-2 text-sm leading-6 text-slate-800">{summary.executive_summary}</p>
      <SummaryItemList title="三項主要優勢" items={summary.main_benefits} field="summary" />
      <SummaryItemList title="三項主要風險" items={summary.main_risks} field="summary" />
      <SummaryItemList title="政策權衡" items={summary.tradeoffs} field="summary" />
      <SummaryItemList title="建議補強措施" items={summary.recommended_actions} field="action" />
      <SummaryItemList title="不確定事項" items={summary.uncertain_items} field="item" />
    </section>
  );
}

function SummaryItemList({
  title,
  items,
  field,
}: {
  title: string;
  items: Array<DecisionSummaryItem | DecisionTradeoffItem>;
  field: "summary" | "action" | "item";
}): ReactElement {
  return (
    <div className="mt-3">
      <h4 className="text-xs font-semibold text-slate-500">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-1 rounded-md bg-white px-2 py-1 text-xs text-slate-500">暫無項目</p>
      ) : (
        <ol className="mt-1 space-y-1">
          {items.slice(0, 3).map((item, index) => {
            const text = String((item as Record<string, unknown>)[field] ?? "");
            const evidence = "evidence_kpi_ids" in item ? item.evidence_kpi_ids ?? [] : [];
            return (
              <li className="rounded-md bg-white px-2 py-1 text-xs leading-5 text-slate-700" key={`${title}-${index}-${text}`}>
                <span>{text}</span>
                {evidence.length > 0 ? <span className="ml-1 text-slate-400">KPI: {evidence.join(", ")}</span> : null}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

function BuildingInfo({ building }: { building: BuildingProperties | null }): ReactElement {
  return (
    <section className="mt-5 border-t border-slate-200 pt-4">
      <h3 className="text-sm font-semibold text-slate-600">建物資訊</h3>
      {building ? (
        <dl className="mt-2 space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
          <InfoRow label="建物狀態" value={statusLabel(building.status)} />
          <InfoRow label="使用類型" value={useTypeLabel(building.use_type)} />
          <InfoRow label="樓層" value={`${building.floors} 層`} />
          <InfoRow label="高度" value={`${building.height_m.toFixed(1)} m`} />
          <InfoRow label="屋齡" value={building.age === null ? "新建" : `${building.age} 年`} />
          <InfoRow label="戶數" value={`${building.residential_units} 戶`} />
          <InfoRow label="模擬人口" value={`${Math.round(building.estimated_population).toLocaleString("zh-TW")} 人`} />
        </dl>
      ) : (
        <p className="mt-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">點選建物可檢視用途、樓層、高度與模擬人口。</p>
      )}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }): ReactElement {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function ModeButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }): ReactElement {
  return (
    <button
      className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${
        active ? "border-rose-700 bg-rose-50 text-rose-900" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
      }`}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function MapNotice({ children }: { children: string }): ReactElement {
  return <div className="absolute left-4 top-4 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">{children}</div>;
}

function EChart({ className, option }: { className: string; option: echarts.EChartsOption }): ReactElement {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) {
      return undefined;
    }
    const chart = echarts.init(ref.current);
    chart.setOption(option, true);
    const resize = (): void => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [option]);

  return <div className={className} ref={ref} />;
}

function buildBuildingCollection(current: RenewalCurrentPayload, scenario: ScenarioRecord, compareMode: CompareMode): GeoJsonFeatureCollection {
  const removedIds = new Set(scenario.removed_building_ids);
  const beforeFeatures = current.buildings.features.map((feature) => ({
    ...feature,
    properties: {
      ...feature.properties,
      status: compareMode === "before" ? "before" : removedIds.has(String(feature.properties.building_id)) ? "removed" : "kept",
    },
  }));

  if (compareMode === "before" || scenario.scenario_id === "0") {
    return { type: "FeatureCollection", features: beforeFeatures };
  }

  const kept = beforeFeatures.filter((feature) => feature.properties.status !== "removed");
  const removed = compareMode === "overlay" ? beforeFeatures.filter((feature) => feature.properties.status === "removed") : [];
  const added = scenario.added_buildings.map((building) => ({
    type: "Feature" as const,
    geometry: building.geometry,
    properties: {
      ...withoutGeometry(building),
      status: "added",
      construction_year: 2026,
      age: 0,
      renewal_status: "new",
    },
  }));
  return { type: "FeatureCollection", features: [...kept, ...removed, ...added] };
}

function buildRoadCollection(current: RenewalCurrentPayload, scenario: ScenarioRecord, compareMode: CompareMode): GeoJsonFeatureCollection {
  if (compareMode === "before" || scenario.modified_roads.length === 0) {
    return current.roads;
  }
  const modifiedById = new Map(scenario.modified_roads.map((road) => [String(road.road_id), road]));
  return {
    type: "FeatureCollection",
    features: current.roads.features.map((feature) => {
      const modified = modifiedById.get(String(feature.properties.road_id));
      return modified
        ? { type: "Feature", geometry: modified.geometry, properties: { ...feature.properties, ...withoutGeometry(modified), status: "modified" } }
        : feature;
    }),
  };
}

function buildFacilityCollection(current: RenewalCurrentPayload, scenario: ScenarioRecord, compareMode: CompareMode): GeoJsonFeatureCollection {
  if (compareMode === "before" || scenario.added_facilities.length === 0) {
    return current.facilities;
  }
  const added = scenario.added_facilities.map((facility) => ({
    type: "Feature" as const,
    geometry: facility.geometry,
    properties: { ...withoutGeometry(facility), status: "added" },
  }));
  return { type: "FeatureCollection", features: [...current.facilities.features, ...added] };
}

function withoutGeometry(record: Record<string, unknown> & { geometry?: unknown }): Record<string, unknown> {
  const { geometry: _geometry, ...properties } = record;
  return properties;
}

function mapUiParamsToApi(scenarioId: ScenarioId, params: ScenarioUiParams, landAreaM2: number): Record<string, number> {
  const housingCount = clamp(Math.round(params.residential_units / 130), 3, 5);
  const housingFloors = clamp(Math.round(params.residential_units / Math.max(housingCount * 12, 1)), 6, 18);
  const openSpaceRatio = clamp(params.park_area_m2 / Math.max(landAreaM2, 1), 0.15, 0.35);
  if (scenarioId === "0") {
    return {};
  }
  if (scenarioId === "A") {
    return {
      removal_count: 8,
      housing_building_count: housingCount,
      housing_floors: housingFloors,
      underground_parking_per_building: clamp(Math.round(params.parking_spaces / housingCount), 0, 180),
      minimum_open_space_ratio: openSpaceRatio,
      commercial_floor_area_multiplier: clamp(1 + params.commercial_floor_area / 50000, 1, 3),
    };
  }
  if (scenarioId === "B") {
    return {
      removal_count: 8,
      resilience_housing_building_count: clamp(Math.round(params.residential_units / 100), 0, 3),
      housing_floors: 9,
      park_count: clamp(Math.round(params.park_area_m2 / 3500), 0, 4),
      disaster_plaza_count: params.park_area_m2 > 1500 ? 1 : 0,
      emergency_route_count: clamp(Math.round(params.sidewalk_width_m * 2), 0, 8),
      green_coverage_target: clamp(params.green_ratio, 0, 0.8),
      eldercare_facilities: 1,
      childcare_facilities: 1,
      underground_parking_per_building: clamp(Math.round(params.parking_spaces), 0, 180),
    };
  }
  return {
    removal_count: 8,
    mixed_use_building_count: clamp(Math.round(params.commercial_floor_area / 12000), 0, 5),
    housing_floors: clamp(Math.round(params.residential_units / 12), 6, 18),
    commercial_floor_area_multiplier: clamp(1 + params.commercial_floor_area / 45000, 1, 3),
    sidewalk_width_gain_m: clamp(params.sidewalk_width_m - 0.8, 0, 3),
    new_bus_stops: clamp(Math.round(params.bus_service_level), 0, 4),
    new_bike_stations: clamp(Math.round(params.bike_station_count), 0, 4),
    shared_parking_spaces: clamp(Math.round(params.parking_spaces), 0, 300),
    daytime_population_multiplier: clamp(1 + params.commercial_floor_area / 100000, 1, 2.5),
  };
}

function readFeatures(format: GeoJSON, collection: GeoJsonFeatureCollection): Feature[] {
  return format.readFeatures(collection, { dataProjection: "EPSG:4326", featureProjection: "EPSG:3857" }) as Feature[];
}

function featureCollectionFromGeometry(geometry: GeoJsonGeometry, properties: Record<string, unknown>): GeoJsonFeatureCollection {
  return { type: "FeatureCollection", features: [{ type: "Feature", properties, geometry }] };
}

function emptyCollection(): GeoJsonFeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

const buildingStyleFunction: StyleFunction = (feature: FeatureLike): Style => {
  const building = toBuildingProperties(feature.getProperties());
  if (building.building_id === selectedBuildingIdRefValue()) {
    return selectedBuildingStyle;
  }
  const opacity = opacityRefValue();
  const color = statusColor(building.status);
  return new Style({
    stroke: new Stroke({ color: strokeForStatus(building.status), width: building.status === "removed" ? 1.8 : 0.9 }),
    fill: new Fill({ color: hexToRgba(color, building.status === "removed" ? 0.22 : opacity) }),
  });
};

const facilityStyleFunction: StyleFunction = (feature: FeatureLike): Style => {
  return facilityStyles[String(feature.get("facility_type"))] ?? pointStyle("#475569", 6);
};

let selectedBuildingIdGetter = (): string | null => null;
let opacityGetter = (): number => 0.72;

function selectedBuildingIdRefValue(): string | null {
  return selectedBuildingIdGetter();
}

function opacityRefValue(): number {
  return opacityGetter();
}

function pointStyle(color: string, radius: number): Style {
  return new Style({
    image: new CircleStyle({
      radius,
      fill: new Fill({ color }),
      stroke: new Stroke({ color: "#ffffff", width: 2 }),
    }),
  });
}

function toBuildingProperties(properties: Record<string, unknown>): BuildingProperties {
  return {
    building_id: String(properties.building_id ?? ""),
    block_id: String(properties.block_id ?? ""),
    floors: Number(properties.floors ?? 0),
    height_m: Number(properties.height_m ?? 0),
    construction_year: properties.construction_year === undefined ? null : Number(properties.construction_year),
    age: properties.age === undefined ? null : Number(properties.age),
    use_type: String(properties.use_type ?? ""),
    residential_units: Number(properties.residential_units ?? 0),
    commercial_floor_area: Number(properties.commercial_floor_area ?? 0),
    estimated_population: Number(properties.estimated_population ?? 0),
    parking_spaces: Number(properties.parking_spaces ?? 0),
    renewal_status: String(properties.renewal_status ?? ""),
    status: (properties.status ?? "before") as BuildingStatus,
  };
}

function buildingMesh(feature: GeoJsonFeature, center: [number, number], selectedBuildingId: string | null): THREE.Mesh | null {
  if (feature.geometry.type !== "Polygon") {
    return null;
  }
  const properties = toBuildingProperties(feature.properties);
  const coordinates = feature.geometry.coordinates as number[][][];
  const ring = coordinates[0];
  if (!Array.isArray(ring) || ring.length < 4) {
    return null;
  }
  const shape = new THREE.Shape();
  ring.forEach((coordinate, index) => {
    const [x, y] = localPoint(coordinate as [number, number], center);
    if (index === 0) {
      shape.moveTo(x, y);
    } else {
      shape.lineTo(x, y);
    }
  });
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: Math.max(properties.height_m, 3), bevelEnabled: false });
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const oldX = position.getX(index);
    const oldY = position.getY(index);
    const oldZ = position.getZ(index);
    position.setXYZ(index, oldX, oldZ, -oldY);
  }
  position.needsUpdate = true;
  geometry.computeVertexNormals();

  const color = properties.building_id === selectedBuildingId ? 0x111827 : statusColor(properties.status);
  const material = new THREE.MeshLambertMaterial({
    color,
    transparent: true,
    opacity: properties.status === "removed" ? 0.28 : 0.86,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData = { properties: feature.properties };
  return mesh;
}

function addRoadLines(root: THREE.Group, collection: GeoJsonFeatureCollection, center: [number, number]): void {
  const material = new THREE.LineBasicMaterial({ color: 0x475569 });
  collection.features.forEach((feature) => {
    if (feature.geometry.type !== "LineString") {
      return;
    }
    const coordinates = feature.geometry.coordinates as number[][];
    const points = coordinates.map((coordinate) => {
      const [x, z] = localPoint(coordinate as [number, number], center);
      return new THREE.Vector3(x, 1.2, -z);
    });
    root.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material));
  });
}

function addFacilityMarkers(root: THREE.Group, collection: GeoJsonFeatureCollection, center: [number, number]): void {
  collection.features.forEach((feature) => {
    if (feature.geometry.type !== "Point") {
      return;
    }
    const [x, z] = localPoint(feature.geometry.coordinates as [number, number], center);
    const marker = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 12, 16), new THREE.MeshLambertMaterial({ color: 0x0f766e }));
    marker.position.set(x, 8, -z);
    root.add(marker);
  });
}

function projectedCenter(collection: GeoJsonFeatureCollection): [number, number] {
  const coordinates = collection.features.flatMap((feature) => polygonCoordinates(feature.geometry));
  const projected = coordinates.map((coordinate) => fromLonLat(coordinate));
  if (projected.length === 0) {
    return [0, 0];
  }
  const sum = projected.reduce<[number, number]>((acc, coordinate) => [acc[0] + coordinate[0], acc[1] + coordinate[1]], [0, 0]);
  return [sum[0] / projected.length, sum[1] / projected.length];
}

function polygonCoordinates(geometry: GeoJsonGeometry): Array<[number, number]> {
  if (geometry.type !== "Polygon") {
    return [];
  }
  return (geometry.coordinates as number[][][])[0].map((coordinate) => coordinate as [number, number]);
}

function localPoint(coordinate: [number, number], center: [number, number]): [number, number] {
  const projected = fromLonLat(coordinate);
  return [projected[0] - center[0], projected[1] - center[1]];
}

function statusColor(status: BuildingStatus): number {
  if (status === "added") {
    return 0x16a34a;
  }
  if (status === "removed") {
    return 0xdc2626;
  }
  if (status === "kept") {
    return 0x2563eb;
  }
  return 0x64748b;
}

function strokeForStatus(status: BuildingStatus): string {
  if (status === "added") {
    return "#166534";
  }
  if (status === "removed") {
    return "#991b1b";
  }
  return "rgba(15, 23, 42, 0.72)";
}

function hexToRgba(color: number, alpha: number): string {
  const red = (color >> 16) & 255;
  const green = (color >> 8) & 255;
  const blue = color & 255;
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function radarOption(payload: KpiPayload | null): echarts.EChartsOption {
  const kpis = payload?.kpis;
  const values = [
    kpis?.resilience_score?.value ?? 0,
    averageKpis(kpis, ["bus_access_score", "bike_access_score", "walkability_score"]),
    averageKpis(kpis, ["green_ratio", "open_space_ratio"], 100),
    averageKpis(kpis, ["shelter_service_population", "emergency_access_score"]),
    kpis?.commercial_activity_score?.value ?? 0,
    kpis?.renewal_opportunity_score?.value ?? 0,
  ];
  return {
    radar: {
      indicator: [
        { name: "韌性", max: 100 },
        { name: "交通", max: 100 },
        { name: "綠地", max: 100 },
        { name: "防災", max: 100 },
        { name: "商業", max: 100 },
        { name: "更新", max: 100 },
      ],
      radius: 78,
      axisName: { fontSize: 11 },
    },
    series: [{ type: "radar", data: [{ value: values, name: payload?.scenario_name ?? "Scenario" }], areaStyle: { color: "rgba(190,18,60,0.18)" } }],
    tooltip: {},
  };
}

function beforeAfterOption(payload: KpiPayload | null): echarts.EChartsOption {
  const selected = ["resilience_score", "green_ratio", "parking_supply", "commercial_activity_score"];
  const labels = selected.map((id) => payload?.kpis[id]?.name ?? id);
  return {
    grid: { left: 42, right: 8, top: 24, bottom: 42 },
    legend: { top: 0 },
    xAxis: { type: "category", data: labels, axisLabel: { rotate: 18, fontSize: 10 } },
    yAxis: { type: "value" },
    series: [
      { name: "Before", type: "bar", data: selected.map((id) => scaledKpi(payload?.kpis[id], "baseline")) },
      { name: "After", type: "bar", data: selected.map((id) => scaledKpi(payload?.kpis[id], "value")) },
    ],
    tooltip: { trigger: "axis" },
  };
}

function averageKpis(kpis: Record<string, KpiRecord> | undefined, ids: string[], multiplier = 1): number {
  if (!kpis) {
    return 0;
  }
  const values = ids.map((id) => kpis[id]?.value).filter((value): value is number => typeof value === "number");
  if (values.length === 0) {
    return 0;
  }
  return Math.min(100, (values.reduce((sum, value) => sum + value * multiplier, 0) / values.length));
}

function scaledKpi(kpi: KpiRecord | undefined, field: "value" | "baseline"): number {
  const value = field === "value" ? kpi?.value : kpi?.baseline_value;
  if (typeof value !== "number") {
    return 0;
  }
  if (kpi?.unit === "比例") {
    return value * 100;
  }
  return value;
}

function rankedKpiChanges(records: KpiRecord[], direction: "positive" | "negative"): KpiRecord[] {
  return records
    .filter((record) => typeof record.absolute_change === "number" && record.absolute_change !== 0)
    .filter((record) => (direction === "positive" ? Number(record.absolute_change) > 0 : Number(record.absolute_change) < 0))
    .sort((a, b) => Math.abs(Number(b.absolute_change)) - Math.abs(Number(a.absolute_change)))
    .slice(0, 3);
}

function scenarioRanking(
  comparison: ComparisonPayload | null,
  objective: RankingObjective
): Array<{ scenarioId: ScenarioId; label: string; rank: number; score: number; scoreLabel: string; evidenceLabel: string }> {
  const ranking = comparison?.rankings?.[objective];
  if (ranking && ranking.length > 0) {
    return ranking.map((row) => ({
      scenarioId: row.scenario_id,
      label: SCENARIO_LABELS[row.scenario_id],
      rank: row.rank,
      score: row.rank_score ?? 0,
      scoreLabel: row.rank_score === null ? "資料不足" : `${row.rank_score.toFixed(1)} 分`,
      evidenceLabel: row.evidence.map((item) => `${item.name}: ${formatRawKpiValue(item.value, item.unit)}`).join("、"),
    }));
  }
  return (comparison?.scenarios ?? [])
    .map((scenario, index) => ({
      scenarioId: scenario.scenario_id,
      label: SCENARIO_LABELS[scenario.scenario_id],
      rank: index + 1,
      score: scenario.kpis.resilience_score?.value ?? 0,
      scoreLabel: formatKpiValue(scenario.kpis.resilience_score),
      evidenceLabel: scenario.kpis.resilience_score?.name ?? "resilience_score",
    }))
    .sort((a, b) => b.score - a.score)
    .map((row, index) => ({ ...row, rank: index + 1 }));
}

function comparisonTableRows(comparison: ComparisonPayload | null): Array<Record<string, string> & { scenarioId: ScenarioId }> {
  return (comparison?.scenarios ?? []).map((scenario) => ({
    scenarioId: scenario.scenario_id,
    label: SCENARIO_LABELS[scenario.scenario_id],
    resilience: formatKpiValue(scenario.kpis.resilience_score),
    renewal: formatKpiValue(scenario.kpis.renewal_opportunity_score),
    units: formatKpiValue(scenario.kpis.residential_units),
    green: formatKpiValue(scenario.kpis.green_ratio),
    parkingGap: formatKpiValue(scenario.kpis.parking_gap),
  }));
}

function formatKpiValue(kpi: KpiRecord | undefined): string {
  if (!kpi || kpi.value === null) {
    return "-";
  }
  return formatRawKpiValue(kpi.value, kpi.unit);
}

function formatRawKpiValue(value: number | null, unit: string): string {
  if (value === null) {
    return "-";
  }
  if (unit === "比例") {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (unit === "分") {
    return `${value.toFixed(1)} 分`;
  }
  return `${Math.round(value).toLocaleString("zh-TW")} ${unit}`;
}

function formatSigned(value: number | null, unit: string): string {
  if (value === null) {
    return "變化量無法計算";
  }
  const sign = value > 0 ? "+" : "";
  if (unit === "比例") {
    return `${sign}${(value * 100).toFixed(1)}%`;
  }
  if (unit === "分") {
    return `${sign}${value.toFixed(1)} 分`;
  }
  return `${sign}${Math.round(value).toLocaleString("zh-TW")} ${unit}`;
}

function formatParam(value: number, unit: string): string {
  if (unit === "比例") {
    return `${(value * 100).toFixed(0)}%`;
  }
  if (unit === "m" || unit === "級" || unit === "站") {
    return `${value.toLocaleString("zh-TW")} ${unit}`;
  }
  return `${Math.round(value).toLocaleString("zh-TW")} ${unit}`;
}

function statusLabel(status: BuildingStatus): string {
  return { before: "更新前現況", kept: "保留", added: "新增", removed: "移除" }[status];
}

function useTypeLabel(useType: string): string {
  return { residential: "住宅", commercial: "商業", mixed_use: "混合使用", public: "公共服務", parking: "停車" }[useType] ?? useType;
}

function assertJson<T>(message: string): (response: Response) => Promise<T> {
  return async (response: Response): Promise<T> => {
    if (!response.ok) {
      throw new Error(`${message}：HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
