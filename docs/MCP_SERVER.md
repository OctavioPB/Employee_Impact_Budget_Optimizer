# EIBO MCP Server

Use EIBO from Claude Desktop, Claude Code or any other [Model Context Protocol](https://modelcontextprotocol.io) client. Managers and people analysts can ask questions in plain language ("who on my team needs a retention conversation?", "what does an 80% budget do to leadership coverage?"), and the assistant answers with EIBO's analytics. Every answer respects the same role-based access rules as the platform.

> EIBO suggests; people decide. The server is read-only: it never saves a scenario, changes data or acts on a simulation.

---

## Quick start

You need Python 3.11+ and the project's dependencies (`pip install -r requirements.txt`). Replace `C:/path/to/Employee_Impact_Budget_Optimizer` with your checkout.

### Claude Code

```bash
claude mcp add eibo --scope user \
  --env EIBO_MCP_USER=U004 \
  -- python C:/path/to/Employee_Impact_Budget_Optimizer/mcp_server/__main__.py
```

Or commit a project-scoped `.mcp.json` at the repository root:

```json
{
  "mcpServers": {
    "eibo": {
      "command": "python",
      "args": ["mcp_server/__main__.py"],
      "env": { "EIBO_MCP_USER": "${EIBO_MCP_USER:-U005}" }
    }
  }
}
```

### Claude Desktop

Add this to `claude_desktop_config.json` (Settings → Developer → Edit Config), then restart Claude Desktop:

```json
{
  "mcpServers": {
    "eibo": {
      "command": "python",
      "args": ["C:/path/to/Employee_Impact_Budget_Optimizer/mcp_server/__main__.py"],
      "env": {
        "EIBO_MCP_USER": "U004",
        "EIBO_MCP_SCENARIO": "A",
        "EIBO_MCP_SIZE": "small"
      }
    }
  }
}
```

The script runs from any working directory. If `python` on your `PATH` is not the environment where you installed the requirements, use that interpreter's full path as `command`.

### Check it works

Ask the assistant: *"Use the eibo tools: who am I and what can I see?"* It should call `whoami` and report your role and departments.

---

## Identity and what each role sees

Each person runs their own server process, and the process's identity decides what it returns. Set **one** of:

| Variable | Example | Meaning |
|---|---|---|
| `EIBO_MCP_USER` | `U004` or `jordan@demo.eibo` | A user from the demo directory (`auth/rbac.py`) |
| `EIBO_MCP_ROLE` + `EIBO_MCP_DEPARTMENTS` | `manager` + `Engineering,Product` | Any role, scoped to departments. Viewer, analyst and manager roles must list departments. |

Demo users: `U002` executive (org-wide) · `U003` director (Engineering, Product) · `U004` manager (Engineering) · `U005` analyst (Engineering, Analytics) · `U006` viewer (Operations).

| | Viewer | Analyst | Manager | Director | Executive |
|---|---|---|---|---|---|
| Departments | own | own | own | all | all |
| Employee rows | yes | yes | yes | yes | yes |
| Attrition risk | – | yes | yes | yes | yes |
| Salary | hidden | band (e.g. $140k–$160k) | exact | exact | exact |
| Run simulations | – | yes | yes | yes | yes |
| Force-retain / exclude overrides | – | – | yes | yes | yes |
| Knowledge, succession, resilience | – | yes | yes | yes | yes |
| Pay equity | – | yes (bands) | yes | yes | yes |

Organization-level totals (headcount, payroll, OHI) are visible to every role. Rows for individual employees are returned only for departments in the caller's scope.

### Privacy: what reaches the LLM

Tool results are sent to the model your client uses, which may be a hosted model. EIBO's design principle is that employee data stays inside the organization, so by default:

- **Names are redacted.** Employees appear as `<role title> #<ID>` (for example `Senior Software Engineer #5AC236BE`). This also applies to names inside other results, such as successors and knowledge holders. Set `EIBO_MCP_SHARE_NAMES=1` only if your organization has approved sending names to the model provider. Viewers stay redacted regardless.
- **Salaries follow the role** (table above).
- **IDs, roles, scores and departments are always sent.** The person running the server can map an ID back to a name in the EIBO web app.

The bundled data is a synthetic demo organization. Before connecting real employee data, confirm the model provider's data-handling terms with your legal and privacy teams.

### Audit trail

Every tool call is written to the audit log (`audit_logs/audit.jsonl`, or `EIBO_MCP_AUDIT_DIR`) with the user, tool and parameters. Simulations are logged under the `simulation` category.

---

## What the assistant can do

### Tools

All tools are read-only (`readOnlyHint: true`) and return structured JSON.

| Tool | Answers | Typical user |
|---|---|---|
| `whoami` | My role, scope, what is masked, which departments exist | everyone |
| `org_overview` | Headcount, payroll vs budget, impact, nexus employees, per-department summary | everyone |
| `list_employees` | People in scope, sortable by impact, attrition risk or salary; filter by department, nexus, risk band | managers, analysts |
| `employee_profile` | One person's impact, retention driver, knowledge held (single-holder flags), pay position, mobility | managers |
| `retention_risks` | Who needs a retention conversation and why | managers |
| `simulate_budget` | The suggested plan at a budget, with coverage constraints, headcount cost and overrides | analysts, managers |
| `compare_budget_scenarios` | Side-by-side plans at up to 6 budget levels | analysts |
| `org_health` | Organizational Health Index, sub-indices, trend, department scores | everyone |
| `knowledge_risks` | Knowledge domains held by one person or nobody, transfer roadmap | managers, analysts |
| `succession_depth` | Who could step up behind each leader, and where there is no successor | managers |
| `resilience_stress_test` | Knock-on departures, cost and coverage loss for a disruption | analysts |
| `fairness_audit` | Four-fifths and chi-square flags on scores and simulated selections | analysts, legal |
| `pay_equity` | Market position, raw and adjusted pay gaps, best-return pay corrections | analysts |

Every tool takes optional `scenario` (`A`/`B`/`C`) and `size` (`small`/`medium`/`large`) arguments. The defaults come from `EIBO_MCP_SCENARIO` and `EIBO_MCP_SIZE`. The first request for the large (5,000-person) organization takes about 30 seconds; later ones are fast.

### Resources

- `eibo://guide/methodology`: how each number is produced, and its limits.
- `eibo://guide/language`: the approved language for people decisions ("not retained in simulation", never "terminated").

### Prompts

| Prompt | For | What it does |
|---|---|---|
| `prepare_retention_conversation(employee_id)` | Managers | Profile, likely driver, open questions and options for a supportive 1:1 |
| `team_health_check(department)` | Managers | Health, retention, knowledge and succession for one department |
| `review_budget_scenario(budget_pct)` | Analysts | Compares nearby budgets, checks coverage, fairness and knowledge risk, lists the questions for decision-makers |

### Example questions

**Managers**
- "Which of my people need a retention conversation this month, and what's driving it?"
- "Prepare me for a 1:1 with 5AC236BE."
- "If someone on my team left, which knowledge would we lose with no backup?"
- "Who could step in if our engineering manager left?"

**People analysts**
- "Compare 70%, 80% and 90% budgets with leadership and skills coverage on."
- "At 80%, how many top-quintile people does the plan keep, and what changes if headcount cost is 25?"
- "Run the fairness audit and tell me which flags need investigation."
- "What happens to resilience if the top 5 people by impact left?"

---

## Running over HTTP (shared or remote use)

For a client that connects over the network instead of launching a process:

```bash
export EIBO_MCP_USER=U005
export EIBO_MCP_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m mcp_server --transport http            # http://127.0.0.1:8790/mcp
```

- Clients must send `Authorization: Bearer $EIBO_MCP_TOKEN`; anything else gets `401`. The server refuses to start without a token of at least 32 characters.
- It binds to `127.0.0.1` by default. Use `--host 0.0.0.0` only behind a TLS-terminating reverse proxy.
- One HTTP server has **one** identity: everyone with the token sees what that identity sees. For per-user access, run one server per user, or put an OAuth identity provider in front and map users to identities (not included).

---

## Configuration reference

| Variable | Default | Purpose |
|---|---|---|
| `EIBO_MCP_USER` | – | Demo user id or email (or use `EIBO_MCP_ROLE`) |
| `EIBO_MCP_ROLE` | – | `viewer`, `analyst`, `manager`, `director`, `executive`, `admin` |
| `EIBO_MCP_DEPARTMENTS` | – | Comma-separated departments for scoped roles |
| `EIBO_MCP_NAME`, `EIBO_MCP_EMAIL` | generic | Identity recorded in the audit trail when using `EIBO_MCP_ROLE` |
| `EIBO_MCP_SCENARIO` | `A` | Default demo organization |
| `EIBO_MCP_SIZE` | `small` | Default organization size |
| `EIBO_MCP_SHARE_NAMES` | off | Send real employee names to the model |
| `EIBO_MCP_AUDIT_DIR` | `audit_logs` | Audit log directory (relative paths resolve against the repository) |
| `EIBO_MCP_TOKEN` | – | Required bearer token for `--transport http` |
| `LOG_LEVEL` | `WARNING` | Server logging (always to stderr) |

## Limitations

- The data is the synthetic demo organization. The web app's real-data path (`demo=false`) is not implemented, so neither is it here.
- Attrition risk is a heuristic, not the trained model (see [Applied AI](APPLIED_AI.md)).
- The Monte Carlo budget forecast is not exposed: its overspend probability compares annual trajectories against a monthly budget line and is being fixed.
- Built on the official `mcp` Python SDK 2.x (`MCPServer`). Code written for SDK 1.x (`FastMCP`) does not run on it.
