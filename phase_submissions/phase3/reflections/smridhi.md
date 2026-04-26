# Individual reflection — Smridhi Patwari

**Course:** Agentic Systems Studio · Track A: Technical Build
**Project:** AeroMind — AI Operations Brain for Air Cargo
**Phase:** 3

## What I owned

ClearPath (the rerouting agent), the prompt-injection filter, the
Next.js ops UI, and most of the long-form writing — the README, the
architecture diagram labels, the screenshot index, and a lot of the
Phase 2 narrative. I also captured the interaction traces into files
once Sai's capture script was in place.

Honestly my ownership felt split in half. The agent + filter work is
very "agentic systems" — disruption detection, handoff flags,
sanitizing untrusted NOTAM text — and the UI work is very
"product/design." I wasn't sure at the start how much the UI
actually mattered for grading, but by the end I'd decided it mattered
a lot. If a reviewer can't see that a workflow is paused waiting on
a human, the DG lock might as well not exist. The amber escalation
card ended up being one of the most important pieces of governance
UX in the whole system, even though it's "just" CSS.

## What I learned

Writing about the system forced me to actually understand it. I
rewrote the "Why Multi-Agent? Why Not Simpler?" section of the
README at least four times. The first draft was generic multi-agent
talk — "separation of concerns, specialized tools, parallel
execution" — and Dhiksha basically gutted it. She said none of that
was specific to AeroMind. She was right. When I rewrote it so each
of the three justifications pointed at an actual code path (ULD +
weather + compliance tool sets, the departure-window constraint,
the conditional fan-out), the section got half as long and twice as
useful. That one piece of feedback genuinely changed how I think
about technical writing. Claims that apply to "any multi-agent
system" are worth almost nothing. Claims that would break if you
changed three lines of code are the ones that matter.

The injection filter. I picked the 120-character anomalous-token
threshold by looking at a handful of NOTAM strings and making a
guess. It works. But I picked it by vibes and that still bothers
me. At one point INJ-05 (the "benign text should pass" case) broke
because I'd added `"override"` to the blocklist, which flags real
ops text like "override crew rest request." Tuning the filter
against synthetic strings is not the same as tuning against a real
corpus. I removed `"override"`, the test passed, but I'm aware I
might have just moved the false-positive surface instead of fixing
it.

The UI. I probably spent more hours than I should have on making
the escalation card visually dominant. But I think that was the
right call. The first version was a small amber banner at the top
of the page and in user testing (Tina and my roommate both looked
at it) neither of them noticed the workflow was paused. That's a
safety failure. The final version is the full-width amber card
with big text and the workflow state in plain English, and it is
impossible to miss. "Dangerous-goods cargo present — awaiting human
approval" beats `DG_LOCK_BREACH` every single time.

## What I would change

Two things. First, the injection filter thresholds need to come from
real data, not my eyeballs. Publicly posted NOTAM samples exist.
I should have downloaded a batch and calibrated the filter
empirically. I'd do that first next time and save the handful of
false positives that slipped through.

Second thing, and this is more about how I worked than the code.
I kept the UI as a side project for too long because I wasn't sure
it "counted." By the time I showed it to the team it was mostly
done and they had good ideas that would have been faster to
incorporate earlier (Tina wanted a governance metrics strip, Sai
wanted a confidence chip on each agent output — both ended up
getting added, but I had to redo some CSS). Next time I'd push a
UI skeleton out in week one even if it looks ugly.
