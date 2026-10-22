# MARINA SMART — максимальный технический аудит по проверяемым источникам
Дата: 2026-10-20. Репозиторий: stvelikiy-star/resort-os. Ветка: fix/marina-staging-preflight-20261020. Документ фиксирует подтверждённые факты и открытые проверки, а не обозначает коммерческую готовность.

## Проверенная конфигурация и источники
- GitHub Actions на коммите fa0c5cd9370c2d3b384de06e3bae5e12d91497e0: пять специализированных MARINA CI workflow завершились SUCCESS (образ API, PostgreSQL, изоляция/restore, тест готовности, полный стек с браузером).
- Миграции/запуск сервера, синтетический отель 12 номеров и три категории, API health/ready и публичная доступность — пройдены в временной PostgreSQL.
- Полный стек: Next.js web, admin, staff; owner login; preview → commit → overlap 409 → canonical grid — тест пройден.
- Chromium проверил owner grid, месяцы, 31 день, мобильный viewport 390px; это **ограниченный smoke**, не весь UX/дизайн и не полная приёмка всех разрешений.
- Two-Property Isolation and Restore CI проверял property-pinned отдельные API-инстансы, восстановление **синтетической** базы, роль/OTA/CSV/mapping сценарии. Не доказана безопасность единого общего API для произвольного числа отелей.
- В Railway проект MARINA SMART Pilot (6949a812-714a-4147-8c79-5a933d3ef732) пуст, сервисов и PostgreSQL нет; постоянного пилота нет.
- Релизный манифест release/marina-smart-current-candidate.json: INTERNAL_CANDIDATE_STAGING_REQUIRED, tenant_context_enabled=false, external_staging_verified=false, production_cutover_authorized=false, backup_restore_target_verified=false.
- Без изменений: реальная Three Crowns база и данные клиентов, согласованная компактная шахматка, роли, существующие интерфейсы, DNS, платежи.

## Технические риски

### P0 — блокируют промышленный запуск
1. **Постоянный stage и проверка фактического целевого окружения отсутствуют.** Марина-специфичный Ubuntu-пакет и безопасный первичный bootstrap теперь прошли CI, но CI работает на одноразовых ресурсах и не эквивалентен реальному серверу.
2. **Tenant/Property не принят как единый SaaS режим.** В auth.py и части API работает PROPERTY_CODE; переключатель MARINA_TENANT_CONTEXT_ENABLED по умолчанию отключён. Тестированы два property-pinned API, но единый API для многих tenants, весь auth/read/write/realtime/AI контур не проверен.
3. **Манифест релиза и ветки не сведены к утверждённому immutable commit.** Есть PR #234 (tenant), #240 (ручные OTA), #241 (CSV), #242 (mapping), #243 (старый Dockerfile) и текущий PR #244; ветки последних правок расходятся. Нельзя бесконтрольно смержить или объявить RC.
4. **Внешние OTA API не работают автоматически.** Booking/Airbnb/Ostrovok — ручные записи и нормализованный CSV, без официальных credentials, pull/webhook/outbound sync и retry reconciliation.
5. **Целевая backup/restore, WSS/HTTPS, браузерное принятие всех ролей, мониторинг и rollback** на постоянном сервере ещё не подтверждены.
6. **Секреты и платежи.** Реальный владелец/ключи в CI не используются. Для production — отдельное управление секретами/HTTPS/CookieSecure. Платежи, QR, MKassa должны оставаться выключенными до собственных тестов.

### P1 — важные недоработки
1. **Тарифы:** ночная сезонная цена реализована в price_room_type(), но отдельный end-to-end тест перехода сезонов добавлен позже основного CI и должен пройти. Проверить перекрытия тарифов, пустые даты и временные зоны.
2. **Роли:** OWNER/RECEPTION/MAID/TECHNICIAN/AGENT и обслуживание; видимость UI не равна server-side разрешениям. Требуется browser/API matrix для каждого сценария.
3. **AI:** интегрирован read-only помощник и knowledge/context, но в текущем CI нет подтверждённого live-провайдера и полноты доступа к бронированиям/финансам/задачам для всех ролей. Не выдавать результат модели за факты из БД.
4. **Брендинг:** в API pms_reservation_create.py booking_number генерируется с префиксом TC-, часть defaults PROPERTY_CODE=THREE_CROWNS, в некоторых текстах наследие Resort Core/Three Crowns, а гостевая web страница явно называет AK BERMET. Это риск перепутать клиента/бренд. **Нельзя менять согласованный UI без согласования**, но на новых инстансах требуется явная MARINA конфигурация и отдельная продуктовая политика номера брони.
5. **Локализация:** были тесты переключателя RU/KG/KZ/EN, но полный постраничный лингвистический аудит и все динамические сообщения ещё не подтверждены.
6. **Дизайн и мобильная UX-приёмка:** 390px browser smoke успешен; нет полноценного подтверждения планшета, доступности, сценариев ошибок, производительности и визуальной регрессии.

