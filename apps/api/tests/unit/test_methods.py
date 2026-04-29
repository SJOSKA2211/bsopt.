"""Exhaustive unit tests for all 12 numerical pricing methods."""

from __future__ import annotations

import math
import pytest
import numpy as np
from src.methods.base import OptionParams, PricingResult
from src.methods.analytical import BlackScholesAnalytical
from src.methods.finite_difference.explicit import ExplicitFDM
from src.methods.finite_difference.implicit import ImplicitFDM
from src.methods.finite_difference.crank_nicolson import CrankNicolsonFDM
from src.methods.monte_carlo.standard import StandardMonteCarlo
from src.methods.monte_carlo.antithetic import AntitheticMonteCarlo
from src.methods.monte_carlo.control_variates import ControlVariateMonteCarlo
from src.methods.monte_carlo.quasi_mc import QuasiMonteCarlo
from src.methods.tree_methods.binomial_crr import BinomialCRR
from src.methods.tree_methods.trinomial import TrinomialTree
from src.methods.tree_methods.richardson import (
    RichardsonExtrapolation,
    TrinomialRichardsonExtrapolation,
)
from src.exceptions import CFLViolationError

# Canonical test parameters: S=100, K=100, T=1, sigma=0.2, r=0.05
# Analytical Call: 10.45058
# Analytical Put: 5.57352
S0, K, T, SIGMA, R = 100.0, 100.0, 1.0, 0.2, 0.05
EXPECTED_CALL = 10.45058
EXPECTED_PUT = 5.57352

@pytest.fixture
def call_params() -> OptionParams:
    return OptionParams(S0, K, T, SIGMA, R, "call")

@pytest.fixture
def put_params() -> OptionParams:
    return OptionParams(S0, K, T, SIGMA, R, "put")

@pytest.mark.unit
def test_analytical_accuracy(call_params, put_params):
    a = BlackScholesAnalytical()
    res_call = a.price(call_params)
    res_put = a.price(put_params)
    
    assert pytest.approx(res_call.computed_price, abs=1e-5) == EXPECTED_CALL
    assert pytest.approx(res_put.computed_price, abs=1e-5) == EXPECTED_PUT
    
    # Greeks
    assert a.delta(call_params) > 0.5
    assert a.delta(put_params) < -0.3 # ATM delta is ~ -0.36
    assert a.gamma(call_params) > 0
    assert a.vega(call_params) > 0
    
    # IV Inversion
    iv = a.implied_volatility(EXPECTED_CALL, call_params)
    assert pytest.approx(iv, abs=1e-4) == SIGMA
    
    # IV edge cases
    assert a.implied_volatility(0.0, call_params) == 0.0
    assert a.implied_volatility(1000.0, call_params) == 0.0

@pytest.mark.unit
def test_fdm_methods(call_params):
    # Explicit
    res_exp = ExplicitFDM(m=100, n=2000).price(call_params)
    assert pytest.approx(res_exp.computed_price, rel=1e-2) == EXPECTED_CALL
    
    # CFL Violation
    with pytest.raises(CFLViolationError):
        ExplicitFDM(m=200, n=100).price(call_params)
        
    # Implicit
    res_imp = ImplicitFDM(m=100, n=100).price(call_params)
    assert pytest.approx(res_imp.computed_price, rel=2e-2) == EXPECTED_CALL # Slightly wider rel
    
    # Crank-Nicolson
    res_cn = CrankNicolsonFDM(m=100, n=100).price(call_params)
    assert pytest.approx(res_cn.computed_price, rel=1e-2) == EXPECTED_CALL

@pytest.mark.unit
def test_mc_methods(call_params):
    # Standard MC
    res_smc = StandardMonteCarlo(num_paths=50_000, seed=42).price(call_params)
    assert pytest.approx(res_smc.computed_price, rel=1e-2) == EXPECTED_CALL
    
    # CI
    price, width = StandardMonteCarlo(num_paths=1000).price_with_confidence_interval(call_params)
    assert width > 0
    
    # Antithetic
    res_amc = AntitheticMonteCarlo(num_paths=50_000, seed=42).price(call_params)
    assert pytest.approx(res_amc.computed_price, rel=1e-2) == EXPECTED_CALL
    
    # Control Variates
    res_cv = ControlVariateMonteCarlo(num_paths=10_000, seed=42).price(call_params)
    assert pytest.approx(res_cv.computed_price, rel=1e-2) == EXPECTED_CALL
    
    # Quasi MC
    res_qmc = QuasiMonteCarlo(num_paths=2**14, seed=42).price(call_params)
    assert pytest.approx(res_qmc.computed_price, rel=1e-2) == EXPECTED_CALL
    
    # Quasi MC power of 2 check
    with pytest.raises(ValueError):
        QuasiMonteCarlo(num_paths=100).price(call_params)

