from .ai_sales import router as ai_sales_router
from .analytics_reports import router as analytics_reports_router
from .automation import router as automation_router
from .automation_read import router as automation_read_router
from .booking_admin import router as booking_admin_router
from .channel_outbound import router as channel_outbound_router
from .communication_ingest import router as communication_ingest_router
from .crm_sync import router as crm_sync_router
from .google_control import router as google_control_router
from .growth_control import router as growth_control_router
from .guest_crm import router as guest_crm_router
from .guest_os import admin_router as guest_os_admin_router
from .guest_os import public_router as guest_os_public_router
from .guest_requests import router as guest_requests_router
from .guest_services import router as guest_services_router
from .health import router as health_router
from .hotel_finance import router as hotel_finance_router
from .inbox import router as inbox_router
from .main import app
from .manager_dashboard import router as manager_dashboard_router
from .observability import install_observability
from .operations import router as operations_router
from .operations_assignment import router as operations_assignment_router
from .operations_history import router as operations_history_router
from .owner_intelligence import router as owner_intelligence_router
from .owner_pace import admin_router as owner_pace_admin_router
from .owner_pace import automation_router as owner_pace_automation_router
from .pms_bulk_tasks import router as pms_bulk_tasks_router
from .pms_chessboard import router as pms_chessboard_router
from .pms_chessboard_read import router as pms_chessboard_read_router
from .pms_control_snapshot import router as pms_control_snapshot_router
from .pms_reservation_create import router as pms_reservation_create_router
from .public_ai_admin import router as public_ai_admin_router
from .realtime import router as realtime_router
from .reception_reservations import router as reception_reservations_router
from .reservation_detail import router as reservation_detail_router
from .reservation_payments import router as reservation_payments_router
from .room_detail import router as room_detail_router
from .site_content import router as site_content_router
from .staff_control import router as staff_control_router
from .staff_guest_requests import router as staff_guest_requests_router
from .staff_task_reports import router as staff_task_reports_router
from .staff_voice import router as staff_voice_router
from .stays import router as stays_router
from .telegram_auth import router as telegram_auth_router
from .telegram_sales import router as telegram_sales_router

install_observability(app)

# Composition layer keeps the public baseline routes stable while allowing
# domain modules to evolve independently.
app.include_router(health_router)
app.include_router(site_content_router)
app.include_router(public_ai_admin_router)
app.include_router(guest_os_public_router)
app.include_router(guest_requests_router)
app.include_router(booking_admin_router)
app.include_router(reception_reservations_router)
app.include_router(reservation_detail_router)
app.include_router(reservation_payments_router)
app.include_router(room_detail_router)
app.include_router(staff_control_router)
app.include_router(hotel_finance_router)
app.include_router(analytics_reports_router)
app.include_router(owner_intelligence_router)
app.include_router(guest_crm_router)
app.include_router(owner_pace_admin_router)
app.include_router(growth_control_router)
app.include_router(pms_chessboard_read_router)
app.include_router(pms_chessboard_router)
app.include_router(pms_reservation_create_router)
app.include_router(pms_control_snapshot_router)
app.include_router(pms_bulk_tasks_router)
app.include_router(guest_os_admin_router)
app.include_router(guest_services_router)
app.include_router(operations_router)
app.include_router(operations_assignment_router)
app.include_router(operations_history_router)
app.include_router(staff_guest_requests_router)
app.include_router(staff_task_reports_router)
app.include_router(stays_router)
app.include_router(telegram_auth_router)

# Direct provider adapters are retained as optional/reference integrations.
# Client-channel orchestration for Three Crowns V1 is owned by n8n.
app.include_router(telegram_sales_router)
app.include_router(staff_voice_router)

app.include_router(automation_router)
app.include_router(automation_read_router)
app.include_router(owner_pace_automation_router)
app.include_router(crm_sync_router)
app.include_router(google_control_router)
app.include_router(communication_ingest_router)
app.include_router(inbox_router)
app.include_router(channel_outbound_router)
app.include_router(ai_sales_router)
app.include_router(realtime_router)
app.include_router(manager_dashboard_router)

# NFC implementation remains dormant in source and is intentionally not composed
# into the active Resort Core application until the owner explicitly reactivates it.
app.version = "0.43.0"
