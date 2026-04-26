# Individual reflection — Dhiksha Rathis

**Course:** Agentic Systems Studio · Track A: Technical Build
**Project:** AeroMind — AI Operations Brain for Air Cargo
**Phase:** 3

## What I owned

I ended up being the person who held the middle of the system. The
orchestrator, the routing logic, the evaluation plan. On paper that's
`aeromind/orchestrator/graph.py`, `routing.py`, the big
`Evaluation plan.md` file with the 35 scenarios, and the two tests in
`test_orchestrator_unit.py`. In reality it felt more like "the thing
that everyone else's code has to plug into." Every time Sai changed
the allowlist or Smridhi tweaked ClearPath's handoff flag or Tina
added a new field to CargoComply, it showed up in the orchestrator
first, and I had to decide whether the change was safe or whether I
needed to push back.

I also co-owned the test plan with Sai. The matrix got big honestly
faster than I expected — we started with maybe 10 scenarios and by
the time we'd argued through all the edge cases we were at 35. Some
of those, like the stress and live-LLM ones, we never ran for Phase
3, and I wrote that honestly into the plan instead of quietly
dropping them.

## What I learned

Three things, though the first one I'm still kind of annoyed about.

The blast-radius cap comparator. I originally wrote it as `>=`. It
passed most of the tests. GOV-02 even passed. Then I wrote GOV-07
(the "exactly at cap should pass" case) as a boundary pair and it
immediately failed. The fix was one character — `>=` to `>` — but I
sat there for a while thinking about how much of my intuition about
"how many autonomous actions is too many" had baked in off-by-one
assumptions. Boundary tests caught something I absolutely would have
shipped otherwise, and I don't think I would have written that test
if Sai hadn't pushed for it.

Second thing. The rule "agents propose, the orchestrator commits"
sounds so obvious that it felt stupid to write it down in Phase 1.
But every single governance case in Phase 3 is literally just that
rule showing up again. DG lock, blast radius, the allowlist — they
all work because the agent doesn't actually *do* the thing, it just
asks, and the orchestrator is the one place that decides. Once I
internalized that, a lot of decisions got simpler. Where does this
check go? In the orchestrator. Always.

Third. I used to think evaluation was a thing you did at the end.
Writing the plan early, before any of the code was real, was
actually the thing that let us catch design problems. The fact that
`WEATHER_ALERT` needed a two-phase handoff only became obvious to me
when I tried to describe E2E-02 and realized I couldn't fit the
parallel-after-reroute thing into a single sentence without
contradicting myself.

## What I would change

Honestly the DG lock thing bugs me. Right now if the DG lock fires,
the commit gets zeroed but the workflow still ends `CLOSED_CLEAN`.
That matches what the code does, and we wrote it up that way in the
failure analysis, but if I was starting over I'd have made DG lock
force `AWAITING_HUMAN` on day one. It's a safety control. A silent
pass with a suppressed side-effect is not what a safety control
should look like in the state dump. We wrote it in as a next step
but I wish I'd caught it in Phase 2.
