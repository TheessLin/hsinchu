import type { ReactElement } from "react";
import { useEffect, useRef, useState } from "react";
import GeoJSON from "ol/format/GeoJSON";
import VectorLayer from "ol/layer/Vector";
import OlMap from "ol/Map";
import VectorSource from "ol/source/Vector";
import { Fill, Stroke, Style } from "ol/style";
import View from "ol/View";
import { apiFetch } from "./api";

type Phase2CandidateDetail = {
  phase1_data_version: string;
  phase2_data_version: string;
  candidate_id: string;
  source_candidate_rank: number;
  grid_ids: string[];
  grid_count: number;
  area: number;
  average_resilience_score: number;
  average_renewal_opportunity_score: number;
  primary_issues: string[];
  geometry: unknown;
  seed: number;
  simulation_parameters: Record<string, number>;
  data_type: "synthetic";
  disclaimer: string;
};

const UI = {
  title: "\u90fd\u5e02\u66f4\u65b0\u6a21\u64ec",
  subtitle: "\u7b2c\u4e8c\u968e\u6bb5\u8cc7\u6599\u8854\u63a5",
  back: "\u8fd4\u56de\u7b2c\u4e00\u968e\u6bb5\u5716\u53f0",
  boundary: "\u5019\u9078\u5340\u7bc4\u570d",
  averageResilience: "\u5e73\u5747\u97cc\u6027\u5206\u6578",
  renewalOpportunity: "\u66f4\u65b0\u6a5f\u6703\u5206\u6578",
  primaryIssues: "\u4e3b\u8981\u554f\u984c",
  gridCount: "\u5305\u542b\u7db2\u683c\u6578",
  area: "\u9762\u7a4d",
  seed: "\u6a21\u64ec Seed",
  versions: "\u8cc7\u6599\u7248\u672c",
  loading: "\u8f09\u5165\u4e2d",
  notFound: "\u67e5\u7121\u5019\u9078\u5340\u8cc7\u6599",
  disclaimer: "\u672c\u7cfb\u7d71\u4f7f\u7528\u6a21\u64ec\u8cc7\u6599\uff0c\u4e0d\u5f97\u4f5c\u70ba\u6b63\u5f0f\u653f\u7b56\u5224\u65b7",
  noIssues: "\u5c1a\u7121\u4e3b\u8981\u554f\u984c\u8cc7\u6599"
};

const boundaryStyle = new Style({
  stroke: new Stroke({ color: "#e11d48", width: 4 }),
  fill: new Fill({ color: "rgba(225, 29, 72, 0.14)" })
});

export function RenewalCandidatePage({
  candidateId,
  onBack
}: {
  candidateId: string;
  onBack: () => void;
}): ReactElement {
  const [detail, setDetail] = useState<Phase2CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const sourceRef = useRef<VectorSource | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    apiFetch(`/api/v1/phase2/candidates/${encodeURIComponent(candidateId)}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(response.status === 404 ? UI.notFound : `${UI.notFound}: ${response.status}`);
        }
        return (await response.json()) as Phase2CandidateDetail;
      })
      .then(setDetail)
      .catch((fetchError: unknown) => {
        if (fetchError instanceof DOMException && fetchError.name === "AbortError") {
          return;
        }
        setDetail(null);
        setError(fetchError instanceof Error ? fetchError.message : UI.notFound);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [candidateId]);

  useEffect(() => {
    if (!mapElementRef.current) {
      return undefined;
    }

    const source = new VectorSource();
    const layer = new VectorLayer({ source, style: boundaryStyle });
    const map = new OlMap({
      target: mapElementRef.current,
      layers: [layer],
      view: new View({ center: [13462500, 2849000], zoom: 13 }),
      controls: []
    });

    mapRef.current = map;
    sourceRef.current = source;

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      sourceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const source = sourceRef.current;
    const map = mapRef.current;
    if (!source || !map || !detail) {
      return;
    }

    const format = new GeoJSON();
    const features = format.readFeatures(
      {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: { candidate_id: detail.candidate_id },
            geometry: detail.geometry
          }
        ]
      },
      { dataProjection: "EPSG:4326", featureProjection: "EPSG:3857" }
    );

    source.clear();
    source.addFeatures(features);
    const extent = source.getExtent();
    if (extent && Number.isFinite(extent[0])) {
      map.getView().fit(extent, { padding: [48, 48, 48, 48], duration: 250, maxZoom: 16 });
    }
  }, [detail]);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-900">
      <header className="flex h-[68px] items-center justify-between border-b border-slate-200 bg-white px-5">
        <div>
          <p className="text-xs font-semibold text-rose-700">{UI.subtitle}</p>
          <h1 className="text-xl font-semibold">
            {UI.title} {candidateId}
          </h1>
        </div>
        <button
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          onClick={onBack}
          type="button"
        >
          {UI.back}
        </button>
      </header>

      <section className="grid min-h-[calc(100vh-68px)] grid-cols-[minmax(620px,1fr)_360px] gap-3 p-3">
        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex h-11 items-center justify-between border-b border-slate-200 px-4">
            <h2 className="font-semibold">{UI.boundary}</h2>
            <span className="text-xs font-medium text-amber-800">{UI.disclaimer}</span>
          </div>
          <div className="relative h-[calc(100%-44px)] min-h-[560px] bg-[#eef4f1]">
            <div className="h-full w-full" ref={mapElementRef} />
            {loading ? (
              <div className="absolute left-4 top-4 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
                {UI.loading}
              </div>
            ) : null}
            {error ? (
              <div className="absolute left-4 top-4 rounded-md border border-red-200 bg-white px-3 py-2 text-sm text-red-700 shadow-sm">
                {error}
              </div>
            ) : null}
          </div>
        </section>

        <aside className="space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {detail ? (
            <>
              <section>
                <h2 className="text-lg font-semibold">{detail.candidate_id}</h2>
                <p className="mt-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                  {UI.disclaimer}
                </p>
              </section>

              <section className="grid grid-cols-2 gap-3">
                <MetricCard label={UI.averageResilience} value={formatScore(detail.average_resilience_score)} />
                <MetricCard label={UI.renewalOpportunity} value={formatScore(detail.average_renewal_opportunity_score)} />
                <MetricCard label={UI.gridCount} value={String(detail.grid_count)} />
                <MetricCard label={UI.area} value={`${Math.round(detail.area).toLocaleString("zh-TW")} m\u00b2`} />
              </section>

              <section>
                <h3 className="text-sm font-semibold text-slate-600">{UI.primaryIssues}</h3>
                <div className="mt-2 space-y-2">
                  {detail.primary_issues.length > 0 ? (
                    detail.primary_issues.map((issue, index) => (
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-2 text-sm" key={issue}>
                        {index + 1}. {issue}
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-slate-500">{UI.noIssues}</div>
                  )}
                </div>
              </section>

              <section className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="flex justify-between gap-3">
                  <span className="text-slate-500">{UI.seed}</span>
                  <span className="font-medium">{detail.seed}</span>
                </div>
                <div className="mt-2 flex justify-between gap-3">
                  <span className="text-slate-500">{UI.versions}</span>
                  <span className="font-medium">
                    {detail.phase1_data_version} / {detail.phase2_data_version}
                  </span>
                </div>
              </section>
            </>
          ) : (
            <div className="text-sm text-slate-600">{loading ? UI.loading : error ?? UI.notFound}</div>
          )}
        </aside>
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }): ReactElement {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(1) : "-";
}
