"""Test all dashboard page endpoints."""
import requests

pages = {
    "Home":       "http://localhost:8501",
    "Market":     "http://localhost:8501/Market_Overview",
    "Performance":"http://localhost:8501/Fund_Performance",
    "Demographics":"http://localhost:8501/Investor_Demographics",
    "Portfolio":  "http://localhost:8501/Portfolio_Analytics",
}

ok = 0
for name, url in pages.items():
    try:
        r = requests.get(url, timeout=15)
        status = "OK" if r.status_code == 200 else "FAIL"
        if r.status_code == 200:
            ok += 1
        print(f"[{status}] {name:20s} -> HTTP {r.status_code}")
    except Exception as e:
        print(f"[FAIL] {name:20s} -> {e}")

print(f"\nPages OK: {ok}/{len(pages)}")
