"""Thematic comparison: composite index + rs-vs-theme (pure)."""
import numpy as np

from gws.phase_a1.theme_move import rs_vs_theme, theme_composite, theme_moves


def test_composite_rebases_and_averages():
    a = np.array([10.0, 11.0, 12.0])          # +20%
    b = np.array([100.0, 105.0, 110.0])       # +10%
    comp = theme_composite([a, b])
    assert comp[0] == 100.0
    assert abs(comp[-1] - (120 + 110) / 2) < 1e-9         # equal-weight of the two rebased series


def test_rs_vs_theme_positive_when_member_leads():
    n = 200
    theme = 100 * np.cumprod(1 + np.full(n, 0.002))
    leader = 100 * np.cumprod(1 + np.full(n, 0.004))      # outpaces the theme
    assert rs_vs_theme(leader, theme, 199, 63) > 0
    laggard = 100 * np.cumprod(1 + np.full(n, 0.001))
    assert rs_vs_theme(laggard, theme, 199, 63) < 0


def test_theme_moves_detects_on_the_composite():
    n = 300
    up = np.concatenate([np.linspace(100, 90, 60), np.linspace(90, 180, 240)])
    comp, moves = theme_moves([up, up * 1.01])
    assert len(comp) == n
    assert any(len(ms) for ms in moves.values())          # the theme's own advance is detected
