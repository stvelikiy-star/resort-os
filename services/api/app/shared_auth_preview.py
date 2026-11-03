"""Close every unrelated HTTP/WS route in the opt-in shared-auth staging slice."""
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
            ('GET', '/health/ready'), ('GET', '/health/live'),
        }
        try:
            auth.shared_auth_preview_guard()
            valid = (scope.get('method'), scope.get('path')) in allowed
            if scope.get('method') == 'OPTIONS':
                valid = scope.get('path') in {p for _, p in allowed}
            if not valid:
                raise HTTPException(503, detail='Only authentication is available in the shared staging preview')
        except HTTPException as error:
            if scope['type'] == 'websocket':
                return await send({'type': 'websocket.close', 'code': 1008})
            return await JSONResponse({'detail': error.detail}, status_code=error.status_code)(scope, receive, send)
        return await self.app(scope, receive, send)
