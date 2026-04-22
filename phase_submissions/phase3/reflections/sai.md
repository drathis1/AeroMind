# Individual reflection — Sai Karthik

**Course:** Agentic Systems Studio · Track A: Technical Build
**Project:** AeroMind — AI Operations Brain for Air Cargo
**Phase:** 3

## What I owned

LoadIQ, the tool registry, the FastAPI app, and the Docker Compose
setup. Basically a lot of the plumbing. LoadIQ itself ended up
relatively short — the interesting logic is in how placements map
to ULDs and whether weight/balance trips — but the supporting stuff
around it (the allowlist, the API surface, making the whole thing
actually runnable from a clean checkout) took way longer than the
agent code did.

I also did most of the evaluation-capture scripting with Dhiksha. The
`eval/capture_traces.py` thing started as me just wanting to stop
re-generating JSON by hand every time a test changed. It turned into
one of the things I'm most proud of from this project because it
made every piece of evidence reproducible on somebody else's
machine, which was not a given earlier.

## What I learned

The allowlist. I genuinely did not think this was going to be
interesting when Dhiksha first brought it up. It seemed like a
bureaucratic thing to add. But when I actually wrote out the explicit
deny reasons — `CARGOCOMPLY_BOOKING_FORBIDDEN`,
`CREW_NOTIFY_WRITE_LOCK`, `DG_LOCK_BREACH`, `BLAST_RADIUS_PENDING` —
it forced me to name every way an agent could misbehave. That
naming exercise was the actual design work. The code fell out of it
in about an hour. I've been thinking about how often "security
controls" in systems I've built before were actually just `if
not allowed: raise` with no useful reason string attached. You can't
audit those. You can audit these.

Second thing. I lost more time than I want to admit to the FastAPI +
asyncpg + SQLAlchemy async combination. At one point the demo API
was crashing every time a workflow ran because the session was
getting closed before the judge finished writing. That's when I
separated the demo pipeline (in-memory) from the real `/v1/workflows/run`
endpoint (needs DB). Which in hindsight is the right call anyway —
a reviewer shouldn't have to `docker-compose up` to click around the
UI — but it took pain to arrive at.

Third thing. I underestimated how much of "the product" is the API
shape. Until I had `POST /v1/workflows/run` returning a clean JSON
response, the project was basically a pile of Python files with
tests. Once the API existed, everything else snapped into place:
the UI could talk to it, the traces could be captured against it,
the screenshots all route through it. Ops people don't see a
LangGraph `StateGraph`, they see a response body.

## What I would change

The blast-radius cap. We ship it as a single integer (default 15)
that counts every commit the same. A ground-crew notification
shouldn't weigh the same as a booking amendment. I flagged this as
Known Limitation #5 in the README but really I should have just
done it. A `dict[tool_name, cost]` with a weighted sum is like 20
lines of code, and the current implementation makes one of our
boundary tests feel artificial because a cap of 1 is really a cap
of "at most one real side-effect." Next time I'd do the weighted
version first and the blunt integer only as a fallback when no
weights are configured.

Also — write the integration tests earlier. We have five `SKIPPED`
cases in the evaluation matrix because they need a live DB and we
didn't get `docker-compose up && pytest --integration` working until
the last week. That's on me.
