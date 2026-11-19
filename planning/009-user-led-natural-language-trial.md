# 009: User-led natural-language trial

**Status:** Not started. The enabling work in
[008](008-project-lifecycle-and-interactive-iteration.md) is complete; see
[008 results](008_results.md). This brief captures the agreed trial direction,
not an instruction to start model calls.

## Scope

Try the existing natural-language collage workflow with the user driving
requests, reacting to previews, and deciding when to continue or stop.
Keep out-of-band observations to Copilot separate from messages sent to the
collage agent. Vision, UI, and cloud hosting remain outside this trial.

## Model use

No fixed trial-wide call budget or shared allowance is required: the user
controls how far the trial goes. Retain the application's existing per-message
call limits, per-request token/time guards, usage recording, and explicit
failure handling. This does not authorize unattended replay batches or an
autonomous retry/tuning campaign.

Record trial observations and any follow-up issues separately from 008's
completed results. Human feedback evaluates the experience; it does not
reopen the completed enabling milestone.
