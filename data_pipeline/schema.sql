-- EIBO Database Schema
-- Medallion Architecture: Bronze → Silver → Gold

-- ============================================================
-- DIMENSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_team (
    team_id         VARCHAR(36) PRIMARY KEY,
    team_name       VARCHAR(100) NOT NULL,
    department      VARCHAR(100) NOT NULL,
    cost_center     VARCHAR(50),
    parent_team_id  VARCHAR(36) REFERENCES dim_team(team_id),
    manager_id      VARCHAR(36),
    annual_budget   NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    scenario_id     VARCHAR(10),
    org_size        VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS dim_employee (
    employee_id         VARCHAR(36) PRIMARY KEY,
    full_name           VARCHAR(150) NOT NULL,
    email               VARCHAR(150),
    role_title          VARCHAR(100) NOT NULL,
    seniority_level     VARCHAR(20) NOT NULL,   -- junior, mid, senior, lead, director, exec
    department          VARCHAR(100) NOT NULL,
    team_id             VARCHAR(36) REFERENCES dim_team(team_id),
    manager_id          VARCHAR(36) REFERENCES dim_employee(employee_id),
    hire_date           DATE NOT NULL,
    annual_salary       NUMERIC(12,2) NOT NULL,
    annual_benefits     NUMERIC(12,2) NOT NULL,
    is_active           BOOLEAN DEFAULT TRUE,
    location            VARCHAR(100),
    created_at          TIMESTAMP DEFAULT NOW(),
    scenario_id         VARCHAR(10),
    org_size            VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id        VARCHAR(36) PRIMARY KEY,
    skill_name      VARCHAR(100) NOT NULL UNIQUE,
    category        VARCHAR(50) NOT NULL,   -- technical, leadership, domain, soft
    is_critical     BOOLEAN DEFAULT FALSE,
    market_scarcity NUMERIC(4,3) DEFAULT 0.5  -- 0=common, 1=very rare
);

CREATE TABLE IF NOT EXISTS employee_skills (
    employee_id     VARCHAR(36) REFERENCES dim_employee(employee_id),
    skill_id        VARCHAR(36) REFERENCES skills(skill_id),
    proficiency     NUMERIC(4,3) NOT NULL,   -- 0.0 to 1.0
    is_primary      BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (employee_id, skill_id)
);

-- ============================================================
-- FACTS
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_performance (
    performance_id  VARCHAR(36) PRIMARY KEY,
    employee_id     VARCHAR(36) REFERENCES dim_employee(employee_id),
    review_date     DATE NOT NULL,
    review_period   VARCHAR(20) NOT NULL,   -- e.g. "2023-Q1"
    kpi_score       NUMERIC(4,2) NOT NULL,  -- 0.0 to 5.0
    goals_met_pct   NUMERIC(5,2),           -- 0-100
    manager_rating  NUMERIC(4,2),
    peer_rating     NUMERIC(4,2),
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_budget (
    budget_id       VARCHAR(36) PRIMARY KEY,
    team_id         VARCHAR(36) REFERENCES dim_team(team_id),
    fiscal_period   VARCHAR(20) NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    budgeted_amount NUMERIC(14,2) NOT NULL,
    actual_amount   NUMERIC(14,2) NOT NULL,
    headcount_plan  INTEGER,
    headcount_actual INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_collaboration (
    source_id           VARCHAR(36) REFERENCES dim_employee(employee_id),
    target_id           VARCHAR(36) REFERENCES dim_employee(employee_id),
    relationship_type   VARCHAR(30) NOT NULL,  -- collaborates_with, reports_to, mentors
    interaction_weight  NUMERIC(4,3) NOT NULL, -- 0.0 to 1.0
    period              VARCHAR(20),
    PRIMARY KEY (source_id, target_id, relationship_type)
);

-- ============================================================
-- DEMO METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS demo_organizations (
    org_id          VARCHAR(36) PRIMARY KEY,
    scenario_id     VARCHAR(10) NOT NULL,
    org_size        VARCHAR(10) NOT NULL,
    org_name        VARCHAR(150) NOT NULL,
    industry        VARCHAR(100),
    description     TEXT,
    total_employees INTEGER,
    annual_budget   NUMERIC(16,2),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- AUDIT
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    log_id          VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    event_type      VARCHAR(50) NOT NULL,
    actor_id        VARCHAR(36),
    resource_type   VARCHAR(50),
    resource_id     VARCHAR(36),
    payload         JSONB,
    ip_address      INET,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_employee_team ON dim_employee(team_id);
CREATE INDEX IF NOT EXISTS idx_employee_manager ON dim_employee(manager_id);
CREATE INDEX IF NOT EXISTS idx_employee_scenario ON dim_employee(scenario_id, org_size);
CREATE INDEX IF NOT EXISTS idx_performance_employee ON fact_performance(employee_id);
CREATE INDEX IF NOT EXISTS idx_performance_period ON fact_performance(review_period);
CREATE INDEX IF NOT EXISTS idx_budget_team ON fact_budget(team_id);
CREATE INDEX IF NOT EXISTS idx_collaboration_source ON fact_collaboration(source_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
