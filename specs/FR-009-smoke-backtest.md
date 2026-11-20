# FR-009 Smoke backtest

After every deploy, run a real 3-day backtest against the new version and poll until the job row reaches `COMPLETED` (timeout 120 s).

`FAILED`, a timeout, or a missing smoke test all count as unstable. There is no "warn" result.
