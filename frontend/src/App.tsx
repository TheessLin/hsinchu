import type { ReactElement } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import type Feature from "ol/Feature";
import type { FeatureLike } from "ol/Feature";
import GeoJSON from "ol/format/GeoJSON";
import VectorLayer from "ol/layer/Vector";
import OlMap from "ol/Map";
import { fromLonLat } from "ol/proj";
import VectorSource from "ol/source/Vector";
import { Fill, Stroke, Style } from "ol/style";
import type { StyleFunction } from "ol/style/Style";
import View from "ol/View";
import { apiFetch } from "./api";
import { RenewalCandidatePage } from "./RenewalCandidatePage";

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: unknown[];
};

type ScoreDetail = {
  score: number;
  components: Record<string, number>;
  weights: Record<string, number>;
  raw_renewal_potential?: number;
};

type DimensionScoreKey =
  | "resilience_score"
  | "built_environment_score"
  | "disaster_evacuation_score"
  | "transport_access_score"
  | "social_demographic_score"
  | "living_health_score"
  | "renewal_potential_score";

type ResilienceRecord = {
  grid_id: string;
  centroid_x: number;
  centroid_y: number;
  district_type: string;
  land_use_type: string;
  population: number;
  daytime_population: number;
  elderly_ratio: number;
  child_ratio: number;
  building_count: number;
  average_building_age: number;
  old_building_ratio: number;
  building_coverage_ratio: number;
  narrow_road_ratio: number;
  open_space_ratio: number;
  green_ratio: number;
  parking_supply: number;
  parking_demand: number;
  bus_access_score: number;
  bike_access_score: number;
  walkability_score: number;
  shelter_access_score: number;
  fire_risk: number;
  flood_risk: number;
  medical_access_score: number;
  park_access_score: number;
  commercial_activity: number;
  ownership_complexity: number;
  renewal_potential: number;
  built_environment_score: number;
  disaster_evacuation_score: number;
  transport_access_score: number;
  social_demographic_score: number;
  living_health_score: number;
  renewal_potential_score: number;
  resilience_score: number;
  score_details: Record<DimensionScoreKey, ScoreDetail>;
};

type CandidateArea = {
  candidate_id: string;
  candidate_rank: number;
  grid_count: number;
  grid_ids: string[];
  area: number;
  average_resilience_score: number;
  average_renewal_opportunity_score: number;
  primary_issues: string[];
  geometry: unknown;
};

type HoverInfo = {
  gridId: string;
  score: number;
  x: number;
  y: number;
};

const DIMENSIONS: Array<{ key: DimensionScoreKey; label: string }> = [
  { key: "resilience_score", label: "綜合健康度" },
  { key: "built_environment_score", label: "建成環境" },
  { key: "disaster_evacuation_score", label: "災害與避難" },
  { key: "transport_access_score", label: "交通可及" },
  { key: "social_demographic_score", label: "社會人口" },
  { key: "living_health_score", label: "生活服務與健康" },
  { key: "renewal_potential_score", label: "更新整備健康度" }
];

const DIMENSION_LABELS = Object.fromEntries(DIMENSIONS.map((dimension) => [dimension.key, dimension.label])) as Record<
  DimensionScoreKey,
  string
>;

const COMPONENT_LABELS: Record<string, string> = {
  building_age_condition: "建物屋齡狀態",
  old_building_condition: "老舊建物狀態",
  coverage_condition: "建蔽壓力",
  density_condition: "建物密度",
  shelter_access: "避難可及",
  fire_safety: "火災安全",
  flood_safety: "淹水安全",
  road_evacuation_condition: "道路避難條件",
  open_space_support: "開放空間支援",
  bus_access: "公車可及",
  bike_access: "自行車可及",
  walkability: "步行友善",
  parking_adequacy: "停車供需",
  elderly_vulnerability: "高齡脆弱度",
  child_service_balance: "兒少服務平衡",
  residential_pressure: "居住人口壓力",
  daytime_pressure: "日間人口壓力",
  medical_access: "醫療可及",
  park_access: "公園可及",
  green_environment: "綠地環境",
  open_space_environment: "開放空間環境",
  daily_service_activity: "日常服務活動",
  renewal_pressure_inverse: "更新壓力反向指標",
  ownership_simplicity: "產權單純度",
  old_building_inverse: "老舊程度反向指標"
};

