-- Kaizen Alpha Greatest Winners Study — schema DDL
-- All study tables live in the `gws` schema inside the kaizen_alpha database,
-- parallel to `public` (production) and `ka_history` (Norgate raw history).
-- Incorporates blueprint §4 corrections: (ticker_id, as_of_date)-keyed feature
-- store via an observations table; two-dataset model (matched_controls vs
-- setup_labels); uncensored smoothness metric; provenance + data-quality registers.

CREATE SCHEMA IF NOT EXISTS gws;

-- ---------------------------------------------------------------------------
-- Phase 0 — Universe
-- ---------------------------------------------------------------------------

-- Historical PIT index-constituent membership (Norgate-sourced). NET-NEW: the
-- production DB has no membership table; this is critical-path blocker #1.
CREATE TABLE IF NOT EXISTS gws.index_membership (
  ticker_id    INTEGER NOT NULL,
  index_name   TEXT    NOT NULL,           -- 'sp500','sp400','sp600','r1000','r2000','r3000','ndx100'
  from_date    DATE    NOT NULL,           -- inclusive
  to_date      DATE,                        -- NULL = still a member
  source       TEXT    NOT NULL DEFAULT 'norgate',
  PRIMARY KEY (ticker_id, index_name, from_date)
);
CREATE INDEX IF NOT EXISTS ix_index_membership_ticker ON gws.index_membership (ticker_id, from_date);

-- Empirically discovered liquidity floors, per period.
CREATE TABLE IF NOT EXISTS gws.liquidity_floors (
  period_label      TEXT    NOT NULL,       -- '1950_2009' | '2010_present'
  year              INTEGER NOT NULL,
  adv_floor_value   NUMERIC NOT NULL,
  discovery_method  TEXT    NOT NULL,        -- pre-committed (e.g. 'kneedle_log10_adv')
  n_tickers_in_dist INTEGER,
  PRIMARY KEY (period_label, year)
);

-- Two-layer time-varying eligibility flag (single source of truth downstream).
CREATE TABLE IF NOT EXISTS gws.universe_eligibility (
  ticker_id          INTEGER NOT NULL,
  date               DATE    NOT NULL,
  eligible           BOOLEAN NOT NULL,
  index_member       BOOLEAN NOT NULL,      -- Layer 1: quality filter
  index_list         TEXT,                   -- which index(es) on this date
  above_price_floor  BOOLEAN NOT NULL,      -- Layer 2a: penny-stock exclusion
  above_adv_floor    BOOLEAN NOT NULL,      -- Layer 2b: liquidity filter
  adv_50d            NUMERIC,
  adv_floor          NUMERIC,
  PRIMARY KEY (ticker_id, date)
);

-- ---------------------------------------------------------------------------
-- Unifying observation table — feature store key (blueprint T2)
-- Every analytical point (setup trough, matched control, sampled point) is an
-- observation; features are joined by (ticker_id, as_of_date).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.observations (
  observation_id  BIGSERIAL PRIMARY KEY,
  ticker_id       INTEGER NOT NULL,
  as_of_date      DATE    NOT NULL,
  obs_type        TEXT    NOT NULL,         -- 'setup_trough' | 'matched_control' | 'sampled_point'
  linked_move_id  INTEGER,                   -- the move this observation derives from, if any
  UNIQUE (ticker_id, as_of_date, obs_type, linked_move_id)
);
CREATE INDEX IF NOT EXISTS ix_observations_tickerdate ON gws.observations (ticker_id, as_of_date);

-- ---------------------------------------------------------------------------
-- Phase A1 — Moves
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.moves (
  move_id            SERIAL PRIMARY KEY,
  ticker_id          INTEGER NOT NULL,
  start_date         DATE    NOT NULL,       -- trough — feature extraction anchor
  peak_date          DATE    NOT NULL,       -- never used in feature extraction
  total_pct_gain     NUMERIC NOT NULL,       -- clustering dim 1: magnitude
  duration_days      INTEGER NOT NULL,       -- clustering dim 2: duration
  smoothness_metric  NUMERIC,                -- clustering dim 3 (uncensored): path efficiency
  max_intra_drawdown NUMERIC,                -- diagnostic/comparative (censored by reversal threshold)
  detection_system   TEXT    NOT NULL,       -- 'atr_swing' (primary) | 'absolute_return' (confirmation)
  reversal_threshold NUMERIC,
  is_primary_scale   BOOLEAN NOT NULL DEFAULT TRUE,
  is_open            BOOLEAN NOT NULL DEFAULT FALSE,  -- move unresolved at series end
  cluster_id         INTEGER,                -- NULL until clustering complete
  cluster_label      TEXT,                   -- descriptive, post-hoc
  context_score      NUMERIC,                -- snapshot from regime_daily at start_date
  context_label      TEXT,
  is_control         BOOLEAN NOT NULL DEFAULT FALSE,
  abs_return_tier    TEXT                    -- '10_25'|'25_50'|'50_100'|'100_300'|'300_plus'
);
CREATE INDEX IF NOT EXISTS ix_moves_ticker ON gws.moves (ticker_id, start_date);

