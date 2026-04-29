# Screenshot index

Six UI screenshots captured against the live Next.js ops dashboard
(`web/`) talking to the FastAPI demo router (`/api/demo/*`). Resolution
1440×900. Reproducible from a clean checkout — see Appendix A of
`docs/final_report.pdf`.

| screenshot_file | what_it_shows | why_it_matters | discussed_in_report |
|---|---|---|---|
| `ui/ui_01_landing_dashboard.png` | Operations dashboard / landing page with mixed-state workflow rows (`DELIVERED`, `READY`, `AWAITING_HUMAN`, `IN_TRANSIT`) | Surfaces the §2 architectural contract on the entry screen and gives an operator an at-a-glance triage view | §3.5 (Figure 4) |
| `ui/ui_06_yet_to_trigger.png` | A `READY` order before the workflow is started; only step 1 (`Order Created`) is `DONE`, steps 2–6 pending | Visualises the orchestrator-mediated coordination: the Coordination Hub diagram shows no agent-to-agent edges | §3.5 (Figure 5) |
| `ui/ui_02_successful_run.png` | A workflow that completed cleanly — all six timeline steps `DONE`, no escalation row | Visual confirmation of a `CLOSED_CLEAN` workflow as defined in §2.3 (CargoComply → ClearPath → LoadIQ → Supplier → Manufacturer) | §3.5 (Figure 6) |
| `ui/ui_03_shared_state_logs.png` | Forensic view of a completed workflow: swimlane, per-agent activity log strip, raw shared-state JSON | Compliance-officer view — shows `completed_agents`, `escalation_flag`, `current_stage`, `workflow_id` exactly as written by the orchestrator | §3.5 (Figure 7) |
| `ui/ui_04_hitl_awaiting_human.png` | Order with a forced route escalation: step 3 (Route Planning, ClearPath) `FAILED`; orchestrator row shows "Human gate open"; status `AWAITING_HUMAN` | The visible-to-the-user side of the same containment behaviour evidenced in the GOV-01 / ESC-01 traces | §3.5 (Figure 8) |
| `ui/ui_05_in_transit.png` | In-transit order — steps 1–4 done, step 5 (Shipment Execution) `RUNNING`, step 6 pending; **Mark delivered** button enabled | Carrier-confirmation step is deliberately gated to the human in the loop — no autonomous closure | §3.5 (Figure 9) |
