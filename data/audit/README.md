# Audit data operating rules

Use append-only JSONL events with hash chaining for material actions. Do not edit historical events. If a correction is required, append a compensating event that references the prior event hash.