CREATE TABLE IF NOT EXISTS gws.move_clusters (
  cluster_id       INTEGER PRIMARY KEY,
  cluster_label    TEXT,
  detection_system TEXT,
  input_dimensions TEXT,                     -- which dims clustered (T4 comparative runs)
  magnitude_p25 NUMERIC, magnitude_p50 NUMERIC, magnitude_p75 NUMERIC,
  duration_p25  NUMERIC, duration_p50  NUMERIC, duration_p75  NUMERIC,
  drawdown_p50  NUMERIC, smoothness_p50 NUMERIC,
  n_moves          INTEGER,
  stability_score  NUMERIC,
  description      TEXT
);

CREATE TABLE IF NOT EXISTS gws.cluster_stability (
  stability_run_id    SERIAL PRIMARY KEY,
  detection_system    TEXT,
  input_dimensions    TEXT,
  n_clusters          INTEGER,
  n_bootstrap_samples INTEGER,
  mean_adj_rand_index NUMERIC,
  mean_variation_info NUMERIC,
  stability_verdict   TEXT,                  -- 'stable'|'marginal'|'unstable'
  notes               TEXT
);

-- Discovery dataset controls (case-control). Distinct from setup_labels (T1).
CREATE TABLE IF NOT EXISTS gws.matched_controls (
  control_id              SERIAL PRIMARY KEY,
  matched_move_id         INTEGER NOT NULL REFERENCES gws.moves(move_id),
  ticker_id               INTEGER NOT NULL,
  date                    DATE    NOT NULL,  -- the as_of_date for this control
  match_market_cap_bucket TEXT,
  match_sector            TEXT,
  match_liquidity_bucket  TEXT
);
CREATE INDEX IF NOT EXISTS ix_matched_controls_tickerdate ON gws.matched_controls (ticker_id, date);

-- Production-dataset forward-labeling artifact. INDEPENDENT sampling frame —
-- NOT derived from matched_controls (T1).
CREATE TABLE IF NOT EXISTS gws.setup_labels (
  label_id         SERIAL PRIMARY KEY,
  ticker_id        INTEGER NOT NULL,
  date             DATE    NOT NULL,         -- the as_of_date; features measured here
  label            BOOLEAN NOT NULL,         -- positive if a confirmed trough falls within forward_window_k
  forward_window_k INTEGER NOT NULL,
  linked_move_id   INTEGER REFERENCES gws.moves(move_id),  -- NULL for negatives
  lead_time_days   INTEGER,                  -- days from `date` to the linked move's trough
  UNIQUE (ticker_id, date, forward_window_k)
);

CREATE TABLE IF NOT EXISTS gws.tradeability_diagnostic (
  diag_id                       SERIAL PRIMARY KEY,
  abs_return_tier               TEXT,
  adv_decile                    INTEGER,
  n_moves                       INTEGER,
  median_market_cap             NUMERIC,
  pct_in_lowest_liquidity_decile NUMERIC,
  sector_concentration          TEXT
);

-- ---------------------------------------------------------------------------
-- Phase A2 — Feature store (keyed by ticker_id, as_of_date — blueprint T2)
-- Long/audit store; a wide matrix is materialized to Parquet for ML (T3).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.features_price_volume (
  ticker_id     INTEGER NOT NULL,
  as_of_date    DATE    NOT NULL,
  feature_name  TEXT    NOT NULL,
  feature_value NUMERIC,
  lookback_days INTEGER NOT NULL,
  PRIMARY KEY (ticker_id, as_of_date, feature_name, lookback_days)
);

CREATE TABLE IF NOT EXISTS gws.features_fundamental (
  ticker_id      INTEGER NOT NULL,
  as_of_date     DATE    NOT NULL,
  feature_name   TEXT    NOT NULL,
  feature_value  NUMERIC,
  period_end     DATE    NOT NULL,           -- PIT join date — never report_date
  period_type    TEXT,
  statement_type TEXT,                        -- 'income'|'balance_sheet'|'cash_flow'
  PRIMARY KEY (ticker_id, as_of_date, feature_name)
);

