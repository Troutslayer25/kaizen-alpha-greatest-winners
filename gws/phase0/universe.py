"""Universe-eligibility builder (Phase 0) — the single source of truth for who's in-scope.

Per (ticker, date), PIT: eligible = index_member ∧ data_valid ∧ above_min_price ∧ >=252-day
history (master §3). Liquidity is NOT a gate — ADV/dollar-volume are recorded as features and
capacity is applied at deployment. The pure cores (`member_flags`, `build_eligibility`) are
tested without a DB; `write_eligibility` persists to gws.universe_eligibility (lazy)."""
from __future__ import annotations

import numpy as np

MIN_PRICE = 1.0            # ~$1 data-validity floor (penny-spread artifact guard), NOT a quality gate
MIN_HISTORY = 252


def member_flags(dates, intervals) -> np.ndarray:
    """Boolean per date: is this date inside any [from_date, to_date] membership interval?
    `intervals` = list of (from_date, to_date | None); None to_date means still a member."""
    dates = list(dates)
    flags = np.zeros(len(dates), dtype=bool)
    for frm, to in intervals:
        for i, d in enumerate(dates):
            if d >= frm and (to is None or d <= to):
                flags[i] = True
    return flags


def build_eligibility(dates, close, volume, intervals, *, min_price=MIN_PRICE,
                      min_history=MIN_HISTORY, adv_window=50, entity_excluded=False, unlock=False):
    """Return one eligibility dict per date. `intervals` are this ticker's index-membership runs.
    adv_50d / dollar_volume_50d are RECORDED (features), never gates.

    `entity_excluded` (review C2): pass True when the entity carries a whole-entity exclusion
    (gws.phase0.exclusions.excluded_ids) — every date is then ineligible, so a stale-adjustment /
    unfetchable name cannot silently remain in the universe."""
    from gws.phase0.lockbox import in_lockbox           # lazy (review C-1)
    dates = list(dates)
    close = np.asarray(close, float)
    volume = np.asarray(volume, float)
    dvol_series = volume * close                         # hoisted (review m7): one multiply, not per-date
    member = member_flags(dates, intervals)
    rows = []
    for i, d in enumerate(dates):
        # sealed holdout: never eligible until the lockbox is explicitly opened (review C-1)
        locked = (not unlock) and in_lockbox(d)
        data_valid = bool(np.isfinite(close[i]) and close[i] > 0 and np.isfinite(volume[i]) and volume[i] > 0)
        above_min = bool(close[i] >= min_price)
        has_history = i >= min_history - 1
        lo = max(0, i - adv_window + 1)
        adv = float(np.nanmean(volume[lo:i + 1])) if i >= lo else np.nan
        dvol = float(np.nanmean(dvol_series[lo:i + 1])) if i >= lo else np.nan
        rows.append({
            "date": d,
            "index_member": bool(member[i]),
            "data_valid": data_valid,
            "above_min_price": above_min,
            "eligible": bool(not locked and not entity_excluded and member[i]
                              and data_valid and above_min and has_history),
            "adv_50d": adv,
            "dollar_volume_50d": dvol,
        })
    return rows


def write_eligibility(conn, ticker_id, rows) -> int:
    """Upsert eligibility rows for one ticker into gws.universe_eligibility (lazy DB)."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO gws.universe_eligibility "
            "(ticker_id, date, eligible, index_member, data_valid, above_min_price, adv_50d, dollar_volume_50d) "
            "VALUES (%(ticker_id)s,%(date)s,%(eligible)s,%(index_member)s,%(data_valid)s,"
            "%(above_min_price)s,%(adv_50d)s,%(dollar_volume_50d)s) "
            "ON CONFLICT (ticker_id, date) DO UPDATE SET eligible=EXCLUDED.eligible, "
            "index_member=EXCLUDED.index_member, data_valid=EXCLUDED.data_valid, "
            "above_min_price=EXCLUDED.above_min_price, adv_50d=EXCLUDED.adv_50d, "
            "dollar_volume_50d=EXCLUDED.dollar_volume_50d",
            [{**r, "ticker_id": ticker_id} for r in rows])
    return len(rows)
