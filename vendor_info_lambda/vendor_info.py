import json
import uuid
from typing import Any, Dict, Optional

from vendor_service import (
    add_info_to_db,
    get_all_vendors_from_db,
    get_vendor_info_by_id_or_name,
    get_security_instances_by_vendor,
    is_admin_claim,
)


def lambda_handler(event, context):
    route_key = _safe_get(event, 'routeKey')
    if not route_key:
        return _bad_request('No routeKey found')

    if route_key == 'GET /vendors/all':
        return get_all_vendors_from_db()

    if route_key.startswith('GET /vendor/'):
        return _handle_get_vendor(event)

    if route_key.startswith('POST '):
        return _handle_post_vendor(event)

    return _bad_request('Invalid routeKey')


def _handle_get_vendor(event: Dict[str, Any]):
    vendor_identifier = _extract_vendor_identifier(event)
    if not vendor_identifier:
        return _bad_request('Vendor identifier missing')

    if _path(event).endswith('security-instances'):
        return get_security_instances_by_vendor(vendor_identifier)

    return _fetch_vendor_by_identifier(vendor_identifier)


def _fetch_vendor_by_identifier(identifier: str):
    try:
        return get_vendor_info_by_id_or_name(id=uuid.UUID(identifier))
    except (ValueError, TypeError):
        return get_vendor_info_by_id_or_name(vendor_name=identifier)


def _handle_post_vendor(event: Dict[str, Any]):
    if not is_admin_claim(event):
        return {'statusCode': 403, 'body': json.dumps('Forbidden: Admins only')}

    payload = event.get('body')
    data = json.loads(payload) if isinstance(payload, str) else (payload or {})

    return add_info_to_db(
        data.get('vendors', []),
        update_all_fields=data.get('updateAllFields', True),
        model=data.get('model', 'sonar'),
    )


def _extract_vendor_identifier(event: Dict[str, Any]) -> Optional[str]:
    params = event.get('pathParameters') or {}
    identifier = params.get('id_or_name')
    if identifier:
        return identifier

    parts = _path(event).split('/')
    if len(parts) >= 2 and parts[0] == 'vendor':
        return parts[1]
    return None


def _path(event: Dict[str, Any]) -> str:
    path = event.get('rawPath') or event.get('path') or ''
    return path.strip('/')


def _safe_get(event: Optional[Dict[str, Any]], key: str):
    if isinstance(event, dict):
        return event.get(key)
    return None


def _bad_request(message: str):
    return {'statusCode': 400, 'body': json.dumps(f'Bad Request: {message}')}