CREATE TABLE IF NOT EXISTS gws.features_context (
  ticker_id     INTEGER NOT NULL,
  as_of_date    DATE    NOT NULL,
  feature_name  TEXT    NOT NULL,
  feature_value NUMERIC,
  PRIMARY KEY (ticker_id, as_of_date, feature_name)
);

CREATE TABLE IF NOT EXISTS gws.feature_catalog (
  feature_name    TEXT PRIMARY KEY,
  branch          TEXT,                       -- 'price_volume'|'fundamental'|'context'
  formula_version TEXT,
  description      TEXT,
  first_used_date DATE,
  status          TEXT,
  deprecation_note TEXT
);

-- ---------------------------------------------------------------------------
-- Phase A3 — Statistical discovery
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.feature_decay (
  feature_name      TEXT    NOT NULL,
  target            TEXT    NOT NULL,
  horizon_days      INTEGER NOT NULL,         -- horizon relative to start_date (trough)
  information_coeff NUMERIC,
  ic_pvalue         NUMERIC,
  ic_tstat          NUMERIC,
  PRIMARY KEY (feature_name, target, horizon_days)
);

CREATE TABLE IF NOT EXISTS gws.findings_registry (
  finding_id                    SERIAL PRIMARY KEY,
  feature_name                  TEXT,
  target                        TEXT,
  passed_walk_forward           BOOLEAN,
  passed_factor_neutralization  BOOLEAN,
  passed_industry_neutralization BOOLEAN,
  passed_pretrough_actionability BOOLEAN,
  tier                          INTEGER,      -- 1 production candidate, 2 validated, 3 exploratory
  economic_mechanism            TEXT,
  notes                         TEXT
);

-- ---------------------------------------------------------------------------
-- Market context workstream
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.regime_daily (
  date            DATE PRIMARY KEY,
  f1_score        NUMERIC,                    -- equity/options relationship (primary)
  f1_alt_rvol     NUMERIC, f1_alt_termstr NUMERIC, f1_alt_vvix NUMERIC, f1_alt_vrp NUMERIC,
  f2_score        NUMERIC,                    -- breadth
  f3_score        NUMERIC,                    -- credit conditions
  composite_score NUMERIC,
  regime_label    TEXT,
  trend_anchor    BOOLEAN,
  score_version   TEXT
);

-- ---------------------------------------------------------------------------
-- Scoring outputs (versioned) + experiment registry
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.scores (
  ticker_id     INTEGER NOT NULL,
  date          DATE    NOT NULL,
  score         NUMERIC,
  score_version TEXT    NOT NULL,             -- 'v1_effect_size'|'v2_elastic_net'|'v2_lightgbm'|'v2_validated'
  target        TEXT    NOT NULL,             -- 'setup_probability'|'cluster_<id>'
  PRIMARY KEY (ticker_id, date, score_version, target)
);

CREATE TABLE IF NOT EXISTS gws.experiments (
  experiment_id  SERIAL PRIMARY KEY,
  hypothesis     TEXT,
  phase          TEXT,
  parameters     JSONB,
  commit_hash    TEXT,
  timestamp      TIMESTAMPTZ DEFAULT now(),
  result_summary TEXT,
  outcome        TEXT
);

-- ---------------------------------------------------------------------------
-- Governance registers (blueprint §1A / §4)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.code_provenance (
  provenance_id    SERIAL PRIMARY KEY,
  component        TEXT NOT NULL,             -- e.g. 'ka_lib.db.ka_query'
  source_path      TEXT,
  bias_tier        TEXT NOT NULL,             -- 'A'|'B'|'C'
  params_stripped  TEXT,                       -- what inherited params were removed (Tier B)
  auditor2_verdict TEXT,
  auditor4_verdict TEXT,
  commit_hash      TEXT,
  reviewed_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gws.data_quality_exceptions (
  exception_id SERIAL PRIMARY KEY,
  ticker_id    INTEGER,
  date_from    DATE,
  date_to      DATE,
  issue        TEXT NOT NULL,                 -- 'phantom_zero_adj_close','split_explosion','numeric_overflow', ...
  resolution   TEXT,                           -- 'repaired'|'excluded'|'documented_limitation'
  source       TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);
