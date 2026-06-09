"""Knowledge Graph & Institutional Memory Mapping for EIBO — Sprint 11.

Builds a knowledge ownership graph over the workforce:
  - 23 knowledge domains, broader than skills (legacy systems, regulatory
    ownership, client relationships, etc.)
  - Single-Knowledge-Holder (SKH) detection per domain
  - knowledge_loss_score per employee: weighted sum of domain criticality
    lost when that employee departs
  - Transfer roadmap: successor recommendations ranked by urgency
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np

from backend.services.data_service import get_org

# ── Knowledge domain taxonomy ──────────────────────────────────────────────
# Each domain has: id, display name, criticality (0-1), department affinities.
# Employees in an affinity dept have higher assignment probability.

_DOMAINS = [
    {"id": "kd_legacy_arch",   "name": "Legacy System Architecture",      "criticality": 0.95, "affinity": ["Engineering", "Technology"]},
    {"id": "kd_security",      "name": "Security Policies & Secrets Mgmt","criticality": 0.92, "affinity": ["Engineering", "Risk & Compliance"]},
    {"id": "kd_hipaa",         "name": "HIPAA / HL7 Integration Logic",   "criticality": 0.90, "affinity": ["Clinical", "Risk & Compliance"]},
    {"id": "kd_reg_proc",      "name": "Regulatory Process Ownership",    "criticality": 0.90, "affinity": ["Risk & Compliance", "Finance"]},
    {"id": "kd_deploy",        "name": "Production Deploy Runbooks",      "criticality": 0.88, "affinity": ["Engineering", "Technology"]},
    {"id": "kd_integration",   "name": "System Integration Architecture", "criticality": 0.87, "affinity": ["Engineering", "Technology"]},
    {"id": "kd_incident",      "name": "Incident Response Playbooks",     "criticality": 0.85, "affinity": ["Engineering", "Operations"]},
    {"id": "kd_client_rel",    "name": "Strategic Client Relationships",  "criticality": 0.85, "affinity": ["Sales", "Product"]},
    {"id": "kd_data_gov",      "name": "Data Governance & Lineage",       "criticality": 0.85, "affinity": ["Engineering", "Operations"]},
    {"id": "kd_fin_close",     "name": "Financial Close Process",         "criticality": 0.82, "affinity": ["Finance"]},
    {"id": "kd_payroll_arch",  "name": "Payroll & Benefits Architecture", "criticality": 0.80, "affinity": ["HR & People", "Finance"]},
    {"id": "kd_ml_ownership",  "name": "ML Model Ownership & Tuning",     "criticality": 0.80, "affinity": ["Engineering", "Product"]},
    {"id": "kd_vendor_rel",    "name": "Key Vendor Relationships",        "criticality": 0.80, "affinity": ["Operations", "Sales"]},
    {"id": "kd_cost_model",    "name": "Cost Modeling & Scenarios",       "criticality": 0.76, "affinity": ["Finance", "Operations"]},
    {"id": "kd_roadmap_ctx",   "name": "Product Roadmap Context",         "criticality": 0.75, "affinity": ["Product"]},
    {"id": "kd_sales_hist",    "name": "Sales Process & Deal History",    "criticality": 0.75, "affinity": ["Sales"]},
    {"id": "kd_contracts",     "name": "Contract Negotiation History",    "criticality": 0.72, "affinity": ["Sales", "Operations"]},
    {"id": "kd_budget_proc",   "name": "Budget Process Ownership",        "criticality": 0.70, "affinity": ["Finance", "Operations"]},
    {"id": "kd_hr_compliance", "name": "HR Compliance Processes",         "criticality": 0.70, "affinity": ["HR & People"]},
    {"id": "kd_ops_sla",       "name": "Operational SLA Agreements",      "criticality": 0.78, "affinity": ["Operations", "Sales"]},
    {"id": "kd_data_sci",      "name": "Data Science Methodologies",      "criticality": 0.78, "affinity": ["Engineering", "Product"]},
    {"id": "kd_mkt_brand",     "name": "Brand Voice & Campaign History",  "criticality": 0.65, "affinity": ["Marketing"]},
    {"id": "kd_onboarding",    "name": "Onboarding & Training IP",        "criticality": 0.60, "affinity": ["HR & People"]},
]

_DOMAIN_INDEX = {d["id"]: i for i, d in enumerate(_DOMAINS)}

_PROF_BASE = {
    "junior": 2.1, "mid": 2.8, "senior": 3.5,
    "lead": 3.9, "director": 4.1, "exec": 4.4,
}

# Assignment probability by dept affinity match
_PROB_AFFINITY = 0.38
_PROB_DEFAULT  = 0.04

# Minimum proficiency to "count" as a qualified holder for a domain
_PROF_THRESHOLD = 3.0

# Full-coverage target: at least this many qualified holders → coverage = 100%
# Scales with org size in build_knowledge_data()
_FULL_COVERAGE_BASE = 3


def build_knowledge_data(scenario: str, size: str) -> dict:
    org = get_org(scenario.upper(), size.lower())
    df  = org.employees.copy().reset_index(drop=True)
    n   = len(df)
    nd  = len(_DOMAINS)

    rng = np.random.default_rng(42)

    # ── Build proficiency matrix (n_employees × n_domains) ────────────────
    # Step 1: ownership mask — does employee i own domain d?
    depts = df["department"].tolist()
    seniorties = df["seniority_level"].tolist()

    ownership = np.zeros((n, nd), dtype=bool)
    proficiency = np.zeros((n, nd), dtype=float)

    for di, dom in enumerate(_DOMAINS):
        affinity_set = set(dom["affinity"])
        for ei in range(n):
            prob = _PROB_AFFINITY if depts[ei] in affinity_set else _PROB_DEFAULT
            if rng.random() < prob:
                ownership[ei, di] = True
                base = _PROF_BASE.get(seniorties[ei], 2.8)
                raw  = base + rng.normal(0, 0.55)
                proficiency[ei, di] = float(np.clip(round(raw, 1), 1.0, 5.0))

    # ── Qualified holders per domain ───────────────────────────────────────
    qualified = proficiency >= _PROF_THRESHOLD  # (n, nd) bool

    # ── SKH detection ──────────────────────────────────────────────────────
    # domain_holder_count[di] = number of qualified holders
    domain_holder_counts = qualified.sum(axis=0)  # (nd,)

    # skh_mask[ei, di] = True if ei is sole qualified holder of di
    skh_mask = qualified & (domain_holder_counts[np.newaxis, :] == 1)  # (n, nd)

    # ── knowledge_loss_score per employee ──────────────────────────────────
    # For each domain d owned by employee i: contribution =
    #   criticality(d) × max(0, 1 − coverage_ratio_after_loss)
    # coverage_ratio_after_loss = (holder_count_without_i) / 2
    # (2 = full-coverage target: at least 2 qualified holders)

    criticalities = np.array([d["criticality"] for d in _DOMAINS])  # (nd,)

    # Full-coverage target scales with org size so scores stay meaningful
    # for medium (500) and large (1000+) orgs
    full_cov = max(_FULL_COVERAGE_BASE, int(np.sqrt(n) / 3))

    kl_scores = np.zeros(n, dtype=float)
    for ei in range(n):
        owned_domains = np.where(ownership[ei])[0]
        score = 0.0
        for di in owned_domains:
            holders_without = domain_holder_counts[di] - (1 if qualified[ei, di] else 0)
            coverage_after  = min(holders_without / full_cov, 1.0)
            score += criticalities[di] * max(0.0, 1.0 - coverage_after)
        kl_scores[ei] = score

    # Normalise 0-100
    kl_max = kl_scores.max() if kl_scores.max() > 0 else 1.0
    kl_scores_norm = (kl_scores / kl_max * 100).round(1)

    # ── Domain summary ─────────────────────────────────────────────────────
    employee_ids   = df["employee_id"].apply(lambda x: str(x)[:8].upper()).tolist()
    employee_names = df["full_name"].tolist()

    domain_rows = []
    for di, dom in enumerate(_DOMAINS):
        hcount  = int(domain_holder_counts[di])
        is_skh  = hcount == 1
        holders = [i for i in range(n) if qualified[i, di]]
        primary_idx = holders[0] if holders else None
        primary_name = employee_names[primary_idx] if primary_idx is not None else "—"

        # Best backup: highest proficiency among non-primary holders
        backup_name = "—"
        backup_prof = 0.0
        if hcount >= 2:
            others = [(i, proficiency[i, di]) for i in holders if i != primary_idx]
            if others:
                bk_idx, bk_prof = max(others, key=lambda x: x[1])
                backup_name = employee_names[bk_idx]
                backup_prof = bk_prof

        coverage = min(hcount / full_cov, 1.0)
        domain_rows.append({
            "domain_id":       dom["id"],
            "name":            dom["name"],
            "criticality":     dom["criticality"],
            "holder_count":    hcount,
            "is_skh":          is_skh,
            "is_uncovered":    hcount == 0,
            "primary_holder":  primary_name,
            "backup_holder":   backup_name,
            "backup_proficiency": round(backup_prof, 1),
            "coverage_ratio":  round(coverage, 2),
        })

    domain_rows.sort(key=lambda x: (-x["criticality"], -int(x["is_skh"])))

    # ── Employee rows (SKH + knowledge loss view) ──────────────────────────
    emp_rows = []
    for ei in range(n):
        skh_domains = [_DOMAINS[di]["name"] for di in range(nd) if skh_mask[ei, di]]
        owned_count = int(ownership[ei].sum())
        emp_rows.append({
            "employee_id":        employee_ids[ei],
            "full_name":          employee_names[ei],
            "department":         depts[ei],
            "seniority_level":    seniorties[ei],
            "role_title":         df.at[ei, "role_title"],
            "knowledge_loss_score": float(kl_scores_norm[ei]),
            "domain_count":       owned_count,
            "skh_domains":        skh_domains,
            "is_skh":             len(skh_domains) > 0,
        })

    emp_rows.sort(key=lambda x: -x["knowledge_loss_score"])

    # ── Transfer roadmap ───────────────────────────────────────────────────
    # Rank all domains by concentration_risk = criticality / log2(holder_count + 1).
    # This surfaces SKH domains at the top, then critical domains with few holders,
    # working correctly for small and large orgs alike.
    # Include top 20 domains by concentration_risk where holder_count ≥ 1.
    domain_concentration = []
    for di, dom in enumerate(_DOMAINS):
        hcount = int(domain_holder_counts[di])
        if hcount == 0:
            continue
        import math
        conc = dom["criticality"] / math.log2(hcount + 1)
        domain_concentration.append((di, conc))
    domain_concentration.sort(key=lambda x: -x[1])
    top_domains = [di for di, _ in domain_concentration[:20]]

    transfer_rows = []
    for di in top_domains:
        dom = _DOMAINS[di]
        hcount = int(domain_holder_counts[di])

        holders_sorted = sorted(
            [i for i in range(n) if qualified[i, di]],
            key=lambda i: -proficiency[i, di],
        )

        is_skh_domain = hcount == 1
        skh_ei = holders_sorted[0]  # primary = highest proficiency holder

        # Best successor: highest proficiency among owners who are NOT the primary
        candidates = [
            (i, proficiency[i, di])
            for i in range(n)
            if i != skh_ei and ownership[i, di]
        ]
        if not candidates:
            # Widen to same-dept employees
            dept_skh = depts[skh_ei]
            candidates = [
                (i, proficiency[i, di])
                for i in range(n)
                if i != skh_ei and depts[i] == dept_skh
            ]

        if not candidates:
            successor_name  = "No internal candidate"
            successor_prof  = 0.0
            prof_gap        = round(5.0 - 0.0, 1)
        else:
            succ_ei, succ_prof = max(candidates, key=lambda x: x[1])
            successor_name  = employee_names[succ_ei]
            successor_prof  = round(succ_prof, 1)
            prof_gap        = round(max(0.0, _PROF_THRESHOLD - successor_prof), 1)

        # Transfer investment estimate:
        # Each proficiency point gap ≈ 3 months of focused coaching × $6,000/month
        transfer_months = round(prof_gap * 3.0, 1) if prof_gap > 0 else 0.5
        transfer_cost   = round(transfer_months * 6_000)

        # Urgency = concentration risk of the domain (independent of org size)
        # = criticality × (1 / log2(holder_count + 1)), normalised so that
        # a sole holder (hcount=1) at max criticality gives urgency = 1.0
        import math
        raw_urgency = dom["criticality"] / math.log2(hcount + 1)
        max_possible = 1.0 / math.log2(2)  # hcount=1, criticality=1.0
        urgency = round(min(raw_urgency / max_possible, 1.0), 3)

        transfer_rows.append({
            "domain_id":           dom["id"],
            "domain_name":         dom["name"],
            "criticality":         float(dom["criticality"]),
            "is_skh":              bool(is_skh_domain),
            "current_holder":      employee_names[skh_ei],
            "current_holder_dept": depts[skh_ei],
            "current_proficiency": float(round(proficiency[skh_ei, di], 1)),
            "successor":           successor_name,
            "successor_proficiency": float(successor_prof),
            "proficiency_gap":     float(prof_gap),
            "transfer_months":     float(transfer_months),
            "transfer_cost":       int(transfer_cost),
            "urgency_score":       float(urgency),
        })

    transfer_rows.sort(key=lambda x: -x["urgency_score"])

    # ── Heatmap data (top 25 employees × all domains they own) ────────────
    top_emp = emp_rows[:25]
    top_emp_ids = {e["employee_id"] for e in top_emp}
    top_emp_idx = [i for i in range(n) if employee_ids[i] in top_emp_ids]

    # Filter domains to only those owned by at least one top employee
    active_domain_ids = set()
    for ei in top_emp_idx:
        for di in range(nd):
            if ownership[ei, di]:
                active_domain_ids.add(_DOMAINS[di]["id"])

    heatmap_domains = [d for d in _DOMAINS if d["id"] in active_domain_ids]
    heatmap_domains.sort(key=lambda d: -d["criticality"])

    heatmap_cells = []
    for ei in top_emp_idx:
        for di, dom in enumerate(_DOMAINS):
            if dom["id"] in active_domain_ids and ownership[ei, di]:
                heatmap_cells.append({
                    "employee_id": employee_ids[ei],
                    "domain_id":   dom["id"],
                    "proficiency": float(proficiency[ei, di]),
                    "is_skh":      bool(skh_mask[ei, di]),
                })

    # ── Summary ────────────────────────────────────────────────────────────
    n_skh_domains    = sum(1 for d in domain_rows if d["is_skh"])
    n_skh_employees  = sum(1 for e in emp_rows if e["is_skh"])
    n_uncovered      = sum(1 for d in domain_rows if d["is_uncovered"])
    avg_kl = float(np.mean([e["knowledge_loss_score"] for e in emp_rows]))

    return {
        "summary": {
            "total_domains":         len(_DOMAINS),
            "skh_domains":           n_skh_domains,
            "uncovered_domains":     n_uncovered,
            "skh_employees":         n_skh_employees,
            "avg_knowledge_loss":    round(avg_kl, 1),
            "high_risk_employees":   sum(1 for e in emp_rows if e["knowledge_loss_score"] >= 60),
        },
        "employees":          emp_rows,
        "domains":            domain_rows,
        "transfer_roadmap":   transfer_rows,
        "heatmap": {
            "employees": [
                {"employee_id": e["employee_id"], "full_name": e["full_name"],
                 "department": e["department"], "knowledge_loss_score": e["knowledge_loss_score"]}
                for e in top_emp
            ],
            "domains": [
                {"domain_id": d["id"], "name": d["name"], "criticality": d["criticality"]}
                for d in heatmap_domains
            ],
            "cells": heatmap_cells,
        },
    }