const INDICATOR_LABELS: Array<[keyof ResilienceRecord, string, "integer" | "ratio" | "score"]> = [
  ["population", "居住人口", "integer"],
  ["daytime_population", "日間人口", "integer"],
  ["elderly_ratio", "高齡人口比例", "ratio"],
  ["child_ratio", "兒少人口比例", "ratio"],
  ["building_count", "建物數", "integer"],
  ["average_building_age", "平均屋齡", "integer"],
  ["old_building_ratio", "老舊建物比例", "ratio"],
  ["building_coverage_ratio", "建蔽率", "ratio"],
  ["narrow_road_ratio", "狹窄道路比例", "ratio"],
  ["open_space_ratio", "開放空間比例", "ratio"],
  ["green_ratio", "綠地比例", "ratio"],
  ["parking_supply", "停車供給", "integer"],
  ["parking_demand", "停車需求", "integer"],
  ["bus_access_score", "公車可及分數", "score"],
  ["bike_access_score", "自行車可及分數", "score"],
  ["walkability_score", "步行分數", "score"],
  ["shelter_access_score", "避難可及分數", "score"],
  ["fire_risk", "火災風險", "score"],
  ["flood_risk", "淹水風險", "score"],
  ["medical_access_score", "醫療可及分數", "score"],
  ["park_access_score", "公園可及分數", "score"],
  ["commercial_activity", "商業活動", "score"],
  ["ownership_complexity", "產權複雜度", "score"],
  ["renewal_potential", "更新機會分數", "score"]
];

const hiddenGridStyle = new Style({
  stroke: new Stroke({ color: "rgba(0,0,0,0)", width: 0 }),
  fill: new Fill({ color: "rgba(0,0,0,0)" })
});

const selectedGridStyle = new Style({
  stroke: new Stroke({ color: "#111827", width: 2.6 }),
  fill: new Fill({ color: "rgba(17, 24, 39, 0.2)" })
});

const boundaryStyle = new Style({
  stroke: new Stroke({ color: "#0f766e", width: 2.5 }),
  fill: new Fill({ color: "rgba(240, 253, 250, 0.08)" })
});

const candidateOutlineStyle = new Style({
  stroke: new Stroke({ color: "#7c3aed", width: 3 }),
  fill: new Fill({ color: "rgba(124, 58, 237, 0.08)" })
});

const selectedCandidateOutlineStyle = new Style({
  stroke: new Stroke({ color: "#e11d48", width: 4 }),
  fill: new Fill({ color: "rgba(225, 29, 72, 0.12)" })
});

const scoreStyles = {
  red: new Style({
    stroke: new Stroke({ color: "rgba(127, 29, 29, 0.75)", width: 0.8 }),
    fill: new Fill({ color: "rgba(220, 38, 38, 0.72)" })
  }),
  amber: new Style({
    stroke: new Stroke({ color: "rgba(146, 64, 14, 0.7)", width: 0.8 }),
    fill: new Fill({ color: "rgba(245, 158, 11, 0.72)" })
  }),
  lightGreen: new Style({
    stroke: new Stroke({ color: "rgba(21, 128, 61, 0.65)", width: 0.8 }),
    fill: new Fill({ color: "rgba(134, 239, 172, 0.72)" })
  }),
  green: new Style({
    stroke: new Stroke({ color: "rgba(20, 83, 45, 0.75)", width: 0.8 }),
    fill: new Fill({ color: "rgba(21, 128, 61, 0.78)" })
  })
};

