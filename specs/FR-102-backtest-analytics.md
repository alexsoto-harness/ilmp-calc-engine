# FR-102 Backtest analytics

- `GET /backtest/{job_id}/analytics` returns `period_return_pct` for a `COMPLETED` job: `(index_level / 1000 - 1) * 100`, rounded to 4 places.
- Jobs that are not `COMPLETED` return `409`. Unknown jobs return `404`.
