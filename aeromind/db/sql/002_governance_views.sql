CREATE OR REPLACE VIEW v_governance_blast_radius AS
SELECT
  COUNT(*) FILTER (WHERE event_type = 'BLAST_RADIUS_CAP') AS blast_events,
  COUNT(*) AS total_events,
  CASE WHEN COUNT(*) = 0 THEN 0
       ELSE COUNT(*) FILTER (WHERE event_type = 'BLAST_RADIUS_CAP')::float / COUNT(*)
  END AS blast_rate
FROM orchestrator_events;

CREATE OR REPLACE VIEW v_governance_dg_breaches AS
SELECT COUNT(*) AS dg_lock_breach_attempts
FROM orchestrator_events
WHERE event_type = 'DG_LOCK_BREACH_ATTEMPT';

CREATE OR REPLACE VIEW v_tool_violation_rate AS
SELECT COUNT(*) AS violations_last_200 FROM governance_violations;
