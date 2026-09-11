"""Background task execution (PROJECT.md section 27).

Long-running tasks must not block a single open HTTP request. A worker
process here will poll the PostgreSQL tasks table (SELECT ... FOR UPDATE
SKIP LOCKED) and drive the orchestrator loop. Not implemented yet --
this package is a placeholder for that future increment.
"""
