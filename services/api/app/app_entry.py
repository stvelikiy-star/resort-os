from .ai_sales import router as ai_sales_router
from .automation import router as automation_router
from .automation_read import router as automation_read_router
from .booking_admin import router as booking_admin_router
from .channel_outbound import router as channel_outbound_router
from .communication_ingest import router as communication_ingest_router
from .health import router as health_router
from .inbox import router as inbox_router
from .main import app
from .manager_dashboard import router as manager_dashboard_router
from .nfc import router as nfc_router
from .nfc_reporting import router as nfc_reporting_router
from .observability import install_observability
from .operations import router as operations_router
from .operations_history import router as operations_history_router
from .realtime import router as realtime_router
from .reservation_detail import router as reservation_detail_router
from .room_detail import router as room_detail_router
from .staff_voice import router as staff_voice_router
from .stays import router as stays_router
from .telegram_auth import router as telegram_auth_router
from .telegram_sales import router as telegram_sales_router

install_observability(app)

# Composition layer keeps the public baseline routes stable while allowing
# domain modules to evolve independently.
app.include_router(health_router)
app.include_router(booking_admin_router)
app.include_router(reservation_detail_router)
app.include_router(room_detail_router)
app.include_router(operations_router)
app.include_router(operations_history_router)
app.include_router(stays_router)
app.include_router(telegram_auth_router)

# Direct provider adapters are retained as optional/reference integrations.
# Client-channel orchestration for Three Crowns V1 is owned by n8n.
app.include_router(telegram_sales_router)
app.include_router(staff_voice_router)

app.include_router(automation_router)
app.include_router(automation_read_router)
app.include_router(communication_ingest_router)
app.include_router(inbox_router)
app.include_router(channel_outbound_router)
app.include_router(ai_sales_router)
app.include_router(realtime_router)
app.include_router(manager_dashboard_router)

# NFC remains composed for backward compatibility with existing implementation,
# but it is explicitly deferred from the active Three Crowns engineering plan.
app.include_router(nfc_router)
app.include_router(nfc_reporting_router)
app.version = "0.21.0"
