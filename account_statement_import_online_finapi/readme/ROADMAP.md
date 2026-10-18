- **Renew consent** first tries the legacy `PUT /api/webForms/bankConnectionUpdate` endpoint. That endpoint was removed
  from Web Form 2.0 and answers HTTP 405 on the live API, so the wizard falls back to a fresh import web form. The user
  reaches the same result; it costs one wasted round trip. Migrate the wizard to the `POST /api/tasks/backgroundUpdate`
  task flow with `WEB_FORM_REQUIRED` handling, the mechanism the scheduled pull already uses.
- A pull is split into one statement period per day by the framework, and the refresh lookback widens that window, so a
  scheduled run currently issues one `GET /transactions` call per day in the window instead of a single ranged read.
  Reads are not PSD2-limited, but this could be reduced to one call per pull.
- The Web Form background update is polled synchronously, for up to `_finapi_background_update_max_wait_seconds`.
  Consuming the finAPI `finalised` / `webFormRequired` webhook callbacks instead would take the wait out of the cron
  worker altogether; a `queue_job` dependency would be the other option.
- Make the refresh interval configurable per provider instead of the fixed six-hour throttle
  (`_finapi_min_data_update_interval_hours`), and surface finAPI's per-day access counter once exposed by the API.
- Add pending transactions via `/api/v2/pendingTransactions`.
- Encrypt `client_secret` and `finapi_refresh_token` at rest.
- Use the webhook callback to advance the wizard automatically instead of requiring the user to click "Refresh status".
- Add IP allowlisting / rate limiting for the webhook endpoint on the reverse proxy (the endpoint itself is protected by
  a shared secret).
