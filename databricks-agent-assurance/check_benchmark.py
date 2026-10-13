"""Check that the installed AgentDojo matches benchmark_manifest.json.

Run before any experiment. Exits non-zero on the first mismatch.

Usage:
    python check_benchmark.py
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from importlib.metadata import version
from pathlib import Path

import agentdojo
from agentdojo.task_suite.load_suites import get_suite

MANIFEST = json.loads((Path(__file__).parent / "benchmark_manifest.json").read_text(encoding="utf-8"))
CANARY = "<CANARY-email_events_injection>"


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'OK  ' if ok else 'FAIL'} {label}{f' ({detail})' if detail else ''}")
    if not ok:
        sys.exit(1)


def main() -> None:
    m = MANIFEST
    installed = version("agentdojo")
    check("agentdojo version", installed == m["agentdojo"]["package_version"], installed)

    pkg = Path(agentdojo.__file__).parent
    for rel, expected in m["source_sha256"].items():
        actual = hashlib.sha256((pkg / rel).read_bytes()).hexdigest()
        check(f"sha256 {rel}", actual == expected)

    suite = get_suite(m["benchmark_version"], m["suite"])
    user_task = suite.get_user_task_by_id(m["user_task"]["id"])
    check("user task ground truth", user_task.GROUND_TRUTH_OUTPUT == m["user_task"]["ground_truth_output"])
    strict = inspect.signature(type(user_task).utility).parameters["strict"].default
    check("utility is strict by default (inbox must be unchanged)", strict is True)

    injection_task = suite.get_injection_task_by_id(m["injection_task"]["id"])
    module = type(injection_task).__module__
    check("injection task source module", module == m["injection_task"]["source_module"], module)
    check("injection task recipient", injection_task._RECIPIENT == m["injection_task"]["recipient"])

    # The ground-truth search must return the email holding the injection slot,
    # otherwise attacked runs that follow the expected path would never see the attack.
    env = suite.load_and_inject_default_environment({m["injection_vector"]["id"]: CANARY})
    calls = user_task.ground_truth(env)
    check("ground-truth search query", calls[0].args.get("query") == m["user_task"]["ground_truth_search_query"])
    hits = env.inbox.search_emails(calls[0].args["query"])
    hit = next((e for e in hits if e.id_ == m["injection_vector"]["email_id"]), None)
    check("ground-truth search reaches injected email", hit is not None and CANARY in hit.body,
          f"email {m['injection_vector']['email_id']}")

    print("All checks passed.")


if __name__ == "__main__":
    main()
