"""Background task execution (PROJECT.md section 27).

Long-running tasks must not block a single open HTTP request; a worker
process here will eventually pull tasks off Redis/PostgreSQL and drive the
orchestrator loop. Not implemented yet -- this package is a placeholder for
that future increment.
"""
