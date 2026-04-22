from decimal import Decimal
from datetime import date, datetime


def make_json_safe(obj):
    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, tuple):
        return [make_json_safe(i) for i in obj]

    if isinstance(obj, list):
        return [make_json_safe(i) for i in obj]

    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    return obj