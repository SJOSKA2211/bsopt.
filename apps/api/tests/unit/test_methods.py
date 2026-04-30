"""Unit tests for numerical pricing methods — Phase 4."""
from __future__ import annotations
import pytest
import numpy as np

pytestmark = pytest.mark.unit
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
from src.methods.tree_methods.richardson import RichardsonExtrapolation, TrinomialRichardsonExtrapolation
from src.exceptions import CFLViolationError

@pytest.fixture
def base_params():
    return OptionParams(
        underlying_price=100.0,
        strike_price=100.0,
        time_to_expiry=1.0,
        volatility=0.2,
        risk_free_rate=0.05,
        option_type="call"
    )

def test_option_params_validation() -> None:
    with pytest.raises(ValueError, match="positive"):
        OptionParams(0, 100, 1, 0.2, 0.05, "call")
    with pytest.raises(ValueError, match="positive"):
        OptionParams(100, 0, 1, 0.2, 0.05, "call")
    with pytest.raises(ValueError, match="positive"):
        OptionParams(100, 100, 0, 0.2, 0.05, "call")
    with pytest.raises(ValueError, match="positive"):
        OptionParams(100, 100, 1, 0, 0.05, "call")
    with pytest.raises(ValueError, match="type"):
        OptionParams(100, 100, 1, 0.2, 0.05, "invalid")

def test_analytical_call(base_params):
    pricer = BlackScholesAnalytical()
    res = pricer.price(base_params)
    assert pytest.approx(res.computed_price, 0.01) == 10.4505
    
    # Test Greeks
    greeks = pricer.greeks(base_params)
    assert 0 < greeks["delta"] < 1
    assert greeks["gamma"] > 0
    assert greeks["vega"] > 0
    assert greeks["theta"] < 0
    assert greeks["rho"] > 0
    
    # Test Implied Vol
    iv = pricer.implied_volatility(res.computed_price, base_params)
    assert pytest.approx(iv, 0.001) == 0.2

def test_analytical_put(base_params):
    params = OptionParams(100, 100, 1, 0.2, 0.05, "put")
    pricer = BlackScholesAnalytical()
    res = pricer.price(params)
    assert pytest.approx(res.computed_price, 0.01) == 5.5735
    
    greeks = pricer.greeks(params)
    assert -1 < greeks["delta"] < 0
    assert greeks["theta"] < 0
    assert greeks["rho"] < 0
    
    iv = pricer.implied_volatility(res.computed_price, params)
    assert pytest.approx(iv, 0.001) == 0.2
    
    # Test invalid IV
    assert pricer.implied_volatility(-1, params) == 0.0

def test_explicit_fdm_cfl_violation(base_params):
    pricer = ExplicitFDM()
    with pytest.raises(CFLViolationError):
        pricer.price(base_params, m_steps=200, n_steps=100)

def test_explicit_fdm_put(base_params):
    params = OptionParams(100, 100, 1, 0.2, 0.05, "put")
    pricer = ExplicitFDM()
    res = pricer.price(params, m_steps=50, n_steps=2000)
    assert pytest.approx(res.computed_price, 0.1) == 5.57

def test_implicit_fdm_put(base_params):
    params = OptionParams(100, 100, 1, 0.2, 0.05, "put")
    pricer = ImplicitFDM()
    res = pricer.price(params, m_steps=100, n_steps=1000)
    assert pytest.approx(res.computed_price, 0.1) == 5.57

def test_crank_nicolson_put(base_params):
    params = OptionParams(100, 100, 1, 0.2, 0.05, "put")
    pricer = CrankNicolsonFDM()
    res = pricer.price(params, m_steps=100, n_steps=1000)
    assert pytest.approx(res.computed_price, 0.01) == 5.57

def test_standard_mc_confidence(base_params):
    pricer = StandardMonteCarlo()
    ci = pricer.price_with_confidence_interval(base_params, num_paths=1000)
    assert ci["ci_lower"] < ci["price"] < ci["ci_upper"]

