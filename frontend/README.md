# AdaptAid web app

Next.js 16 (App Router, React 19, Tailwind 4, shadcn/ui). See the [project README](../README.md).

- `npm run dev`: development server (expects the API at `BACKEND_URL`, default http://localhost:8000)
- `npm run gen:api`: regenerate the typed API client from the backend's OpenAPI schema (`make gen-api` from the root)
- `npx playwright test --project=e2e`: browser journeys against a production build
- `src/app/api/[...path]/route.ts`: same-origin proxy to FastAPI; `src/proxy.ts`: role-based route gating
