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
