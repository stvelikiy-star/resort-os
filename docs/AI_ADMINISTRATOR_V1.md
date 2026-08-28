# Three Crowns AI Administrator V1

Status: IMPLEMENTED IN INTEGRATION BRANCH / PROVIDER CREDENTIALS NOT CONNECTED.

## Channels

- Website: `3korony.com -> Resort Core public AI admin endpoint`.
- WhatsApp: `GREEN API -> n8n -> Resort Core -> OpenAI -> GREEN API`.

The two channels share Resort Core as the only hotel truth source. AI never owns room inventory, live pricing, payment or reservation confirmation.

## Website AI administrator

UI component:
- `apps/web/components/AiAdministratorWidget.tsx`
- mounted globally from `apps/web/app/layout.tsx`
- styling: `apps/web/app/ai-admin.css`

Core endpoint:
- `GET /api/v1/public/ai-admin/capabilities`
- `POST /api/v1/public/ai-admin/chat`

The widget contains an explicit date/guest checker. When the guest asks for exact dates, the request is resolved through Core `check-availability`; only returned sellable categories and totals may be shown.

The public AI endpoint:
- loads approved guest facts from the same Core facts source used by automation;
- loads current room-type inventory metadata;
- optionally executes Core availability for explicit dates/guest count;
- sends only the verified bundle to the configured OpenAI model;
- rate-limits public requests per client address;
- never confirms a Reservation or payment;
- never invents prepayment amount/terms/method.

## WhatsApp / GREEN API n8n workflow

Import:

`automation/n8n/whatsapp-green-ai-admin.json`

Flow:

1. receive `incomingMessageReceived` from GREEN API;
2. normalize text/chat/message id;
3. load verified hotel facts from Resort Core using `X-Resort-Service-Key`;
4. use OpenAI only to extract intent/date/guest facts from the guest message;
5. when exact dates + adults are available, call Core `GET /api/v1/booking/check-availability`;
6. build a verified context containing only Core hotel facts and sellable availability;
7. use OpenAI to compose a short reply in the guest language;
8. send the text through GREEN API `sendMessage`.

Current template is intentionally `active:false`. Do not activate it until the real GREEN API instance and OpenAI credentials are connected and webhook security is configured.

## Required production environment

Core / website AI:
- `OPENAI_API_KEY`
- `OPENAI_API_BASE_URL`
- `OPENAI_PUBLIC_ASSISTANT_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `AI_ADMIN_MAX_MESSAGES`
- `AI_ADMIN_RATE_LIMIT_PER_MINUTE`

n8n / WhatsApp:
- `RESORT_CORE_URL`
- `AUTOMATION_SERVICE_KEY`
- `OPENAI_API_KEY`
- `OPENAI_API_BASE_URL`
- `OPENAI_WHATSAPP_MODEL` (or `OPENAI_SALES_MODEL` fallback)
- `GREEN_API_URL`
- `GREEN_API_ID_INSTANCE`
- `GREEN_API_TOKEN_INSTANCE`
- `GREEN_API_WEBHOOK_SECRET`

No real secrets are committed.

## GREEN API connection procedure

1. Create/authorize the hotel WhatsApp instance in GREEN API.
2. Store `idInstance` and `apiTokenInstance` only in deployment secrets/environment.
3. Import `whatsapp-green-ai-admin.json` into the production n8n instance.
4. Configure the GREEN API incoming webhook to the production n8n webhook URL.
5. Enable incoming message webhooks.
6. Apply webhook secret validation before activating the workflow.
7. Test from a non-staff WhatsApp number:
   - generic hotel question;
   - missing dates;
   - complete dates + adults/children;
   - unavailable dates;
   - booking intent;
   - attempt to force invented discount/payment/confirmation.
8. Confirm every live price shown in WhatsApp matches direct Core availability for the same input.
9. Confirm the workflow never says a ReservationRequest is a confirmed booking.

GREEN API send-message transport uses the provider endpoint form:
`POST {apiUrl}/waInstance{idInstance}/sendMessage/{apiTokenInstance}` with `chatId` and `message`.

## Truth / safety rules

- `ReservationRequest != Reservation`.
- No automatic global prepayment percentage.
- Manager decides payment amount, terms and method.
- AI cannot report payment received unless Core contains a manager-confirmed payment fact.
- Availability/price comes only from Core.
- UNKNOWN/PARTIAL facts are escalated instead of guessed.
- Public AI must not request passport or bank-card data.
- Provider failures are failures; they must not be described as successful delivery.

## Remaining activation blockers

1. Real OpenAI production key + selected model names.
2. Real GREEN API `idInstance` + `apiTokenInstance`.
3. Webhook secret enforcement on the active n8n endpoint.
4. External HTTPS deployment of Core/web/n8n.
5. End-to-end WhatsApp test on the real hotel number.

Until those are supplied and tested, status is IMPLEMENTED but NOT LIVE / NOT VERIFIED WITH REAL PROVIDERS.
