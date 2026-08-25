from .automation import router as automation_router
from .booking_admin import router as booking_admin_router
from .main import app
from .operations import router as operations_router
from .stays import router as stays_router
from .telegram_auth import router as telegram_auth_router

# Composition layer keeps the public baseline routes stable while allowing
# domain modules to evolve independently.
app.include_router(booking_admin_router)
app.include_router(operations_router)
app.include_router(stays_router)
app.include_router(telegram_auth_router)
app.include_router(automation_router)
app.version = "0.6.0"
