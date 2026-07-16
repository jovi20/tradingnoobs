import os
import sys
import types


os.environ.setdefault("RELEASE_PROFILE", "DEVELOPMENT_FULL")
os.environ.setdefault(
    "DEPLOYMENT_CAPABILITY_ALLOWLIST",
    "MARKET,BROKER_SYNC,AI_INSIGHTS,PDF_EXPORT,RISK_CARDS,OPEN_REGISTRATION",
)
sys.modules.setdefault("finnhub", types.SimpleNamespace(Client=lambda *args, **kwargs: object()))
sys.modules.setdefault("pandas", types.SimpleNamespace(DataFrame=object))
sys.modules.setdefault("numpy", types.SimpleNamespace())
sys.modules.setdefault("binance", types.SimpleNamespace())
sys.modules.setdefault("binance.spot", types.SimpleNamespace(Spot=lambda *args, **kwargs: object()))
