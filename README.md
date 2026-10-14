# Databricks Agent Eval Case Study

A bounded case study on prompt-injection controls for tool-using agents, run on
[AgentDojo](https://github.com/ethz-spylab/agentdojo) with evidence recorded in
Databricks (MLflow, Delta).

**Question:** to protect a tool-using agent from prompt injection, should you
buy safety (an expensive frontier model that resists on its own) or build it
(a free open-weight model behind a hard block on risky tools)? Compared on
leaks, correct answers, and cost per correct answer, across three models:
a budget closed model, a frontier closed model, and a free open-weight model.

Status: setup. Models selected; no benchmark runs yet.

## Layout

| Path | Contents |
|---|---|
| `databricks-agent-assurance/` | Implementation: pinned AgentDojo, benchmark manifest and check |
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
