# Databricks Agent Eval Case Study

A bounded case study on prompt-injection controls for tool-using agents, run on
[AgentDojo](https://github.com/ethz-spylab/agentdojo) with evidence recorded in
Databricks (MLflow, Delta).

**Question:** which controls reduce prompt-injection risk while preserving
legitimate task completion, at what cost and latency, and do the benefits
survive a model swap?

Status: setup. No benchmark runs or model selection completed yet.

## Layout

| Path | Contents |
|---|---|
| `databricks-agent-assurance/` | Implementation (added in v0) |
| `prereg/ledger.csv` | Pre-registration ledger: SHA-256 hashes of hypotheses, committed before each run |
| `scripts/prereg.py` | Registers and verifies hypothesis hashes |

## Pre-registration

Each hypothesis is written privately, hashed, and the hash is committed and
pushed **before** the experiment runs. When results are published, the
hypothesis text can be checked against the ledger:

```bash
python scripts/prereg.py verify <file> --id <entry-id>
```

The write-up will be linked here when published.

This is not a safety certification. Results apply only to the tested tasks,
models, and configurations.
