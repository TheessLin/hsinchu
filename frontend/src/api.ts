const STATIC_DEMO_ENABLED = import.meta.env.VITE_STATIC_DEMO === "1";

type StaticRoute = {
  pattern: RegExp;
  file: string;
};

const STATIC_ROUTES: StaticRoute[] = [
  { pattern: /^\/api\/v1\/health$/, file: "health.json" },
  { pattern: /^\/api\/boundary$/, file: "boundary.json" },
  { pattern: /^\/api\/grids$/, file: "grids.json" },
  { pattern: /^\/api\/simulation\/generate$/, file: "simulation-generate.json" },
  { pattern: /^\/api\/resilience$/, file: "resilience.json" },
  { pattern: /^\/api\/candidates$/, file: "candidates.json" },
  { pattern: /^\/api\/v1\/phase2\/candidates\/R-01$/, file: "phase2-candidate-R-01.json" },
  { pattern: /^\/api\/renewal\/R-01\/current$/, file: "renewal-current.json" },
  { pattern: /^\/api\/renewal\/R-01\/blocks$/, file: "renewal-blocks.json" },
  { pattern: /^\/api\/renewal\/R-01\/buildings$/, file: "renewal-buildings.json" },
  { pattern: /^\/api\/renewal\/R-01\/roads$/, file: "renewal-roads.json" },
  { pattern: /^\/api\/renewal\/R-01\/facilities$/, file: "renewal-facilities.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios$/, file: "renewal-scenarios.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/0$/, file: "renewal-scenario-0.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/A$/, file: "renewal-scenario-A.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/B$/, file: "renewal-scenario-B.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/C$/, file: "renewal-scenario-C.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/0\/kpis$/, file: "renewal-scenario-0-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/A\/kpis$/, file: "renewal-scenario-A-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/B\/kpis$/, file: "renewal-scenario-B-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/C\/kpis$/, file: "renewal-scenario-C-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/0\/summary$/, file: "renewal-scenario-0-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/A\/summary$/, file: "renewal-scenario-A-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/B\/summary$/, file: "renewal-scenario-B-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/C\/summary$/, file: "renewal-scenario-C-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/0\/run$/, file: "renewal-scenario-0.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/A\/run$/, file: "renewal-scenario-A.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/B\/run$/, file: "renewal-scenario-B.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/C\/run$/, file: "renewal-scenario-C.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/0\/run-kpis$/, file: "renewal-scenario-0-run-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/A\/run-kpis$/, file: "renewal-scenario-A-run-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/B\/run-kpis$/, file: "renewal-scenario-B-run-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/scenarios\/C\/run-kpis$/, file: "renewal-scenario-C-run-kpis.json" },
  { pattern: /^\/api\/renewal\/R-01\/comparison$/, file: "renewal-comparison.json" },
  { pattern: /^\/api\/renewal\/R-01\/recommendation$/, file: "renewal-recommendation.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/0\.json$/, file: "renewal-scenario-0-export.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/A\.json$/, file: "renewal-scenario-A-export.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/B\.json$/, file: "renewal-scenario-B-export.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/C\.json$/, file: "renewal-scenario-C-export.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/0\/buildings\.geojson$/, file: "renewal-scenario-0-buildings.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/A\/buildings\.geojson$/, file: "renewal-scenario-A-buildings.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/B\/buildings\.geojson$/, file: "renewal-scenario-B-buildings.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/C\/buildings\.geojson$/, file: "renewal-scenario-C-buildings.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/0\/roads\.geojson$/, file: "renewal-scenario-0-roads.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/A\/roads\.geojson$/, file: "renewal-scenario-A-roads.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/B\/roads\.geojson$/, file: "renewal-scenario-B-roads.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/C\/roads\.geojson$/, file: "renewal-scenario-C-roads.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/0\/facilities\.geojson$/, file: "renewal-scenario-0-facilities.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/A\/facilities\.geojson$/, file: "renewal-scenario-A-facilities.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/B\/facilities\.geojson$/, file: "renewal-scenario-B-facilities.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/C\/facilities\.geojson$/, file: "renewal-scenario-C-facilities.geojson" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/0\/kpis\.csv$/, file: "renewal-scenario-0-kpis.csv" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/A\/kpis\.csv$/, file: "renewal-scenario-A-kpis.csv" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/B\/kpis\.csv$/, file: "renewal-scenario-B-kpis.csv" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/C\/kpis\.csv$/, file: "renewal-scenario-C-kpis.csv" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/0\/decision-summary\.json$/, file: "renewal-scenario-0-decision-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/A\/decision-summary\.json$/, file: "renewal-scenario-A-decision-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/B\/decision-summary\.json$/, file: "renewal-scenario-B-decision-summary.json" },
  { pattern: /^\/api\/renewal\/R-01\/export\/scenarios\/C\/decision-summary\.json$/, file: "renewal-scenario-C-decision-summary.json" },
];

export function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (!STATIC_DEMO_ENABLED) {
    return fetch(input, init);
  }

  const requestPath = toRequestPath(input);
  const route = STATIC_ROUTES.find((candidate) => candidate.pattern.test(requestPath));
  if (!route) {
    return Promise.resolve(new Response(null, { status: 404, statusText: `Static demo data not found: ${requestPath}` }));
  }

  return fetch(staticAssetUrl(route.file), {
    signal: init?.signal,
  });
}

function toRequestPath(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return new URL(input, window.location.origin).pathname;
  }
  if (input instanceof URL) {
    return input.pathname;
  }
  return new URL(input.url, window.location.origin).pathname;
}

function staticAssetUrl(file: string): string {
  return `${import.meta.env.BASE_URL}demo-data/${file}`;
}
