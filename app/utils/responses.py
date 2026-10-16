"""Consistent JSON response helpers."""

from flask import jsonify


def success(data=None, status=200, message=None, meta=None):
    if message:
        if isinstance(data, dict):
            data = {**data, "message": message}
        elif data is None:
            data = {"message": message}
    if meta is not None:
        if isinstance(data, dict):
            data = {**data, "meta": meta}
        else:
            data = {"items": data, "meta": meta}
    payload = {"status": "success", "data": data}
    return jsonify(payload), status


def error(message, status=400, code="bad_request", details=None):
    payload = {"status": "error", "message": message}
    if details:
        payload["errors"] = {
            field: value if isinstance(value, list) else [value]
            for field, value in details.items()
        }
    return jsonify(payload), status