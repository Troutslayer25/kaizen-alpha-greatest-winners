"""Lineage: sweep detection classes + exclusion consumption."""
import numpy as np

from gws.phase0.data_quality_sweep import scan_series
from gws.phase0.exclusions import forward_fill_excluded, tradeable_mask


def _clean(n=60):
    dates = list(range(n))
    close = (100 * np.cumprod(1 + np.full(n, 0.001))).tolist()
    return dates, close


def test_phantom_zero_needs_volume():
    dates, close = _clean()
    adj = list(close); adj[20] = -1.0
    vol = [1e6] * 60
    spans = scan_series(dates, close, adj, vol)["phantom_zero"]
    assert spans == [(20, 20)]
    # same bad adj on a zero-volume (untraded) bar is NOT a phantom-zero (aligned predicate)
    vol0 = list(vol); vol0[20] = 0
    assert scan_series(dates, close, adj, vol0)["phantom_zero"] == []


def test_non_contiguous_corruption_stays_separate_spans():
    dates, close = _clean()
    adj = list(close); adj[10] = -1; adj[40] = -1
    vol = [1e6] * 60
    spans = scan_series(dates, close, adj, vol)["phantom_zero"]
    assert spans == [(10, 10), (40, 40)]        # NOT one (10,40) envelope


def test_splice_detector_ignores_legit_split_with_action_record():
    dates, close = _clean()
    # a real 2:1 split on day 30: raw close halves (a jump), adjusted stays continuous
    close = np.array(close); close[30:] /= 2
    adj = np.cumprod(1 + np.full(60, 0.001)) * 100        # continuous adjusted
    vol = [1e6] * 60
    # without the action record -> flagged; WITH it -> not flagged
    assert scan_series(dates, close, adj, vol, action_dates=None)["adjustment_splice"] == [(30, 30)]
    assert scan_series(dates, close, adj, vol, action_dates={30})["adjustment_splice"] == []


def test_tradeable_mask_and_forward_fill():
    dates = list(range(6))
    vol = [10, 0, 10, 10, 10, 10]
    spans = [(4, 4)]                              # date 4 excluded by a QC span
    mask = tradeable_mask(dates, vol, spans)
    assert list(mask) == [True, False, True, True, False, True]
    vals = np.array([1.0, 99.0, 2.0, 3.0, 99.0, 4.0])   # 99s are the untradeable bars
    filled = forward_fill_excluded(vals, mask)
    assert list(filled) == [1.0, 1.0, 2.0, 3.0, 3.0, 4.0]   # no phantom jump on excluded bars
