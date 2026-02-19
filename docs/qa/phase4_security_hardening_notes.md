# Phase 4 Security Hardening Notes

## SQL injection elleni gyakorlat
- API adatelérés PostgREST query paraméterezett hívásokon keresztül történik (`api/supabase_client.py`),
  nem string-összefűzött SQL futtatással a request pathban.
- A futási útvonalak (`projects/files/runs`) explicit filter paramétereket használnak (`eq.`, `in.`).

## Auth policy guard
- Read-only ellenőrző script: `scripts/smoke_phase4_auth_security_config.py`.
- Ellenőrzött minimumok:
  - `jwt_exp <= 3600`
  - `refresh_token_rotation_enabled = true`
  - `password_min_length >= 6`

## HTTP security hardening
- API oldali security headerek middleware-ben:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`
  - API route-okra CSP: `default-src 'none' ...`
- Frontend oldali CSP meta policy: `frontend/index.html`.

## Sensitive data védelem
- Privát storage bucket policy már Phase 1-ben bevezetve.
- Signed URL TTL központi env-konfig: `API_SIGNED_URL_TTL_S` (default: 300s).

## Path traversal védelem
- Fájlnév-szanitizálás centralizálva: `api/routes/files.py::_sanitize_filename`.
- Tiltott értékek: üres, `.` és `..`, illetve path separator maradék.
