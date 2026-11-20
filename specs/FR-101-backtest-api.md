# FR-101 Backtest API

- `POST /backtest` accepts `{index_id, days}` (1 to 30 days) and returns `202` with `{job_id, status: QUEUED}`.
- `GET /backtest/{job_id}` returns the job row. Status moves `QUEUED -> RUNNING -> COMPLETED`, or `FAILED` with an `error`.
- Unknown job ids return `404`.
- Job rows live only in the calc engine's own table `calc_backtest_job` (architecture rule A1).
