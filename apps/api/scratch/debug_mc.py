
import numpy as np
from src.methods.base import OptionParams
from src.methods.monte_carlo.control_variates import ControlVariateMonteCarlo

params = OptionParams(
    underlying_price=100.0,
    strike_price=100.0,
    time_to_expiry=1.0,
    volatility=0.2,
    risk_free_rate=0.05,
    option_type="call"
)

cv_pricer = ControlVariateMonteCarlo()

# Modified ControlVariateMonteCarlo logic to debug
def debug_price(params, num_paths=100000, num_steps=50):
    underlying_price = params.underlying_price
    strike_price = params.strike_price
    time_to_expiry = params.time_to_expiry
    volatility = params.volatility
    risk_free_rate = params.risk_free_rate
    delta_time = time_to_expiry / num_steps

    rng = np.random.default_rng(42)
    brownian_increments = rng.standard_normal((num_paths, num_steps)) * np.sqrt(delta_time)
    brownian_motion = np.cumsum(brownian_increments, axis=1)

    time_grid = np.linspace(delta_time, time_to_expiry, num_steps)
    paths = underlying_price * np.exp(
        (risk_free_rate - 0.5 * volatility**2) * time_grid + volatility * brownian_motion
    )
    terminal_prices = paths[:, -1]

    payoff_standard = np.maximum(terminal_prices - strike_price, 0)
    
    raw_price = np.mean(payoff_standard) * np.exp(-risk_free_rate * time_to_expiry)
    print(f"Raw MC Price (without CV): {raw_price}")
    
    # Rest of CV logic...
    geometric_mean = np.exp(np.mean(np.log(paths), axis=1))
    payoff_geometric = np.maximum(geometric_mean - strike_price, 0)
    cov_matrix = np.cov(payoff_standard, payoff_geometric)
    beta = cov_matrix[0, 1] / cov_matrix[1, 1]
    expected_geo_payoff = np.mean(payoff_geometric)
    payoff_cv = payoff_standard - beta * (payoff_geometric - expected_geo_payoff)
    cv_price = np.mean(payoff_cv) * np.exp(-risk_free_rate * time_to_expiry)
    print(f"CV Price: {cv_price}")

debug_price(params)
