THREE CROWNS RESORT OS — REAL ADMIN / MAC LOCAL REVIEW
Version: Resort OS 0.62.2
Accepted executable product SHA: ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4

THIS IS NOT A STANDALONE DEMO HTML.
The archive contains the actual Resort OS repository code at the accepted executable boundary, including:
- apps/admin — real Admin/PMS UI
- services/api — real FastAPI Resort Core
- packages/database — PostgreSQL/Prisma schema and committed migrations
- data-intake — canonical Three Crowns rooms/rates
- apps/staff — staff interface

FIRST START ON MAC
1. Start Docker Desktop.
2. Open Terminal.
3. cd into this extracted folder.
4. Run:

   bash RUN_REAL_ADMIN_MAC.sh

5. When READY appears, the script opens:
   http://127.0.0.1:13001

OWNER LOGIN
user: owner_local
pass: TCReviewOwner2026Safe

OTHER LOCAL ROLE ACCOUNTS
Reception: reception_local / TCReviewReception2026Safe
Dining:    dining_local / TCReviewDining2026Safe
Maid:      maid_local / TCReviewMaid2026Safe
Tech:      tech_local / TCReviewTech2026Safe

WHAT THE START SCRIPT DOES
- starts a dedicated local PostgreSQL volume;
- applies the committed Prisma migrations;
- loads the canonical Three Crowns inventory and rate data;
- creates local review users in the real staff_users/auth system;
- builds and starts the actual Resort Core, Admin/PMS and Staff apps;
- verifies Admin -> Core -> PostgreSQL authentication before opening the browser.

NO SYNTHETIC RESERVATIONS ARE CREATED.
The chessboard starts from the canonical hotel inventory/rates; bookings that you create are written to the real local PostgreSQL database through Resort Core.

LOCAL REVIEW ONLY
Real bank/acquiring, WhatsApp/Green API, TTLock and other production providers remain disabled. This local package does not claim production deployment or external provider verification.

STOP WITHOUT DELETING LOCAL DATA
   bash STOP_REAL_ADMIN_MAC.sh

FULL RESET OF LOCAL REVIEW DATABASE
   RESET_REAL_ADMIN=1 bash RUN_REAL_ADMIN_MAC.sh

macOS Gatekeeper note:
Do not double-click shell files in Finder. Run the bash command above from Terminal; this avoids the Finder .command quarantine problem shown in the previous package.
