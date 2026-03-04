# SKU-Ops Frontend

React app for supply yard material management. Built with [Vite](https://vitejs.dev/), [Tailwind CSS](https://tailwindcss.com/), and [Tremor](https://tremor.so/).

## Development

```bash
npm run dev        # Start dev server on http://localhost:3000 (proxies API to :8000)
npm run build      # Production build → dist/
npm run preview    # Preview production build locally
```

## Environment

See `frontend/.env.example`. In development, the Vite dev server proxies `/api` to `localhost:8000` automatically — no env var needed.

For standalone frontend deployments (separate host from backend), set:

```
VITE_BACKEND_URL=https://api.your-domain.com
```
