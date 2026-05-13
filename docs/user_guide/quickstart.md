# EIBO Quickstart Guide

> Get from zero to your first workforce optimization simulation in under 5 minutes.

---

## What You Need Before Starting

- A running EIBO instance (see [Deployment Guide](../admin_guide/deployment.md))
- A user account with at least **Analyst** role
- A modern browser (Chrome 110+, Firefox 115+, Edge 110+)

If you don't have an account yet, ask your EIBO administrator.

---

## Step 1: Open the Platform

Navigate to your EIBO URL (e.g. `http://localhost:8501`). You'll land on the **Info** page with two views:

- **Business View** — plain-language explanation of what the platform does, ROI calculator, and a guided tour of each module.
- **Engineering View** — architecture diagrams, algorithm descriptions, performance benchmarks.

Start with Business View if this is your first time. Engineering View is useful when evaluating the platform technically or explaining it to a tech team.

---

## Step 2: Load Demo Data

EIBO ships with three fully synthetic demo organizations so you can explore every feature without uploading real data.

1. In the **left sidebar**, confirm **Use demo data** is toggled on (it is by default).
2. Choose a **Scenario**:
   - **A — Growing Company**: Rapid headcount expansion, skills gaps forming.
   - **B — Restructuring**: Budget pressure, overlapping roles across teams.
   - **C — Merger Integration**: Two org units recently combined, collaboration networks not yet connected.
3. Choose an **Org size**: Small (50 employees), Medium (500), or Large (5,000).
4. Click **Dashboard** in the navigation.

The dashboard loads immediately — no database setup required.

---

## Step 3: Understand the Dashboard

The Dashboard answers: *Where is our budget going, and where is our critical talent?*

Key panels:

| Panel | What it shows |
|---|---|
| Budget Allocation | Spend by department, with role-level breakdown |
| Impact Score Distribution | How talent impact is spread across the org |
| Top Organizational Nexuses | Employees whose departure would most fragment collaboration |
| Team Fragility | Departments with high dependency on a few individuals |
| Attrition Risk Heatmap | Departments with the highest retention risk concentration |

Hover over any chart element for details. Click a department name to jump to the **Drill-Down** view for that team.

---

## Step 4: Run Your First Simulation

Click **Simulation** in the sidebar.

1. **Set the available budget**: Use the slider to set what percentage of current spend you want to work with (50%–120%). The platform recalculates in real time.
2. **Review the optimization result**: The model suggests which employees to retain to maximize organizational impact within your budget. "Suggested Retention" means the model recommends keeping this person; "Not Retained in Simulation" means the budget doesn't cover them under current constraints.
3. **Apply manual overrides**: Every suggestion can be overridden. Click the toggle next to any employee and add an annotation (e.g., "Critical project until Q3"). The model recalculates around your override.
4. **Compare scenarios**: Save the current simulation as a named scenario, then adjust the budget and save another. Use the **Scenarios** tab to compare them side by side.

> **Remember**: The platform *suggests*, you *decide*. Every output is a starting point for a human conversation, not a verdict.

---

## Step 5: Explore Predictive Analytics

Click **Predictive** in the sidebar.

- **Attrition Risk**: Each employee shows a calibrated probability of voluntary departure within 12 months, with the specific drivers listed (engagement trend, tenure, market salary gap, etc.).
- **Budget Forecast**: 12-month budget projection with confidence intervals. See how budget changes in one department ripple across the org.
- **Early Warning System**: Configurable thresholds that trigger alerts when attrition risk clusters appear in a department.

All predictions include **SHAP explanations** — expand any prediction card to see which factors contributed most and by how much.

---

## Step 6: Drill Into a Team

Click **Drill-Down** in the sidebar, or click any department name in the Dashboard.

The drill-down moves from **Org → Department → Team → Individual**:

1. Select a department from the left panel.
2. Click a team to see its collaboration network graph. Node size = impact score; edge thickness = collaboration frequency. Employees flagged as **Organizational Nexus** have a badge.
3. Click any employee node to open their full profile:
   - Radar chart across all 4 impact dimensions (performance, centrality, skills, replacement cost)
   - Historical performance trend
   - Skill matrix with criticality ratings
   - Current attrition risk with SHAP breakdown
   - Simulation status (Suggested Retention / Not Retained) with override capability

---

## Step 7: Upload Real Data (When Ready)

When you're ready to move beyond demo data:

1. Toggle off **Use demo data** in the sidebar.
2. Go to **Dashboard** and use the **Upload** panel to provide your HR data file (CSV or Excel).
3. The platform validates the file format and flags any issues before ingestion.
4. Once ingested, all analysis runs on your real data with the same privacy controls applied to demo mode.

Contact your administrator if your organization uses a supported HRIS (Workday, SAP SuccessFactors, BambooHR) — direct integration may already be configured.

---

## Common Questions

**Q: Can I undo a simulation override?**
Yes. Click the override toggle again to revert to the model's suggestion. The annotation is preserved in the audit log.

**Q: Who can see salary data?**
Visibility depends on your role. Analysts see salary ranges, not exact figures. Managers see exact figures for their department. Executives see org-wide. Viewers see no salary data.

**Q: Is my uploaded data shared externally?**
No. EIBO runs entirely on your infrastructure. No data leaves your environment.

**Q: How often are the models retrained?**
Attrition and impact models retrain monthly by default, or when data drift is detected. Administrators can trigger manual retraining from the **Admin** page.

**Q: What does "Organizational Nexus" mean?**
An employee whose betweenness centrality in the collaboration network exceeds 0.7 — meaning a disproportionate share of information flow and cross-team connections passes through them. Their departure would fragment the network.

---

## Getting Help

- **In-app tooltips**: Hover over any metric name for a plain-language explanation.
- **Info page**: Click **Info** in the sidebar → Engineering View for technical depth.
- **Administrator**: For account issues, data ingestion, or HRIS integration.
- **GitHub Issues**: [Report a bug or request a feature](https://github.com/your-org/eibo/issues)

---

*EIBO — Employee Impact & Budget Optimizer · OPB AI Mastery Lab*
