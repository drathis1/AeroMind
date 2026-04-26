# Individual reflection — Tina Sibbal

**Course:** Agentic Systems Studio · Track A: Technical Build
**Project:** AeroMind — AI Operations Brain for Air Cargo
**Phase:** 3

## What I owned

CargoComply (the compliance agent), the LLM-as-judge, the audit
hash chain, and the database schema. So basically most of the
"trust layer" of the system — the pieces that have to be right
because an ops manager is going to rely on them to make a legal
decision. I also wrote `tests/test_audit_chain.py` and the
`test_judge_flags_ungrounded` test.

Looking back, I think the reason CargoComply is the agent I owned
is that I was the most paranoid about what it would do. The other
two agents (LoadIQ, ClearPath) are about efficiency. CargoComply is
about *not breaking the law*. If LoadIQ picks a slightly worse
load plan, cargo leaves a few minutes late. If CargoComply approves
a shipment that should have been held for sanctions screening,
that's a real violation. So I kept pushing for stricter grounding
rules, more explicit source citations, and the LLM-as-judge.
Sometimes the team thought I was being too careful. I think it's
the one place in the project where being too careful was the right
call.

## What I learned

The grounding trick was bigger than I thought it would be. For a
while I was writing prompts that said "please cite your sources"
and hoping the LLM would do the right thing. It mostly does.
Mostly isn't good enough for compliance. The real fix was putting
`source_chunk_id` into the `ComplianceStatement` pydantic model as
a required-ish field, and then making the judge flag anything with
`source_chunk_id=None`. Now I don't have to trust the LLM at all.
The structure itself enforces the rule. That was a lightbulb moment
for me about how to design safety into agentic systems — don't rely
on the model to behave, rely on the shape of the data it has to
produce.

The hash chain was a rabbit hole. The code is 46 lines. But I lost
a whole afternoon to a weird bug where verify_chain kept failing
on chains I knew were clean. It turned out Python was serializing
a dict with different key orders depending on how I constructed it,
and the SHA-256 was picking that up as a change. Fixed with
`sort_keys=True` and explicit `separators=(",",":")`. That one
line is the difference between a hash chain and a pseudo-hash
chain. If you ever read a tutorial that leaves out the
canonicalization step, the tutorial is wrong.

The governance SQL views were the thing I didn't expect to enjoy
but did. Writing out `v_governance_blast_radius`,
`v_governance_dg_breaches`, `v_tool_violation_rate` forced me to
think about what an ops manager actually wants to see. Rate of tool
violations per hour. Number of DG breach attempts this week. Not
raw rows. *Aggregates with meaning.* Smridhi ended up building the
governance strip in the UI basically from the shape of those three
views. That was a fun moment where design and data model lined up
without us having to negotiate it.

## What I would change

Schema versioning on audit rows. Right now if I ever change the
shape of `decision_payload` — say I add a new field — every old
hash in the chain becomes invalid. That's correct in the strict
tamper-detection sense, but it's painful for real-world schema
evolution. A `schema_version` column plus a versioned canonicalizer
would let us evolve without breaking historical verification. I've
since seen this pattern in production-grade audit logs (the people
who wrote the AWS QLDB SDK definitely thought about this) and I
wish I'd baked it in from the start. Next project I'd treat
canonicalization + versioning as step one of any append-only log.

Also: I should have written more unit tests for the judge's
heuristics. The three I wrote (`_ungrounded`, `_pareto_dominated`,
`_load_coverage_fail`) all have one positive test and no negative
test. I got lucky that they work. Next time I'd write the negative
cases too — the "this should NOT flag" counter-examples — because
that's where false positives come from.