def test_antithetic_mc_odd_paths(base_params):
    pricer = AntitheticMonteCarlo()
    # Test odd number of paths to cover line 20
    res = pricer.price(base_params, num_paths=10001)
    assert res.parameter_set["num_paths"] == 10002
    assert pytest.approx(res.computed_price, 0.5) == 10.45

def test_antithetic_mc_put(base_params):
    params = OptionParams(100, 100, 1, 0.2, 0.05, "put")
    pricer = AntitheticMonteCarlo()
    res = pricer.price(params, num_paths=10000)
    assert pytest.approx(res.computed_price, 0.2) == 5.57

def test_binomial_crr_american(base_params):
    pricer = BinomialCRR()
    # European call
    params_euro = OptionParams(
        base_params.underlying_price,
        base_params.strike_price,
        base_params.time_to_expiry,
        base_params.volatility,
        base_params.risk_free_rate,
        base_params.option_type,
        exercise_type="european",
    )
    res_euro = pricer.price(params_euro, num_steps=500)
    assert pytest.approx(res_euro.computed_price, 0.01) == 10.45

    # American call (should be same as Euro for non-dividend)
    params_amer = OptionParams(
        base_params.underlying_price,
        base_params.strike_price,
        base_params.time_to_expiry,
        base_params.volatility,
        base_params.risk_free_rate,
        base_params.option_type,
        exercise_type="american",
    )
    res_amer = pricer.price(params_amer, num_steps=500)
    assert pytest.approx(res_amer.computed_price, 0.01) == 10.45

    # American put (should be higher than Euro)
    params_put_euro = OptionParams(100, 100, 1, 0.2, 0.05, "put", exercise_type="european")
    params_put_amer = OptionParams(100, 100, 1, 0.2, 0.05, "put", exercise_type="american")
    res_euro_put = pricer.price(params_put_euro, num_steps=500)
    res_amer_put = pricer.price(params_put_amer, num_steps=500)
    assert res_amer_put.computed_price > res_euro_put.computed_price

def test_trinomial_put(base_params):
    params = OptionParams(100, 100, 1, 0.2, 0.05, "put")
    pricer = TrinomialTree()
    res = pricer.price(params, num_steps=500)
    assert pytest.approx(res.computed_price, 0.01) == 5.57

@pytest.mark.parametrize("pricer_class", [
    BlackScholesAnalytical, ExplicitFDM, ImplicitFDM, CrankNicolsonFDM,
    StandardMonteCarlo, AntitheticMonteCarlo, ControlVariateMonteCarlo,
    QuasiMonteCarlo, BinomialCRR, TrinomialTree,
    RichardsonExtrapolation, TrinomialRichardsonExtrapolation
])
def test_all_methods_agreement(pricer_class, base_params):
    pricer = pricer_class()
    if isinstance(pricer, ExplicitFDM):
        res = pricer.price(base_params, m_steps=50, n_steps=2000)
    elif isinstance(pricer, (ImplicitFDM, CrankNicolsonFDM)):
        res = pricer.price(base_params, m_steps=100, n_steps=1000)
    else:
        res = pricer.price(base_params)
    
    bs_price = 10.4505
    tol = 0.3 if "MonteCarlo" in pricer.__class__.__name__ else 0.1
    assert pytest.approx(res.computed_price, abs=tol) == bs_price


def test_analytical_geometric_asian(base_params):
    pricer = BlackScholesAnalytical()
    price = pricer.geometric_asian_price(base_params)
    # For a fixed underlying and volatility, GA price < BS price
    assert 0 < price < 10.45


def test_control_variate_mc_convergence(base_params):
    pricer = ControlVariateMonteCarlo()
    # Use 10,000 paths for more stability in unit test
    res = pricer.price(base_params, num_paths=10000)
    assert pytest.approx(res.computed_price, abs=0.2) == 10.45


def test_quasi_mc_sobol_paths(base_params):
    pricer = QuasiMonteCarlo()
    # Should enforce power of 2
    res = pricer.price(base_params, num_paths=500)
    assert res.parameter_set["num_paths"] == 512