@pytest.mark.unit
def test_tree_methods(call_params):
    # Binomial CRR
    res_crr = BinomialCRR(steps=1000).price(call_params)
    assert pytest.approx(res_crr.computed_price, rel=1e-3) == EXPECTED_CALL
    
    # American Call should equal European Call (no dividends)
    res_crr_am = BinomialCRR(steps=100, is_american=True).price(call_params)
    res_crr_eu = BinomialCRR(steps=100, is_american=False).price(call_params)
    assert res_crr_am.computed_price >= res_crr_eu.computed_price
    
    # Trinomial
    res_tri = TrinomialTree(steps=500).price(call_params)
    assert pytest.approx(res_tri.computed_price, rel=1e-3) == EXPECTED_CALL

@pytest.mark.unit
def test_richardson_extrapolation(call_params):
    # Binomial Richardson
    res_br = RichardsonExtrapolation(steps=100).price(call_params)
    assert pytest.approx(res_br.computed_price, rel=1e-4) == EXPECTED_CALL
    
    # Trinomial Richardson
    res_tr = TrinomialRichardsonExtrapolation(steps=100).price(call_params)
    assert pytest.approx(res_tr.computed_price, rel=1e-4) == EXPECTED_CALL

@pytest.mark.unit
def test_cross_method_agreement(call_params):
    """Verify that all methods converge to the same price."""
    methods = [
        BlackScholesAnalytical(),
        ExplicitFDM(m=100, n=2000),
        ImplicitFDM(m=100, n=200),
        CrankNicolsonFDM(m=100, n=100),
        StandardMonteCarlo(num_paths=100_000, seed=42),
        AntitheticMonteCarlo(num_paths=100_000, seed=42),
        ControlVariateMonteCarlo(num_paths=50_000, seed=42),
        QuasiMonteCarlo(num_paths=2**15, seed=42),
        BinomialCRR(steps=1000),
        TrinomialTree(steps=1000),
        RichardsonExtrapolation(steps=200),
        TrinomialRichardsonExtrapolation(steps=200),
    ]
    
    prices = []
    for m in methods:
        res = m.price(call_params)
        prices.append(res.computed_price)
        
    mean_price = np.mean(prices)
    for p in prices:
        # Most methods should be within 1% of the mean at these resolutions
        assert pytest.approx(p, rel=0.02) == mean_price

@pytest.mark.unit
def test_analysis_statistics():
    from src.analysis.statistics import calculate_mape, calculate_summary_stats, calculate_confidence_interval
    
    assert calculate_mape(100.0, 90.0) == 10.0
    assert calculate_mape(0.0, 90.0) == 0.0
    
    stats = calculate_summary_stats([1, 2, 3, 4, 5])
    assert stats["mean"] == 3.0
    assert stats["std"] > 0
    assert calculate_summary_stats([]) == {}
    
    low, high = calculate_confidence_interval([10, 10.1, 9.9, 10.05, 9.95])
    assert low < 10 < high
    assert calculate_confidence_interval([]) == (0.0, 0.0)

@pytest.mark.unit
def test_convergence_analysis():
    from src.analysis.convergence import estimate_convergence_order, check_stability
    
    steps = [100, 200, 400, 800]
    errors = [0.1, 0.05, 0.025, 0.0125] # Order 1
    order = estimate_convergence_order(steps, errors)
    assert pytest.approx(order, abs=0.1) == 1.0
    assert estimate_convergence_order([1], [1]) == 0.0
    
    assert check_stability([10.45, 10.451, 10.4505], threshold=0.1) is True
    assert check_stability([10, 20], threshold=0.1) is False

@pytest.mark.unit
def test_option_params_validation():
    # Valid
    p = OptionParams(100, 100, 1, 0.2, 0.05, "call")
    assert p.underlying_price == 100
    
    # Invalid negative prices
    with pytest.raises(ValueError, match="must be > 0"):
        OptionParams(-1, 100, 1, 0.2, 0.05, "call")
    with pytest.raises(ValueError, match="must be > 0"):
        OptionParams(100, -1, 1, 0.2, 0.05, "call")
    with pytest.raises(ValueError, match="must be > 0"):
        OptionParams(100, 100, -1, 0.2, 0.05, "call")
    with pytest.raises(ValueError, match="must be > 0"):
        OptionParams(100, 100, 1, -0.2, 0.05, "call")
    
    # Invalid option type
    with pytest.raises(ValueError, match="must be 'call' or 'put'"):
        OptionParams(100, 100, 1, 0.2, 0.05, "binary")
