"""
data_sources/ — Free real-data API integrations.

Every source is optional: it returns None (or '') when its API key is absent
or the network call fails.  Tools gracefully fall back to AI estimates.

Sources
-------
fema        FEMA NFHL flood zone classification     (no key needed)
census      US Census ACS 5-year estimates          (free key optional)
fred        FRED / Freddie Mac mortgage rates       (free key required)
hud         HUD Fair Market Rents by ZIP            (free token required)
walk_score  Walk Score, Transit Score, Bike Score   (free key required)

Free key registration
---------------------
FRED:        https://fred.stlouisfed.org/docs/api/api_key.html
Census:      https://api.census.gov/data/key_signup.html
HUD:         https://www.huduser.gov/hudapi/public/register.php
Walk Score:  https://www.walkscore.com/professional/api.php
"""

from data_sources.fema       import get_flood_zone
from data_sources.census     import get_acs_data
from data_sources.fred       import get_mortgage_rates
from data_sources.hud        import get_fair_market_rents
from data_sources.walk_score import get_walk_score

__all__ = [
    "get_flood_zone",
    "get_acs_data",
    "get_mortgage_rates",
    "get_fair_market_rents",
    "get_walk_score",
]
