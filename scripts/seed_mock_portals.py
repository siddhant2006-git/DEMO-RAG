#!/usr/bin/env python
"""Ensures data/mock_portals/ has the fixture files the mock verification
adapters read (gst.json, udyam.json, debarment.json). Idempotent — running
it again never overwrites an existing fixture, so local edits to the mock
data survive.
"""
import json
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parents[1] / "data" / "mock_portals"

DEFAULTS = {
    "gst.json": {
        "27AAAPL1234C1Z5": {
            "status": "ACTIVE",
            "legal_name": "Ganga Infra Projects Pvt Ltd",
            "registration_date": "2018-04-01",
            "filing_status": "REGULAR",
            "avg_annual_turnover": 41000000,
            "turnover_currency": "INR",
            "turnover_period": "FY2022-23 to FY2024-25",
        },
        "07BBCPL5678D1Z2": {
            "status": "ACTIVE",
            "legal_name": "Bharat Steelworks Ltd",
            "registration_date": "2015-09-12",
            "filing_status": "REGULAR",
            "avg_annual_turnover": 92000000,
            "turnover_currency": "INR",
            "turnover_period": "FY2022-23 to FY2024-25",
        },
        "29CCDPL9012E1Z8": {
            "status": "CANCELLED",
            "legal_name": "Southern Traders & Co",
            "registration_date": "2012-03-20",
            "cancellation_date": "2024-11-05",
            "filing_status": "SUSPENDED",
            "avg_annual_turnover": 18000000,
            "turnover_currency": "INR",
            "turnover_period": "FY2022-23 to FY2024-25",
        },
    },
    "udyam.json": {
        "UDYAM-DL-01-1234567": {
            "valid": True,
            "enterprise_name": "Ganga Infra Projects Pvt Ltd",
            "category": "Small",
            "registration_date": "2021-06-15",
        },
        "UDYAM-MH-05-7654321": {
            "valid": True,
            "enterprise_name": "Bharat Steelworks Ltd",
            "category": "Medium",
            "registration_date": "2019-02-10",
        },
    },
    "debarment.json": {
        "listed_gstins": ["29CCDPL9012E1Z8"],
        "listed_pans": [],
    },
}


def main() -> None:
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in DEFAULTS.items():
        path = MOCK_DIR / filename
        if path.exists():
            print(f"skip (exists): {path}")
            continue
        path.write_text(json.dumps(content, indent=2), encoding="utf-8")
        print(f"wrote: {path}")


if __name__ == "__main__":
    main()
