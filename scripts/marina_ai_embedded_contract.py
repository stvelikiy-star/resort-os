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
    live_context = read("services/api/app/marina_assistant_context.py")
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
    require("build_assistant_live_context" in backend, "live PMS context wired")
    require("reservation_requests" in live_context and "operational_tasks" in live_context, "live context reads operational facts")
    require("AGENT_ROLE" in live_context and "bookingAgentId" in live_context, "agent context is scoped to linked agency")
    require("contains_guest_pin" in live_context and "role_filtered" in live_context, "live context privacy boundary")
    require("TECH_BLOCK" in backend and "DIRTY" in backend and "IN_INSPECTION" in backend, "core room-state knowledge")
    require("marina_assistant_knowledge.md" in backend and "_select_manual_context" in backend, "operational manual retrieval wired")
    require("## CHECK-IN" in knowledge and "## CHECK-OUT" in knowledge, "manual includes check-in/out")
    require("## Работа горничной" in knowledge and "## Работа техника" in knowledge, "manual includes staff workflows")
    require("## Запрещённые действия" in knowledge and "## Типовые ошибки" in knowledge, "manual includes safety/troubleshooting")
    require("Never reveal or request passwords" in backend, "secret protection")
    require('"store": False' in backend, "OpenAI response storage disabled")
    require("ASSISTANT_MAX_OUTPUT_TOKENS" in backend, "assistant output token cap")
    require("marina_assistant_router" in entry and "include_router(marina_assistant_router)" in entry, "router composed")
    require('import MarinaAiAssistant from "./MarinaAiAssistant"' in admin, "admin imports assistant")
    require("<MarinaAiAssistant" in admin, "admin mounts assistant")
    require('import MarinaAiAssistant from "./MarinaAiAssistant"' in staff, "staff imports assistant")
    require("<MarinaAiAssistant" in staff, "staff mounts assistant")
    require("/core/api/v1/assistant/chat" in admin_widget, "admin widget calls canonical endpoint")
    require("/core/api/v1/assistant/chat" in staff_widget, "staff widget calls canonical endpoint")
    require("current_screen" in admin_widget and "current_screen" in staff_widget, "screen context forwarded")
    require('locale: "ru"' not in admin_widget and 'locale: "ru"' not in staff_widget, "assistant locale follows UI")
    require("onNavigate" in admin_widget and "onNavigate" in admin, "assistant navigation action wired")
    require("Обратитесь к администратору системы" not in admin_widget and "Обратитесь к администратору системы" not in staff_widget, "generic admin fallback removed")
    require('<MarinaAiAssistant screen="KITCHEN"' in kitchen, "kitchen mounts assistant")
    require('<MarinaAiAssistant screen="WAITER"' in waiter, "waiter mounts assistant")
    print("MARINA_AI_EMBEDDED_CONTRACT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
