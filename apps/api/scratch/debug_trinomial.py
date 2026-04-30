import numpy as np

def price_trinomial(S, K, T, r, sigma, num_steps):
    dt = T / num_steps
    dx = sigma * np.sqrt(3 * dt)
    u = np.exp(dx)
    d = 1.0 / u
    
    nu = r - 0.5 * sigma**2
    pu = 0.5 * ((sigma**2 * dt + nu**2 * dt**2) / dx**2 + nu * dt / dx)
    pd = 0.5 * ((sigma**2 * dt + nu**2 * dt**2) / dx**2 - nu * dt / dx)
    pm = 1.0 - pu - pd
    
    j = np.arange(2 * num_steps + 1) - num_steps
    S_values = S * (u ** j)
    grid = np.maximum(S_values - K, 0)
    
    df = np.exp(-r * dt)
    for _ in range(num_steps):
        grid = df * (pu * grid[2:] + pm * grid[1:-1] + pd * grid[:-2])
        
    return grid[0]

print(price_trinomial(100, 100, 1, 0.05, 0.2, 500))