export function App(): ReactElement {
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [records, setRecords] = useState<ResilienceRecord[]>([]);
  const [candidates, setCandidates] = useState<CandidateArea[]>([]);
  const [activeDimension, setActiveDimension] = useState<DimensionScoreKey>("resilience_score");
  const [scoreMin, setScoreMin] = useState(0);
  const [scoreMax, setScoreMax] = useState(100);
  const [seedInput, setSeedInput] = useState("42");
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedGridId, setSelectedGridId] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [showCandidateOutlines, setShowCandidateOutlines] = useState(true);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);

  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const gridLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const gridSourceRef = useRef<VectorSource | null>(null);
  const candidateLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const candidateSourceRef = useRef<VectorSource | null>(null);
  const activeDimensionRef = useRef<DimensionScoreKey>(activeDimension);
  const scoreRangeRef = useRef({ min: scoreMin, max: scoreMax });
  const selectedGridIdRef = useRef<string | null>(selectedGridId);
  const selectedCandidateIdRef = useRef<string | null>(selectedCandidateId);
  const recordsRef = useRef<ResilienceRecord[]>([]);
  const candidatesRef = useRef<CandidateArea[]>([]);

  const recordById = useMemo(() => new Map(records.map((record) => [record.grid_id, record])), [records]);
  const selectedRecord = selectedGridId ? recordById.get(selectedGridId) ?? null : null;
  const filteredRecords = useMemo(
    () => records.filter((record) => record[activeDimension] >= scoreMin && record[activeDimension] <= scoreMax),
    [activeDimension, records, scoreMax, scoreMin]
  );
  const topCandidates = useMemo(() => candidates.slice(0, 5), [candidates]);
  const renewalCandidateId = useMemo(() => {
    const match = currentPath.match(/^\/renewal\/([^/]+)$/);
    return match ? decodeURIComponent(match[1]) : null;
  }, [currentPath]);
  const averageDimensionScores = useMemo(() => {
    if (filteredRecords.length === 0) {
      return DIMENSIONS.slice(1).map(() => 0);
    }

    return DIMENSIONS.slice(1).map((dimension) =>
      round1(filteredRecords.reduce((sum, record) => sum + record[dimension.key], 0) / filteredRecords.length)
    );
  }, [filteredRecords]);

  useEffect(() => {
    const handlePopState = (): void => setCurrentPath(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/v1/health", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`健康檢查失敗：${response.status}`);
        }

        return response.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setHealthError(error instanceof Error ? error.message : "健康檢查發生未知錯誤");
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!mapElementRef.current) {
      return undefined;
    }

    const boundarySource = new VectorSource();
    const gridSource = new VectorSource();
    const candidateSource = new VectorSource();
    const boundaryLayer = new VectorLayer({ source: boundarySource, style: boundaryStyle });
    const gridLayer = new VectorLayer({ source: gridSource, style: gridStyleFunction });
    const candidateLayer = new VectorLayer({ source: candidateSource, style: candidateStyleFunction });
    const map = new OlMap({
      target: mapElementRef.current,
      layers: [boundaryLayer, gridLayer, candidateLayer],
      view: new View({ center: fromLonLat([120.955, 24.8]), zoom: 11 }),
      controls: []
    });
    const geoJsonFormat = new GeoJSON();
    const controller = new AbortController();

    mapRef.current = map;
    gridLayerRef.current = gridLayer;
    gridSourceRef.current = gridSource;
    candidateLayerRef.current = candidateLayer;
    candidateSourceRef.current = candidateSource;

    Promise.all([
      apiFetch("/api/boundary", { signal: controller.signal }).then(assertJson<GeoJsonFeatureCollection>("研究範圍載入失敗")),
      apiFetch("/api/grids", { signal: controller.signal }).then(assertJson<GeoJsonFeatureCollection>("分析網格載入失敗"))
    ])
      .then(([boundaryGeoJson, gridGeoJson]) => {
        const boundaryFeatures = geoJsonFormat.readFeatures(boundaryGeoJson, {
          dataProjection: "EPSG:4326",
          featureProjection: "EPSG:3857"
        });
        const gridFeatures = geoJsonFormat.readFeatures(gridGeoJson, {
          dataProjection: "EPSG:4326",
          featureProjection: "EPSG:3857"
        });

        boundarySource.addFeatures(boundaryFeatures);
        gridSource.addFeatures(gridFeatures);
        applyRecordsToGridFeatures(recordsRef.current);
        applyCandidateFeatures(candidatesRef.current);

        const extent = boundarySource.getExtent();
        if (extent && Number.isFinite(extent[0])) {
          map.getView().fit(extent, { padding: [22, 22, 22, 22], duration: 250 });
        }
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setMapError(error instanceof Error ? error.message : "圖資載入發生未知錯誤");
      });

    map.on("pointermove", (event) => {
      const hit = map.forEachFeatureAtPixel(
        event.pixel,
        (feature) => {
          const candidate = feature as Feature;
          return candidate.get("grid_id") ? candidate : undefined;
        },
        { layerFilter: (layer) => layer === gridLayer }
      ) as Feature | undefined;

      const target = map.getTargetElement();
      target.style.cursor = hit ? "pointer" : "";

      if (!hit) {
        setHoverInfo(null);
        return;
      }

      const gridId = String(hit.get("grid_id"));
      const score = Number(hit.get(activeDimensionRef.current));
      const rect = target.getBoundingClientRect();
      const pointer = event.originalEvent as MouseEvent;
      setHoverInfo({
        gridId,
        score,
        x: pointer.clientX - rect.left + 12,
        y: pointer.clientY - rect.top + 12
      });
    });

    map.on("singleclick", (event) => {
      const clickedGrid = map.forEachFeatureAtPixel(
        event.pixel,
        (feature) => {
          const candidate = feature as Feature;
          return candidate.get("grid_id") ? candidate : undefined;
        },
        { layerFilter: (layer) => layer === gridLayer }
      ) as Feature | undefined;

      selectGrid(clickedGrid ? String(clickedGrid.get("grid_id")) : null);
    });

    void loadDashboardData(42, false);

    return () => {
      controller.abort();
      map.setTarget(undefined);
      mapRef.current = null;
      gridLayerRef.current = null;
      gridSourceRef.current = null;
      candidateLayerRef.current = null;
      candidateSourceRef.current = null;
    };
  }, []);

  useEffect(() => {
    activeDimensionRef.current = activeDimension;
    scoreRangeRef.current = { min: scoreMin, max: scoreMax };
    selectedGridIdRef.current = selectedGridId;
    selectedCandidateIdRef.current = selectedCandidateId;
    gridLayerRef.current?.changed();
    candidateLayerRef.current?.changed();
  }, [activeDimension, scoreMax, scoreMin, selectedGridId, selectedCandidateId]);

  useEffect(() => {
    recordsRef.current = records;
    applyRecordsToGridFeatures(records);
    if (!selectedGridId && records.length > 0) {
      selectGrid(records[0].grid_id);
    }
  }, [records, selectedGridId]);

  useEffect(() => {
    candidatesRef.current = candidates;
    applyCandidateFeatures(candidates);
  }, [candidates]);

  useEffect(() => {
    candidateLayerRef.current?.setVisible(showCandidateOutlines);
  }, [showCandidateOutlines]);

  async function loadDashboardData(seed: number, regenerate: boolean): Promise<void> {
    setIsGenerating(true);
    try {
      if (regenerate) {
        const generateResponse = await apiFetch("/api/simulation/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ seed })
        });
        if (!generateResponse.ok) {
          throw new Error(`模擬重新產生失敗：${generateResponse.status}`);
        }
      }

      const [resilienceResponse, candidatesResponse] = await Promise.all([apiFetch("/api/resilience"), apiFetch("/api/candidates")]);
      if (!resilienceResponse.ok) {
        throw new Error(`韌性評分載入失敗：${resilienceResponse.status}`);
      }
      if (!candidatesResponse.ok) {
        throw new Error(`候選區載入失敗：${candidatesResponse.status}`);
      }

      const resiliencePayload = (await resilienceResponse.json()) as { records: ResilienceRecord[] };
      const candidatesPayload = (await candidatesResponse.json()) as { records: CandidateArea[] };
      setRecords(resiliencePayload.records);
      setCandidates(candidatesPayload.records);
      setSelectedCandidateId(null);
      setMapError(null);
    } catch (error) {
      setMapError(error instanceof Error ? error.message : "資料載入發生未知錯誤");
    } finally {
      setIsGenerating(false);
    }
  }

  function applyRecordsToGridFeatures(nextRecords: ResilienceRecord[]): void {
    const source = gridSourceRef.current;
    if (!source) {
      return;
    }

    const nextRecordById = new Map(nextRecords.map((record) => [record.grid_id, record]));
    source.getFeatures().forEach((feature) => {
      const gridId = String(feature.get("grid_id"));
      const record = nextRecordById.get(gridId);
      if (!record) {
        return;
      }

      Object.entries(record).forEach(([key, value]) => {
        if (key !== "score_details") {
          feature.set(key, value, true);
        }
      });
    });
    gridLayerRef.current?.changed();
  }

  function applyCandidateFeatures(nextCandidates: CandidateArea[]): void {
    const source = candidateSourceRef.current;
    if (!source) {
      return;
    }

    const geoJsonFormat = new GeoJSON();
    source.clear();
    if (nextCandidates.length === 0) {
      candidateLayerRef.current?.changed();
      return;
    }

    const features = geoJsonFormat.readFeatures(candidateFeatureCollection(nextCandidates), {
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:3857"
    });
    source.addFeatures(features);
    candidateLayerRef.current?.changed();
  }

  const gridStyleFunction: StyleFunction = (feature: FeatureLike): Style => {
    const gridId = String(feature.get("grid_id") ?? "");
    if (gridId === selectedGridIdRef.current) {
      return selectedGridStyle;
    }

    const score = Number(feature.get(activeDimensionRef.current));
    const { min, max } = scoreRangeRef.current;
    if (!Number.isFinite(score) || score < min || score > max) {
      return hiddenGridStyle;
    }

    return styleForScore(score);
  };

  const candidateStyleFunction: StyleFunction = (feature: FeatureLike): Style => {
    const candidateId = String(feature.get("candidate_id") ?? "");
    return candidateId === selectedCandidateIdRef.current ? selectedCandidateOutlineStyle : candidateOutlineStyle;
  };

  function selectGrid(gridId: string | null): void {
    selectedGridIdRef.current = gridId;
    setSelectedGridId(gridId);
    gridLayerRef.current?.changed();
  }

  function handleRegenerate(): void {
    const seed = Number.parseInt(seedInput, 10);
    void loadDashboardData(Number.isFinite(seed) ? seed : 42, true);
  }

  function navigateToRenewal(candidateId: string): void {
    const path = `/renewal/${encodeURIComponent(candidateId)}`;
    window.history.pushState({}, "", path);
    setCurrentPath(path);
  }

  function navigateToDashboard(): void {
    window.history.pushState({}, "", "/");
    setCurrentPath("/");
  }

  function zoomToCandidate(candidate: CandidateArea): void {
    const source = candidateSourceRef.current;
    const map = mapRef.current;
    if (!source || !map) {
      return;
    }

    selectedCandidateIdRef.current = candidate.candidate_id;
    setSelectedCandidateId(candidate.candidate_id);
    const firstGridId = candidate.grid_ids[0] ?? null;
    if (firstGridId) {
      selectGrid(firstGridId);
    }

    const feature = source.getFeatures().find((item) => item.get("candidate_id") === candidate.candidate_id);
    const extent = feature?.getGeometry()?.getExtent();
    if (extent && Number.isFinite(extent[0])) {
      map.getView().fit(extent, { padding: [70, 70, 70, 70], duration: 450, maxZoom: 15 });
    }
    candidateLayerRef.current?.changed();
  }

  return (
    <>
      {renewalCandidateId ? <RenewalCandidatePage candidateId={renewalCandidateId} onBack={navigateToDashboard} /> : null}
      <main className={renewalCandidateId ? "hidden" : "h-screen min-h-[720px] overflow-hidden bg-slate-100 text-slate-900"}>
      <header className="flex h-[68px] items-center justify-between border-b border-slate-200 bg-white px-5">
        <div>
          <p className="text-xs font-semibold text-emerald-700">新竹市都市韌性健康模擬 POC</p>
          <h1 className="text-xl font-semibold">都市韌性互動圖台</h1>
        </div>
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
          本系統使用模擬資料，不得作為正式政策判斷
        </div>
      </header>

      <section className="grid h-[calc(100vh-68px)] min-h-[652px] grid-cols-[300px_minmax(520px,1fr)_360px] grid-rows-[1fr_210px] gap-3 p-3">
        <aside className="row-span-2 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <section>
            <h2 className="text-sm font-semibold text-slate-600">構面切換</h2>
            <div className="mt-3 space-y-2">
              {DIMENSIONS.map((dimension) => (
                <button
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${
                    activeDimension === dimension.key
                      ? "border-emerald-600 bg-emerald-50 text-emerald-900"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                  key={dimension.key}
                  onClick={() => setActiveDimension(dimension.key)}
                  type="button"
                >
                  {dimension.label}
                </button>
              ))}
            </div>
          </section>

          <section className="mt-5 border-t border-slate-200 pt-4">
            <h2 className="text-sm font-semibold text-slate-600">圖例</h2>
            <div className="mt-3 space-y-2 text-sm">
              <LegendRow color="bg-red-600" label="0-39 低分" />
              <LegendRow color="bg-amber-500" label="40-59 中低分" />
              <LegendRow color="bg-green-300" label="60-79 中高分" />
              <LegendRow color="bg-green-700" label="80-100 高分" />
              <label className="flex cursor-pointer items-center gap-2 pt-2 text-sm">
                <input
                  checked={showCandidateOutlines}
                  className="h-4 w-4 accent-violet-700"
                  onChange={(event) => setShowCandidateOutlines(event.target.checked)}
                  type="checkbox"
                />
                <span>{"\u986f\u793a\u5019\u9078\u5340\u5916\u6846"}</span>
              </label>
              <div className="flex items-center gap-2 pt-2">
                <span className="h-3 w-6 rounded-sm border-2 border-violet-600 bg-violet-100" />
                <span>都市更新候選區外框</span>
              </div>
            </div>
          </section>

          <section className="mt-5 border-t border-slate-200 pt-4">
            <h2 className="text-sm font-semibold text-slate-600">分數區間篩選</h2>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <label className="text-xs text-slate-500">
                最低分
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                  max={100}
                  min={0}
                  onChange={(event) => setScoreMin(clampNumber(Number(event.target.value), 0, scoreMax))}
                  type="number"
                  value={scoreMin}
                />
              </label>
              <label className="text-xs text-slate-500">
                最高分
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                  max={100}
                  min={0}
                  onChange={(event) => setScoreMax(clampNumber(Number(event.target.value), scoreMin, 100))}
                  type="number"
                  value={scoreMax}
                />
              </label>
            </div>
            <input
              className="mt-3 w-full accent-emerald-700"
              max={100}
              min={0}
              onChange={(event) => setScoreMin(Math.min(Number(event.target.value), scoreMax))}
              type="range"
              value={scoreMin}
            />
            <input
              className="w-full accent-emerald-700"
              max={100}
              min={0}
              onChange={(event) => setScoreMax(Math.max(Number(event.target.value), scoreMin))}
              type="range"
              value={scoreMax}
            />
            <p className="mt-2 text-xs text-slate-500">
              目前顯示 {filteredRecords.length} / {records.length || 0} 格
            </p>
          </section>

          <section className="mt-5 border-t border-slate-200 pt-4">
            <h2 className="text-sm font-semibold text-slate-600">模擬參數</h2>
            <label className="mt-3 block text-xs text-slate-500">
              固定 Seed
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                onChange={(event) => setSeedInput(event.target.value)}
                type="number"
                value={seedInput}
              />
            </label>
            <button
              className="mt-3 w-full rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={isGenerating}
              onClick={handleRegenerate}
              type="button"
            >
              {isGenerating ? "重新產生中..." : "重新產生模擬資料"}
            </button>
            <div className="mt-4 rounded-md bg-slate-50 p-3 text-xs text-slate-600">
              <div>API 狀態：{health?.status === "ok" ? "正常" : healthError ? "錯誤" : "載入中"}</div>
              <div className="mt-1 truncate">服務：{health?.service ?? "-"}</div>
              {healthError ? <div className="mt-1 text-red-700">{healthError}</div> : null}
            </div>
          </section>
        </aside>

        <section className="relative overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex h-11 items-center justify-between border-b border-slate-200 px-4">
            <div>
              <h2 className="font-semibold">OpenLayers 圖台</h2>
              <p className="text-xs text-slate-500">目前構面：{DIMENSION_LABELS[activeDimension]}</p>
            </div>
            <div className="text-sm text-slate-600">500m 網格：{records.length || "載入中"}</div>
          </div>
          <div className="relative h-[calc(100%-44px)] bg-[#eef4f1]">
            <div className="h-full w-full" ref={mapElementRef} />
            {mapError ? (
              <div className="absolute left-4 top-4 rounded-md border border-red-200 bg-white px-3 py-2 text-sm text-red-700 shadow-sm">
                {mapError}
              </div>
            ) : null}
            {hoverInfo ? (
              <div
                className="pointer-events-none absolute rounded-md border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow"
                style={{ left: hoverInfo.x, top: hoverInfo.y }}
              >
                <div className="font-semibold">{hoverInfo.gridId}</div>
                <div>
                  {DIMENSION_LABELS[activeDimension]}：{formatScore(hoverInfo.score)}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <aside className="row-span-2 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <RightPanel record={selectedRecord} />
        </aside>

        <section className="grid grid-cols-[minmax(420px,1fr)_minmax(360px,0.9fr)] gap-3">
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex h-10 items-center justify-between border-b border-slate-200 px-4">
              <h2 className="font-semibold">候選區排名</h2>
              <span className="text-xs text-slate-500">Top 5，代碼僅代表模擬群聚</span>
            </div>
            <div className="h-[170px] overflow-y-auto">
              {topCandidates.length === 0 ? (
                <div className="px-4 py-6 text-sm text-slate-500">目前條件下沒有符合門檻的候選區。</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500">
                    <tr>
                      <th className="px-3 py-2 text-left">排名</th>
                      <th className="px-3 py-2 text-left">候選區</th>
                      <th className="px-3 py-2 text-right">網格數</th>
                      <th className="px-3 py-2 text-right">健康度</th>
                      <th className="px-3 py-2 text-right">更新機會</th>
                      <th className="px-3 py-2 text-left">主要問題</th>
                      <th className="px-3 py-2 text-right">{"\u64cd\u4f5c"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topCandidates.map((candidate) => (
                      <tr
                        className={`cursor-pointer border-t border-slate-100 hover:bg-violet-50 ${
                          selectedCandidateId === candidate.candidate_id ? "bg-violet-50" : ""
                        }`}
                        key={candidate.candidate_id}
                        onClick={() => zoomToCandidate(candidate)}
                      >
                        <td className="px-3 py-2">{candidate.candidate_rank}</td>
                        <td className="px-3 py-2 font-semibold text-violet-800">{candidate.candidate_id}</td>
                        <td className="px-3 py-2 text-right">{candidate.grid_count}</td>
                        <td className="px-3 py-2 text-right">{formatScore(candidate.average_resilience_score)}</td>
                        <td className="px-3 py-2 text-right">{formatScore(candidate.average_renewal_opportunity_score)}</td>
                        <td className="max-w-[220px] truncate px-3 py-2">{candidate.primary_issues.join("、")}</td>
                        <td className="px-3 py-2 text-right">
                          {candidate.candidate_id === "R-01" ? (
                            <button
                              className="rounded-md bg-violet-700 px-2 py-1 text-xs font-semibold text-white hover:bg-violet-800"
                              onClick={(event) => {
                                event.stopPropagation();
                                navigateToRenewal(candidate.candidate_id);
                              }}
                              type="button"
                            >
                              {"\u9032\u5165\u90fd\u5e02\u66f4\u65b0\u6a21\u64ec"}
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="font-semibold">構面比較圖</h2>
              <span className="text-xs text-slate-500">依目前篩選網格平均</span>
            </div>
            <EChart
              className="h-[165px]"
              option={{
                grid: { left: 42, right: 8, top: 14, bottom: 36 },
                xAxis: {
                  type: "category",
                  axisLabel: { interval: 0, rotate: 20, fontSize: 10 },
                  data: DIMENSIONS.slice(1).map((dimension) => dimension.label)
                },
                yAxis: { type: "value", min: 0, max: 100 },
                series: [
                  {
                    type: "bar",
                    data: averageDimensionScores,
                    itemStyle: { color: "#047857" }
                  }
                ],
                tooltip: { trigger: "axis" }
              }}
            />
          </section>
        </section>
      </section>
      </main>
    </>
  );
}

function RightPanel({ record }: { record: ResilienceRecord | null }): ReactElement {
  if (!record) {
    return (
      <div>
        <h2 className="text-lg font-semibold">網格基本資料</h2>
        <p className="mt-3 text-sm text-slate-600">請點選地圖上的分析網格，查看模擬指標與構面分數。</p>
      </div>
    );
  }

  const dimensionValues = DIMENSIONS.slice(1).map((dimension) => record[dimension.key]);
  const problems = DIMENSIONS.slice(1)
    .map((dimension) => ({ label: dimension.label, score: record[dimension.key] }))
    .sort((a, b) => a.score - b.score)
    .slice(0, 3);
  const componentRows = Object.entries(record.score_details)
    .flatMap(([dimension, detail]) =>
      Object.entries(detail.components).map(([component, value]) => ({
        dimension: DIMENSION_LABELS[dimension as DimensionScoreKey],
        component: COMPONENT_LABELS[component] ?? component,
        value
      }))
    )
    .sort((a, b) => a.value - b.value)
    .slice(0, 8);

  return (
    <div className="space-y-4">
      <section>
        <h2 className="text-lg font-semibold">網格基本資料</h2>
        <dl className="mt-3 space-y-2 text-sm">
          <InfoRow label="grid_id" value={record.grid_id} />
          <InfoRow label="行政分區" value={cleanCategoryValue(record.district_type, "district")} />
          <InfoRow label="土地使用" value={cleanCategoryValue(record.land_use_type, "landUse")} />
          <InfoRow label="中心座標" value={`${record.centroid_x.toFixed(5)}, ${record.centroid_y.toFixed(5)}`} />
        </dl>
      </section>

      <section className="grid grid-cols-2 gap-3">
        <ScoreCard label="綜合健康度" value={record.resilience_score} />
        <ScoreCard label="更新機會分數" value={record.renewal_potential} />
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-600">六大構面雷達圖</h3>
        <EChart
          className="mt-2 h-[230px]"
          option={{
            radar: {
              indicator: DIMENSIONS.slice(1).map((dimension) => ({ name: dimension.label, max: 100 })),
              radius: 78,
              axisName: { fontSize: 11 }
            },
            series: [
              {
                type: "radar",
                data: [{ value: dimensionValues, name: record.grid_id }],
                areaStyle: { color: "rgba(4, 120, 87, 0.22)" },
                lineStyle: { color: "#047857" },
                itemStyle: { color: "#047857" }
              }
            ],
            tooltip: {}
          }}
        />
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-600">問題前三名</h3>
        <div className="mt-2 space-y-2">
          {problems.map((problem, index) => (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-2 text-sm" key={problem.label}>
              <div className="flex items-center justify-between">
                <span>
                  {index + 1}. {problem.label}
                </span>
                <span className="font-semibold text-red-700">{formatScore(problem.score)}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-600">構面計算明細</h3>
        <div className="mt-2 max-h-[190px] overflow-y-auto rounded-md border border-slate-200">
          <table className="w-full text-sm">
            <tbody>
              {componentRows.map((row) => (
                <tr className="border-b border-slate-100 last:border-b-0" key={`${row.dimension}-${row.component}`}>
                  <td className="px-3 py-2 text-slate-500">{row.dimension}</td>
                  <td className="px-3 py-2 text-slate-500">{row.component}</td>
                  <td className="px-3 py-2 text-right font-medium">{formatScore(row.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-slate-600">指標明細</h3>
        <div className="mt-2 max-h-[300px] overflow-y-auto rounded-md border border-slate-200">
          <table className="w-full text-sm">
            <tbody>
              {INDICATOR_LABELS.map(([key, label, type]) => (
                <tr className="border-b border-slate-100 last:border-b-0" key={String(key)}>
                  <td className="px-3 py-2 text-slate-500">{label}</td>
                  <td className="px-3 py-2 text-right font-medium">{formatValue(record[key], type)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
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

function InfoRow({ label, value }: { label: string; value: string }): ReactElement {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function ScoreCard({ label, value }: { label: string; value: number }): ReactElement {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${scoreTextColor(value)}`}>{formatScore(value)}</div>
    </div>
  );
}

function LegendRow({ color, label }: { color: string; label: string }): ReactElement {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-3 w-6 rounded-sm ${color}`} />
      <span>{label}</span>
    </div>
  );
}

function assertJson<T>(message: string): (response: Response) => Promise<T> {
  return async (response: Response): Promise<T> => {
    if (!response.ok) {
      throw new Error(`${message}：${response.status}`);
    }

    return (await response.json()) as T;
  };
}

function candidateFeatureCollection(candidates: CandidateArea[]): GeoJsonFeatureCollection {
  return {
    type: "FeatureCollection",
    features: candidates.map((candidate) => ({
      type: "Feature",
      properties: {
        candidate_id: candidate.candidate_id,
        candidate_rank: candidate.candidate_rank,
        grid_count: candidate.grid_count
      },
      geometry: candidate.geometry
    }))
  };
}

function styleForScore(score: number): Style {
  if (score < 40) {
    return scoreStyles.red;
  }
  if (score < 60) {
    return scoreStyles.amber;
  }
  if (score < 80) {
    return scoreStyles.lightGreen;
  }
  return scoreStyles.green;
}

function scoreTextColor(score: number): string {
  if (score < 40) {
    return "text-red-700";
  }
  if (score < 60) {
    return "text-amber-700";
  }
  if (score < 80) {
    return "text-green-600";
  }
  return "text-green-800";
}

function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(1) : "-";
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function clampNumber(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(Math.max(value, min), max);
}

function formatValue(value: unknown, type: "integer" | "ratio" | "score"): string {
  if (typeof value !== "number") {
    return "-";
  }
  if (type === "ratio") {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (type === "integer") {
    return Math.round(value).toLocaleString("zh-TW");
  }
  return value.toFixed(1);
}

function cleanCategoryValue(value: string, kind: "district" | "landUse"): string {
  if (!value.includes("\uFFFD")) {
    return value;
  }
  if (kind === "district") {
    if (value.includes("_")) {
      return "北區";
    }
    if (value.includes("F")) {
      return "東區";
    }
    if (value.includes("s")) {
      return "香山區";
    }
    return "模擬行政分區";
  }
  return "規則式模擬用地";
}
