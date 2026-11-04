"""Close every unrelated HTTP/WS route in the opt-in shared-auth staging slice."""
import re

from fastapi import HTTPException
from starlette.responses import JSONResponse


class SharedAuthPreviewBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        from . import auth
        if not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED or scope['type'] == 'lifespan':
            return await self.app(scope, receive, send)
        allowed = {
            ('POST', '/api/v1/auth/login'), ('POST', '/api/v1/auth/logout'),
            ('GET', '/api/v1/auth/me'), ('GET', '/api/v1/auth/mode'),
            # Narrow, reviewed read-only management summary. Other workspaces remain closed.
            ('GET', '/api/v1/admin/dashboard'),
            ('GET', '/api/v1/pms/grid'),
            # Reception bookings are read-only and bound to authenticated property.
            ('GET', '/api/v1/admin/reception/reservations'),
            # Transactional PMS booking and hotel-scoped 60-minute inventory HOLDs.
            # Payment, stay transitions and unreviewed PMS writes stay closed.
            ('POST', '/api/v1/admin/pms/reservations/new/preview'),
            ('POST', '/api/v1/admin/pms/reservations/new/commit'),
            # Owner/manager schedule edits; reservation UUID matcher below.

            ('GET', '/api/v1/admin/pms/holds'),
            ('POST', '/api/v1/admin/pms/holds'),
            # Reviewed hotel-scoped staff lifecycle (stage 2 / isolated staging only).
            ('GET', '/api/v1/admin/staff/overview'),
            ('POST', '/api/v1/admin/staff'),
            ('GET', '/health/ready'), ('GET', '/health/live'),
        }
        try:
            auth.shared_auth_preview_guard()
            method, path = scope.get('method'), scope.get('path')
            staff_patch = (scope['type'] == 'http' and method in {'PATCH', 'OPTIONS'} and
                           isinstance(path, str) and re.fullmatch(
                               r'/api/v1/admin/staff/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',
                               path) is not None)
            pms_cancel = (scope['type'] == 'http' and method in {'POST', 'OPTIONS'} and
                          isinstance(path, str) and re.fullmatch(
                              r'/api/v1/admin/pms/reservations/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/cancel',
                              path) is not None)
            hold_item = (scope['type'] == 'http' and method in {'GET', 'DELETE', 'OPTIONS'} and
                         isinstance(path, str) and re.fullmatch(
                             r'/api/v1/admin/pms/holds/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',
                             path) is not None)
            schedule_change = (scope['type'] == 'http' and method in {'POST', 'OPTIONS'} and
                               isinstance(path, str) and re.fullmatch(
                                   r'/api/v1/admin/pms/reservations/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/schedule/(?:preview|commit)',
                                   path) is not None)
            schedule_read = (scope['type'] == 'http' and method in {'GET', 'OPTIONS'} and
                             isinstance(path, str) and re.fullmatch(
                                 r'/api/v1/admin/pms/reservations/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/schedule',
                                 path) is not None)
            internal_payment = (scope['type'] == 'http' and
                                isinstance(path, str) and re.fullmatch(
                                    r'/api/v1/admin/booking/reservations/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/(?:payments|acquiring-readiness|cancellation-finance-review)',
                                    path) is not None and (
                                        method == 'OPTIONS' or
                                        (method == 'POST' and path.endswith('/payments')) or
                                        (method == 'GET' and (
                                            path.endswith('/acquiring-readiness') or
                                            path.endswith('/cancellation-finance-review')))
                                    ))
            stay_transition = (scope['type'] == 'http' and method in {'POST', 'OPTIONS'} and
                               isinstance(path, str) and re.fullmatch(
                                   r'/api/v1/admin/stays/reservations/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}/check-(?:in|out)',
                                   path) is not None)
            reception_detail = (scope['type'] == 'http' and method in {'GET', 'OPTIONS'} and
                                isinstance(path, str) and re.fullmatch(
                                    r'/api/v1/admin/reception/reservations/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',
                                    path) is not None)
            valid = (method, path) in allowed or staff_patch or pms_cancel or hold_item or schedule_change or schedule_read or internal_payment or stay_transition or reception_detail
            if method == 'OPTIONS':
                valid = path in {p for _, p in allowed} or staff_patch or pms_cancel or hold_item or schedule_change or schedule_read or internal_payment or stay_transition or reception_detail
            if not valid:
                raise HTTPException(503, detail='Only authentication is available in the shared staging preview')
        except HTTPException as error:
            if scope['type'] == 'websocket':
                return await send({'type': 'websocket.close', 'code': 1008})
            return await JSONResponse({'detail': error.detail}, status_code=error.status_code)(scope, receive, send)
        return await self.app(scope, receive, send)
