from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


def main() -> int:
    backend = read("services/api/app/marina_assistant.py")
    knowledge = read("services/api/app/marina_assistant_knowledge.md")
    entry = read("services/api/app/app_entry.py")
    admin = read("apps/admin/components/AdminShell.tsx")
    staff = read("apps/staff/components/StaffRoleGateway.tsx")
    admin_widget = read("apps/admin/components/MarinaAiAssistant.tsx")
    staff_widget = read("apps/staff/components/MarinaAiAssistant.tsx")
    kitchen = read("apps/staff/components/KitchenEntry.tsx")
    waiter = read("apps/staff/components/WaiterEntry.tsx")

    require('prefix="/api/v1/assistant"' in backend, "assistant endpoint prefix")
    require("Depends(current_user)" in backend, "server session is source of role truth")
    require('"read_only": True' in backend, "read-only boundary")
    require("TECH_BLOCK" in backend and "DIRTY" in backend and "IN_INSPECTION" in backend, "core room-state knowledge")
    require("marina_assistant_knowledge.md" in backend and "_select_manual_context" in backend, "operational manual retrieval wired")
    require("## CHECK-IN" in knowledge and "## CHECK-OUT" in knowledge, "manual includes check-in/out")
    require("## Работа горничной" in knowledge and "## Работа техника" in knowledge, "manual includes staff workflows")
    require("## Запрещённые действия" in knowledge and "## Типовые ошибки" in knowledge, "manual includes safety/troubleshooting")
    require("Never reveal or request passwords" in backend, "secret protection")
    require('"store": False' in backend, "OpenAI response storage disabled")
    require("async def _live_context" in backend and "async def _safe_live_context" in backend, "live read-only context wired")
    require('LIVE_HOTEL_ROLES = {"OWNER", "MANAGER", "RECEPTION"}' in backend, "hotel live scope is role bounded")
    require('role == "MAID"' in backend and "HOUSEKEEPING" in backend, "housekeeping live scope")
    require('role == "TECHNICIAN"' in backend and "MAINTENANCE" in backend, "maintenance live scope")
    require("LIVE_DINING_ROLES" in backend and "kitchen_orders" in backend, "dining live scope")
    require('"bookingAgentId" AS agent_id' in backend and '"agentId"=$2' in backend, "agent live scope is bound to authenticated bookingAgentId")
    require("AGENT_ACCOUNT_NOT_LINKED_OR_INACTIVE" in backend, "agent live context fails closed when account is not linked")
    require('"scope_rule": "Only rows whose agentId equals the authenticated user\'s bookingAgentId are included."' in backend, "agent context documents strict agency isolation")
    require("LIVE_CONTEXT_TEMPORARILY_UNAVAILABLE" in backend, "live data failure degrades safely")
    require('"live_context": live_context' in backend, "model prompt receives server live context")
    require('"live_context_available"' in backend, "chat response exposes live-context availability flag")
    require("_navigation_suggestion" in backend and '"navigation": _navigation_suggestion' in backend, "role-safe navigation hint returned")
    require('"live_read_only": True' in backend, "capabilities expose live read-only mode")
    require('"occupancy"' in backend and '"vacant_sellable_rooms"' in backend and '"occupancy_percent"' in backend, "owner live context includes factual occupancy")
    require('"active_reservations"' in backend and '"remaining_kgs"' in backend, "owner live context includes active reservations and balances")
    require('"finance"' in backend and '"confirmed_payments_today_kgs"' in backend and '"debtor_count"' in backend, "owner live context includes finance snapshot")
    require('"task_counts"' in backend and '"active_inventory_holds"' in backend, "owner live context includes operations and inventory holds")
    require('"reason": row["reason"]' in backend and '"usage_category": row["usage_category"]' in backend, "room attention includes block reason and usage")
    require('"guest_first_name"' in backend and '"phone"' not in backend.split("async def _live_context",1)[1].split("class AssistantMessage",1)[0], "live context omits phone fields")
    require('"email"' not in backend.split("async def _live_context",1)[1].split("class AssistantMessage",1)[0], "live context omits email fields")
    require("ASSISTANT_MAX_OUTPUT_TOKENS" in backend, "assistant output token cap")
    require("marina_assistant_router" in entry and "include_router(marina_assistant_router)" in entry, "router composed")
    require('import MarinaAiAssistant from "./MarinaAiAssistant"' in admin, "admin imports assistant")
    require("<MarinaAiAssistant" in admin, "admin mounts assistant")
    require('import MarinaAiAssistant from "./MarinaAiAssistant"' in staff, "staff imports assistant")
    require("<MarinaAiAssistant" in staff, "staff mounts assistant")
    require("/core/api/v1/assistant/chat" in admin_widget, "admin widget calls canonical endpoint")
    require("/core/api/v1/assistant/chat" in staff_widget, "staff widget calls canonical endpoint")
    require("current_screen" in admin_widget and "current_screen" in staff_widget, "screen context forwarded")
    require("onNavigate" in admin_widget and "onNavigate" in admin, "assistant navigation is wired")
    require("Обратитесь к администратору системы" not in admin_widget and "Обратитесь к администратору системы" not in staff_widget, "generic admin fallback removed")
    require('<MarinaAiAssistant screen="KITCHEN"' in kitchen, "kitchen mounts assistant")
    require('<MarinaAiAssistant screen="WAITER"' in waiter, "waiter mounts assistant")
    print("MARINA_AI_EMBEDDED_CONTRACT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