## Контрольные ворота (никакого production до выполнения)
- G1: согласовать актуальный commit/PR, выполнить CI + browser+season+isolation.
- G2: отдельное изолированное staging-окружение PostgreSQL/API/Web/Admin/Staff, HTTPS, WSS и health/readiness, мониторинг, без реальных клиентов.
- G3: два синтетических tenants и все запреты межотельного доступа; проверить любой доступ через API/AI/realtime/background.
- G4: полный browser E2E OWNER/ADMIN/RECEPTION/AGENT/MAID/TECHNICIAN/другие роли; бронь, HOLD, изменение, отмена, 60 ночей, сезоны, конфликты.
- G5: target backup→separate restore→row checksums и сценарий отката.
- G6: отдельная приёмка одного отеля и письменное разрешение на production; включение платежей/provider adapters только после их специальных тестов.

## План запуска
1. Закрыть и подтвердить CI на новой ветке, включая тест границы сезона.
2. Встроить тест ролевой матрицы и live AI evidence без секретов.
3. Проверить все несовместимые изменения веток PR #234/240/241/242/244 и сформировать единый RC.
4. Развернуть изолированный постоянный staging, сделать E2E+rollback; стоимость сервисов согласовать отдельно от проверки.
5. Только после приёмки связать реальные сайты отелей и проводить поэтапный onboarding.


## Обновление проверки — 2026-10-22

### Проверенный кандидат
- PR #244: `fix/marina-staging-preflight-20261020`; базовая ветка `marina-smart/channel-mappings-20261016`, базовый SHA `ded416371a62ab32167585ff9c8a92c729ef8a3c`.
- Текущий commit PR на момент проверки: `e7f3f94856e40201944f3e76386f030eae6744e8`; манифест фиксирует последний исходный/test commit `d7483660bff070556c060e9df0049d70749b7c65`.
- GitHub Actions на `e7f3f94`: 65 возвращённых workflow-запусков завершились `success`. У `Three Crowns Full Staging Gate` job `staging-full-gate` имеет статус `skipped`; это не внешняя staging-приёмка.
- Дополнительно подтверждены успешные jobs: MARINA Two-Property Isolation and Restore, Full Stack Synthetic Smoke, Ubuntu Hotel Fleet, API Image, AK BERMET и Public Browser.
- Локально на текущем дереве: hardening 405 checks, release contract 36 миграций/105 ограничений, 32 модульных теста, Python compile и diff check — успешно.

### Решение по размещению
- Решение владельца от 2026-10-22: Railway не использовать как обязательную инфраструктуру. Целевой контур — собственный Ubuntu-сервер и домен AI PROF KG.
- `compose.marina-fleet.yaml` — только синтетический стенд; его нельзя использовать для реальных данных гостиницы.
- `compose.production.yaml`, `.env.production.example` и `docs/SINGLE_SERVER_PRODUCTION_RUNBOOK.md` содержат значения и маршрутизацию Three Crowns (`3korony.com`, `THREE_CROWNS`, `/srv/three-crowns`). Их нельзя копировать на Marina-сервер без отдельной проверенной конфигурации.
- Общий MARINA multi-tenant runtime остаётся выключенным. Целевая схема — отдельная база, API, сеть, volume, настройки и backup-набор на каждый отель.

### Открытые блокеры до реального пилота
1. Выполнить read-only preflight на целевом Ubuntu-хосте; состояние сервера из этой рабочей среды не наблюдалось.
2. Проверить на реальном домене HTTPS/WSS, полный role/browser acceptance, шифрованный off-site backup, отдельное восстановление и откат.
3. Выполнить внешний staging на AI PROF KG Ubuntu, не затрагивая Three Crowns и клиентские данные.
4. OTA API и банковский эквайринг остаются выключенными/неподключёнными до официального доступа и провайдерских E2E. CI не доказывает подключение Booking.com/Airbnb/Ostrovok или банков.


## Проверка инфраструктурного этапа — 2026-10-22

- Текущий проверенный PR #244 commit: `73a9bf06167507adf808eb71f1e2ff905ec870b1`; 66/66 GitHub Actions workflow завершились успешно. Подтверждены MARINA PostgreSQL API smoke, полный синтетический стек, Ubuntu fleet CI и Ubuntu production package CI.
- Ранее открытые пункты «создать безопасный первичный provisioning» и «подготовить MARINA-пакет для Ubuntu» закрыты на уровне реализации и CI: bootstrap пустого отеля с первым OWNER, изолированный Compose/Caddy, fail-closed env preflight и production runbook готовы. CI не подтверждает работу на настоящем сервере.
- Остаток до реального пилота: preflight целевого Ubuntu, DNS/TLS/WSS, полный браузерный и ролевой E2E, проверка off-site backup/restore и rollback.
- `production_cutover_authorized=false`, `external_staging_verified=false`; `staging-full-gate` skipped. Никаких изменений реального сервера, DNS, production данных или платежей не делали.
