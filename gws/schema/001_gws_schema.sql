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
--
-- KEYED ON entity_id (= Norgate assetid = ka_history.entities.entity_id), NOT
-- tickers.id. tickers.id only exists for the ~7,250 CURRENT FMP symbols; keying
-- membership there silently drops every delisted / pre-2010 constituent and
-- reintroduces survivorship bias into the one table whose whole job is to prevent
-- it (review 2026-07-03 CF-1). entity_id is the permanent identity that exists for
-- dead names. The FMP-era public join goes through gws.entity_ticker_map.
CREATE TABLE IF NOT EXISTS gws.index_membership (
  entity_id    BIGINT  NOT NULL,           -- Norgate assetid = ka_history.entities.entity_id
  index_name   TEXT    NOT NULL,           -- 'sp500','sp400','sp600','r1000','r2000','r3000','ndx100'
  from_date    DATE    NOT NULL,           -- inclusive
  to_date      DATE,                        -- NULL = still a member AND still listed (see ingester)
  source       TEXT    NOT NULL DEFAULT 'norgate',
  PRIMARY KEY (entity_id, index_name, from_date)
);
CREATE INDEX IF NOT EXISTS ix_index_membership_entity ON gws.index_membership (entity_id, from_date);

-- entity_id <-> tickers.id crosswalk (lineage artifact, not a convention). Populated
-- for entities that have a live FMP symbol; delisted / pre-2010 entities have NO row
-- here and are joined by entity_id against ka_history only.
CREATE TABLE IF NOT EXISTS gws.entity_ticker_map (
  entity_id    BIGINT  NOT NULL PRIMARY KEY,   -- ka_history.entities.entity_id (Norgate assetid)
  ticker_id    BIGINT NOT NULL,               -- public.tickers.id (FMP domain)
  match_method TEXT    NOT NULL,               -- 'assetid_symbol' | 'manual' | ...
  confidence   NUMERIC,                        -- 0..1 (symbol-recycling ambiguity)
  created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_entity_ticker_map_ticker ON gws.entity_ticker_map (ticker_id);

-- Watchlist symbols the ingester could NOT resolve to a ka_history entity — persisted,
-- never printed-and-forgotten (review 2026-07-03 CF-1). A non-trivial count here HALTs
-- the ingest: a silently short universe is the failure mode we are guarding against.
CREATE TABLE IF NOT EXISTS gws.index_membership_unmapped (
  norgate_symbol TEXT NOT NULL,
  index_name     TEXT NOT NULL,
  reason         TEXT NOT NULL,                -- 'no_assetid' | 'assetid_not_in_ka_history'
  observed_at    TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (norgate_symbol, index_name)
);

-- Liquidity-tier reference (v2: NOT a universe gate). The ADV floor was removed from
-- universe construction; liquidity is carried as a feature and capacity is applied at the
-- deployment layer. This table is retained only for optional liquidity-tier / capacity
-- bucketing (knee-of-curve utility) — never to gate gws.universe_eligibility.
CREATE TABLE IF NOT EXISTS gws.liquidity_floors (
  period_label      TEXT    NOT NULL,       -- '1950_2009' | '2010_present'
  year              INTEGER NOT NULL,
  adv_floor_value   NUMERIC NOT NULL,
  discovery_method  TEXT    NOT NULL,        -- pre-committed (e.g. 'kneedle_log10_adv')
  n_tickers_in_dist INTEGER,
  PRIMARY KEY (period_label, year)
);

-- Time-varying eligibility flag (single source of truth downstream).
-- v2: eligible = index_member AND data_valid AND above_min_price AND 252-day history.
-- NO institutional ADV liquidity gate — liquidity is a recorded feature, not a filter.
CREATE TABLE IF NOT EXISTS gws.universe_eligibility (
  ticker_id          BIGINT NOT NULL,
  date               DATE    NOT NULL,
  eligible           BOOLEAN NOT NULL,
  index_member       BOOLEAN NOT NULL,      -- Layer 1: quality filter (index membership)
  index_list         TEXT,                   -- which index(es) on this date
  data_valid         BOOLEAN NOT NULL,      -- Layer 2: minimal data-validity screen (real volume, clean data)
  above_min_price    BOOLEAN NOT NULL,      -- data-validity price floor (~$1; penny-spread artifact guard)
  adv_50d            NUMERIC,               -- recorded liquidity metric — FEATURE, not a gate
  dollar_volume_50d  NUMERIC,               -- recorded — FEATURE, not a gate
  PRIMARY KEY (ticker_id, date)
);

-- ---------------------------------------------------------------------------
-- Unifying observation table — feature store key (blueprint T2)
-- Every analytical point (setup trough, matched control, sampled point) is an
-- observation; features are joined by (ticker_id, as_of_date).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.observations (
  observation_id  BIGSERIAL PRIMARY KEY,
  ticker_id       BIGINT NOT NULL,
  as_of_date      DATE    NOT NULL,
  obs_type        TEXT    NOT NULL,         -- 'setup_trough' | 'matched_control' | 'sampled_point'
  linked_move_id  INTEGER,                   -- the move this observation derives from, if any
  UNIQUE (ticker_id, as_of_date, obs_type, linked_move_id)
);
CREATE INDEX IF NOT EXISTS ix_observations_tickerdate ON gws.observations (ticker_id, as_of_date);

-- ---------------------------------------------------------------------------
-- Phase A1 — Moves
-- Canonical detector: threshold-free, multi-scale MFE (gws/phase_a1/move_detector_mfe.py).
-- ATR-swing (gws/phase_a1/trough_detector.py) is retained as a reference / cross-check
-- baseline only. Detector parameters (scale set, primary scale, percentile-significance
-- cutoff, the absolute-return cross-check) are finalized in the Phase A1 pre-commit.
--
-- PERSISTENCE CONTRACT (the detectors return ticker-agnostic, index-keyed dataclasses;
-- the Phase-A1 writer performs this mapping — see move_detector_mfe.MoveMFE):
--   MoveMFE.magnitude   -> total_pct_gain      MoveMFE.smoothness       -> smoothness_metric
--   MoveMFE.mae         -> mae                 MoveMFE.early_smoothness -> early_smoothness
--   MoveMFE.scale       -> scale               MoveMFE.drawdown_timing  -> drawdown_timing
--   MoveMFE.trail_atr   -> trail_atr           MoveMFE.is_open          -> is_open
--   trough_idx/peak_idx -> start_date/peak_date (writer maps bar index -> calendar date)
--   writer also attaches ticker_id, sets detection_system, and sets is_primary_scale
--   (TRUE only for the pre-committed primary scale).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gws.moves (
  move_id            SERIAL PRIMARY KEY,
  -- ID DOMAIN (review C1): the study RULE is single-domain — `ticker_id` holds the Norgate
  -- entity_id (= assetid) everywhere; FMP `tickers.id` is strictly QC / cross-check and is NEVER
  -- persisted here. `id_domain` is a belt-and-suspenders discriminator IN the natural key so that,
  -- even if that rule is ever violated, an FMP-domain persist can never DELETE a Norgate catalog.
  -- ticker_id is BIGINT because Norgate assetids can exceed 2^31-1.
  id_domain          TEXT    NOT NULL DEFAULT 'norgate',
  ticker_id          BIGINT  NOT NULL,
  start_date         DATE    NOT NULL,       -- trough — feature extraction anchor
  peak_date          DATE    NOT NULL,       -- never used in feature extraction
  resolved_date      DATE,                    -- stop-fire (resolution) date; NULL if is_open. The move's
                                             -- DECISION date for significance percentiles (review C-2), NOT peak_date.
  total_pct_gain     NUMERIC NOT NULL,       -- clustering dim 1: magnitude  (MoveMFE.magnitude)
  duration_days      INTEGER NOT NULL,       -- clustering dim 2: duration
  smoothness_metric  NUMERIC,                -- clustering dim 3 (uncensored): path efficiency
  early_smoothness   NUMERIC,                -- comparative dim: smoothness of the first third (early drama)
  drawdown_timing    NUMERIC,                -- comparative dim: location of deepest drawdown in [0,1] (0=early shakeout)
  mae                NUMERIC,                -- max adverse excursion below start (recorded, not gated)
  max_intra_drawdown NUMERIC,                -- diagnostic/comparative (drawdown from running peak)
  detection_system   TEXT    NOT NULL,       -- 'mfe' (canonical) | 'atr_swing' | 'absolute_return' (cross-check)
  scale              TEXT    NOT NULL DEFAULT 'none',  -- MFE multi-scale tag (e.g. 'trail_6'); 'none' for non-MFE.
                                             -- NOT NULL so the UNIQUE natural key below works (Postgres treats
                                             -- NULLs as distinct, which would defeat ON CONFLICT for non-MFE writers).
  trail_atr          NUMERIC,                -- the trailing-stop ATR multiple this move was detected at
  reversal_threshold NUMERIC,                -- (atr_swing baseline only)
  is_primary_scale   BOOLEAN NOT NULL DEFAULT TRUE,   -- writer sets per the pre-committed primary scale
  is_open            BOOLEAN NOT NULL DEFAULT FALSE,  -- move unresolved at series end
  cluster_id         INTEGER,                -- NULL until clustering complete
  cluster_label      TEXT,                   -- descriptive, post-hoc
  context_score      NUMERIC,                -- snapshot from regime_daily at start_date
  context_label      TEXT,
  is_control         BOOLEAN NOT NULL DEFAULT FALSE,
  magnitude_pctile   NUMERIC,                -- significance = percentile, not a hardcoded cutoff.
                                             -- PIT RULE (review 2026-07-03 CF-3): this percentile MUST NOT be
                                             -- computed over the full 1950-2025 population — that leaks the future
                                             -- move distribution into every training-fold label. Assign it via
                                             -- gws.phase_a1.significance (frozen train-block threshold OR expanding
                                             -- window: rank vs moves decided on/before this move's decision date).
  pctile_basis       TEXT CONSTRAINT ck_pctile_basis
                       CHECK (pctile_basis IS NULL OR pctile_basis = 'expanding'
                              OR pctile_basis LIKE 'frozen_train:%'),   -- 'full_sample' unrepresentable even via raw SQL (CF-3)
  -- Classification catalog (gws.phase_a1.move_characterization). Two JSONB bags so the move
  -- population can be queried in ways not foreseen now WITHOUT a schema migration per descriptor:
  --   descriptors : POST-HOC move shape/structure (magnitude, pullbacks, streaks, gaps, volume
  --                 profile, pre-move base, RS-during) — outcome data, for classification/query.
  --   inception   : PIT state AT the trough (price vs MA sweep, dist-from-52w-hi/lo, ATR%, RSI,
  --                 vol-vs-avg, RS-vs-bench) — forward-invariant, so moves can be sliced by what
  --                 the tape looked like when they BEGAN ("moves that started above the 200-day MA").
  -- Query typed: (descriptors->>'num_pullbacks')::numeric, (inception->>'incept_above_sma200')::numeric.
  descriptors        JSONB,
  inception          JSONB,
  detect_params      JSONB,                  -- {atr_period, min_duration, scales} detection provenance (Lineage m-10)
  run_id             TEXT,                    -- optional detection-run tag (latest-run wins via delete-before-insert)
  UNIQUE (id_domain, ticker_id, start_date, scale, detection_system)   -- natural key -> idempotent re-persist
);
CREATE INDEX IF NOT EXISTS ix_moves_descriptors ON gws.moves USING GIN (descriptors);
CREATE INDEX IF NOT EXISTS ix_moves_inception   ON gws.moves USING GIN (inception);
-- Expression btree indexes for the hot NUMERIC-range JSONB predicates (Lineage m-3): GIN(jsonb_ops)
-- accelerates @>/? containment, NOT (bag->>k)::numeric ranges. Add more per observed query load.
CREATE INDEX IF NOT EXISTS ix_moves_desc_magnitude
  ON gws.moves (((descriptors ->> 'magnitude')::numeric));
CREATE INDEX IF NOT EXISTS ix_moves_incept_sma200
  ON gws.moves (((inception ->> 'incept_price_to_sma200')::numeric));
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
-- PERSISTENCE CONTRACT: build_matched_controls (gws/phase_a1/matched_controls.py) returns
-- pool rows + `matched_setup_id` (a setup row-index). The writer resolves
-- matched_setup_id -> matched_move_id (the setup's move) and renames the caller's match
-- columns to match_market_cap_bucket / match_sector / match_liquidity_bucket. Match values
-- MUST be PIT (computed from data on/before the control's own date).
CREATE TABLE IF NOT EXISTS gws.matched_controls (
  control_id              SERIAL PRIMARY KEY,
  matched_move_id         INTEGER NOT NULL REFERENCES gws.moves(move_id),
  ticker_id               BIGINT NOT NULL,
  date                    DATE    NOT NULL,  -- the as_of_date for this control
  match_market_cap_bucket TEXT,
  match_sector            TEXT,
  match_liquidity_bucket  TEXT
);
CREATE INDEX IF NOT EXISTS ix_matched_controls_tickerdate ON gws.matched_controls (ticker_id, date);

-- Production-dataset forward-labeling artifact. INDEPENDENT sampling frame —
-- NOT derived from matched_controls (T1).
-- PERSISTENCE CONTRACT: build_setup_labels (gws/phase_a1/labeling.py) returns `as_of_index`
-- (a bar index) and `linked_trough_index`. The writer maps as_of_index -> date and resolves
-- linked_trough_index -> the move_id whose start_date is that trough -> linked_move_id.
-- lead_time_days / linked_move_id are future-derived label metadata and MUST NEVER be features.
CREATE TABLE IF NOT EXISTS gws.setup_labels (
  label_id         SERIAL PRIMARY KEY,
  ticker_id        BIGINT NOT NULL,
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
  ticker_id     BIGINT NOT NULL,
  as_of_date    DATE    NOT NULL,
  feature_name  TEXT    NOT NULL,
  feature_value NUMERIC,
  lookback_days INTEGER NOT NULL,
  PRIMARY KEY (ticker_id, as_of_date, feature_name, lookback_days)
);

CREATE TABLE IF NOT EXISTS gws.features_fundamental (
  ticker_id      BIGINT NOT NULL,
  as_of_date     DATE    NOT NULL,
  feature_name   TEXT    NOT NULL,
  feature_value  NUMERIC,
  period_end     DATE    NOT NULL,           -- QUARTER IDENTIFIER only (which fiscal quarter)
  available_date DATE    NOT NULL,           -- public-availability gate: filing/release date when
                                             --   reliable, else period_end + conservative lag (OQ-9).
                                             --   A quarter is usable only where available_date <= as_of_date.
                                             --   Fundamentals are NEVER treated as known at period_end.
  period_type    TEXT,
  statement_type TEXT,                        -- 'income'|'balance_sheet'|'cash_flow'
  PRIMARY KEY (ticker_id, as_of_date, feature_name),
  CHECK (available_date <= as_of_date)        -- structural guard against quarter-end look-ahead
);

CREATE TABLE IF NOT EXISTS gws.features_context (
  ticker_id     BIGINT NOT NULL,
  as_of_date    DATE    NOT NULL,
  feature_name  TEXT    NOT NULL,
  feature_value NUMERIC,
  PRIMARY KEY (ticker_id, as_of_date, feature_name)
);

CREATE TABLE IF NOT EXISTS gws.feature_catalog (
  feature_name    TEXT PRIMARY KEY,
  branch          TEXT,                       -- 'price_volume'|'fundamental'|'context'|'generic'
  formula_version TEXT,
  description      TEXT,
  first_used_date DATE,
  status          TEXT,
  deprecation_note TEXT,
  -- ORIGIN of the feature (why it entered the catalog), tagged at registration BEFORE
  -- results are seen. An honesty/Auditor-4 instrument: lets Gate A3->A4 cross-tab which
  -- Tier-1 findings came from generic discovery vs. pre-existing practitioner concepts.
  motivation      TEXT NOT NULL DEFAULT 'unclassified'
    CHECK (motivation IN ('theory_motivated','practitioner_derived',
                          'generic_statistical','auto_generated','unclassified'))
);

-- ---------------------------------------------------------------------------
-- Phase A3 — Statistical discovery
-- ---------------------------------------------------------------------------

-- Entry-point analysis (Method 8, expanded): candidate entries ALONG each move — including
-- points of strength (breakout / gap / MA-reclaim), not only the pre-trough window — scored by
-- forward reward/risk. "Low-risk entry" = best forward_mfe / forward_mae. Detector unchanged;
-- this is an analysis layer on top of gws.moves. See research/entry_point_discovery.md.
CREATE TABLE IF NOT EXISTS gws.entry_candidates (
  entry_id       BIGSERIAL PRIMARY KEY,
  move_id        INTEGER NOT NULL REFERENCES gws.moves(move_id),
  ticker_id      BIGINT NOT NULL,
  as_of_date     DATE    NOT NULL,            -- the candidate entry date (joins the feature store)
  entry_type     TEXT,                         -- descriptive, post-hoc: 'trough'|'pullback'|'strength'|...
  forward_mfe    NUMERIC,                       -- reward: max favorable excursion from here to peak
  forward_mae    NUMERIC,                       -- risk: max adverse excursion from here before the gain
  reward_risk    NUMERIC,                       -- forward_mfe / forward_mae (the low-risk-entry score)
  days_to_peak   INTEGER,
  UNIQUE (move_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_entry_candidates_tickerdate ON gws.entry_candidates (ticker_id, as_of_date);

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
  ticker_id     BIGINT NOT NULL,
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
  ticker_id    BIGINT,
  date_from    DATE,
  date_to      DATE,
  issue        TEXT NOT NULL,                 -- 'phantom_zero_adj_close','split_explosion','numeric_overflow', ...
  resolution   TEXT,                           -- 'repaired'|'excluded'|'documented_limitation'
  source       TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);
