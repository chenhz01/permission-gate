#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""permission-gate — least-privilege surface audit for AI agent tool permissions.

Static analysis only. Reads a tool manifest (tools x operations) and a
permission policy (allow/deny rules), enumerates the (tool, operation)
surface, classifies every pair as allowed / denied / unreviewed, and scores
the over-permission surface. No network, no command execution.
"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")
except Exception:
    pass

RISK_WEIGHTS = {"exec": 4, "write": 3, "network": 3, "read": 1}

VERSION = "0.1.1"


class AuditError(Exception):
    """Raised for any input problem that should map to exit code 2."""


def parse_rule(entry):
    """Parse a 'tool:op' policy entry. Returns (tool, op); either may be '*'."""
    if not isinstance(entry, str):
        raise AuditError("policy entries must be strings, got %r" % (entry,))
    parts = entry.split(":")
    if len(parts) != 2:
        raise AuditError("invalid policy entry %r: expected 'tool:op'" % (entry,))
    tool, op = parts
    if tool == "" or op == "":
        raise AuditError("invalid policy entry %r: empty segment" % (entry,))
    return tool, op


def rule_matches(rule, tool, op):
    rt, ro = rule
    return (rt == "*" or rt == tool) and (ro == "*" or ro == op)


def rule_covered_by(sub, sup):
    """True if rule `sup` covers (is at least as broad as) rule `sub`."""
    st, so = sub
    ut, uo = sup
    return (ut == "*" or ut == st) and (uo == "*" or uo == so)


def audit(manifest, policy):
    """Core audit. Returns a report dict. Raises AuditError on bad shapes."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tools"), list):
        raise AuditError("manifest must be an object with a 'tools' list")
    if not isinstance(policy, dict) or not isinstance(policy.get("allow"), list) \
            or not isinstance(policy.get("deny"), list):
        raise AuditError("policy must be an object with 'allow' and 'deny' lists")

    pairs = []
    seen = set()
    for tool in manifest["tools"]:
        if not isinstance(tool, dict) or "name" not in tool or "ops" not in tool:
            raise AuditError("each tool needs 'name' and 'ops'")
        ops = tool["ops"]
        if not isinstance(ops, list):
            raise AuditError("tool %r: 'ops' must be a list" % (tool.get("name"),))
        for op in ops:
            if not isinstance(op, str) or op == "":
                raise AuditError("tool %r: operation must be a non-empty string"
                                 % (tool.get("name"),))
            key = (tool["name"], op)
            if key in seen:
                continue
            seen.add(key)
            pairs.append({"tool": key[0], "op": key[1],
                          "weight": RISK_WEIGHTS.get(key[1], 2)})

    allow = [parse_rule(e) for e in policy["allow"]]
    deny = [parse_rule(e) for e in policy["deny"]]

    allowed, denied, unreviewed = [], [], []
    for p in pairs:
        tool, op = p["tool"], p["op"]
        if any(rule_matches(r, tool, op) for r in deny):
            p["status"] = "denied"
            denied.append(p)
        elif any(rule_matches(r, tool, op) for r in allow):
            p["status"] = "allowed"
            allowed.append(p)
        else:
            p["status"] = "unreviewed"
            unreviewed.append(p)

    total = len(pairs)
    if total:
        surface_pct = round(100.0 * len(unreviewed) / total, 1)
        w_all = sum(p["weight"] for p in pairs)
        w_un = sum(p["weight"] for p in unreviewed)
        risk_weighted = round(100.0 * w_un / w_all, 1) if w_all else 0.0
    else:
        surface_pct, risk_weighted = 0.0, 0.0
    score = round(100.0 - risk_weighted, 1)

    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 50 else "D"

    redundant = []
    for a in allow:
        for b in allow:
            if a != b and a not in redundant and rule_covered_by(a, b) and a != b:
                if (a[0], a[1]) != ("*", "*") or b == ("*", "*"):
                    redundant.append(a)
                    break

    recs = []
    for p in sorted(unreviewed, key=lambda x: -x["weight"])[:5]:
        recs.append("decide: allow or deny '%s:%s' (weight %d)"
                    % (p["tool"], p["op"], p["weight"]))
    for r in redundant[:5]:
        recs.append("remove redundant allow '%s:%s' (covered by a broader rule)"
                    % (r[0], r[1]))
    if not recs and total:
        recs.append("policy surface is fully explicit; keep it in sync with the manifest")

    return {
        "schema": "permission-gate/v1",
        "total_pairs": total,
        "allowed": len(allowed),
        "denied": len(denied),
        "unreviewed": len(unreviewed),
        "surface_pct": surface_pct,
        "risk_weighted_surface_pct": risk_weighted,
        "score": score,
        "grade": grade,
        "unreviewed_pairs": [{"tool": p["tool"], "op": p["op"], "weight": p["weight"]}
                             for p in sorted(unreviewed, key=lambda x: (-x["weight"], x["tool"], x["op"]))],
        "redundant_allows": ["%s:%s" % r for r in redundant],
        "recommendations": recs,
    }


def _load_json(path, what):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise AuditError("cannot read %s file: %s" % (what, e))
    except ValueError as e:
        raise AuditError("%s file is not valid JSON: %s" % (what, e))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="permission-gate",
        description="Score the over-permission surface of an AI agent tool policy (static, offline).")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    sub = parser.add_subparsers(dest="cmd")

    p_audit = sub.add_parser("audit", help="audit a manifest against a policy")
    p_audit.add_argument("--manifest", required=True, help="tool manifest JSON (tools x ops)")
    p_audit.add_argument("--policy", required=True, help="permission policy JSON (allow/deny)")
    p_audit.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p_audit.add_argument("--min-score", type=int, default=None,
                         help="exit 1 if score falls below this threshold")

    args = parser.parse_args(argv)
    if args.cmd != "audit":
        parser.print_usage(sys.stderr)
        return 2
    try:
        manifest = _load_json(args.manifest, "manifest")
        policy = _load_json(args.policy, "policy")
        report = audit(manifest, policy)
    except AuditError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print("permission-gate report")
        print("  pairs: %d  allowed: %d  denied: %d  unreviewed: %d"
              % (report["total_pairs"], report["allowed"],
                 report["denied"], report["unreviewed"]))
        print("  surface: %s%%  risk-weighted: %s%%  score: %s  grade: %s"
              % (report["surface_pct"], report["risk_weighted_surface_pct"],
                 report["score"], report["grade"]))
        for r in report["recommendations"]:
            print("  - %s" % r)

    if args.min_score is not None and report["score"] < args.min_score:
        print("error: score %s below required minimum %d" % (report["score"], args.min_score),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
