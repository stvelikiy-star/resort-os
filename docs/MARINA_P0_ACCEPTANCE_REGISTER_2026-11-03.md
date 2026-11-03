# MARINA SMART — P0: инвентаризация сред и единый протокол приёмки

Дата: 2026-11-03 (Asia/Bishkek).
Статус документа: **рабочий протокол, не подтверждение production-readiness**.
Репозиторий: `stvelikiy-star/resort-os`.
Зафиксированный исходный коммит: `8a68e48bd62d93c741f9444fd8141d512ca61e7d` (`prep/marina-shared-platform-20261103`).
Источник результатов CI: GitHub Actions, 2026-11-03. На этой ветке обнаружено 73 запуска, 72 `success` и 1 `failure` на более раннем SHA `88260ee06`. **Это 72 запуска рабочих процессов, не 72 отдельных end-to-end сценария.** Сводка не заменяет проверку обязательных gates для релизного SHA.

## I. Инварианты окружений (P0)

| Среда | Подтверждённая конфигурация в репозитории | Назначение | Защита и разрешённые изменения |
|---|---|---|---|
| `MARINA_DEMO` | `compose.marina-demo.yaml` | Только синтетическая публичная демонстрация | Никаких реальных GREEN-API, платежей, production-учётных данных, переноса тестовых данных в production |
| `MARINA_HOTEL01` | `compose.marina-fleet.yaml` | Отдельный приватный тестовый объект | Секреты и БД изолированы; изменения — только после снимка, идентификации работающих контейнеров и плана отката |
| Shared MARINA (цель) | `docs/MARINA_PRIMARY_PREPARATION.md`, `docs/MARINA_SHARED_AUTH_PREVIEW.md` | Будущая единая платформа | НЕ объявлять развёрнутой; проверять tenant/session/provider isolation до допуска |
| Production per-hotel package | `compose.marina-production.yaml` | Технический пакет для отдельного гостиничного стека | НЕ выдавать за готовую shared MARINA; не развёртывать до проверки хоста, DNS, backup, образов и onboarding |

Границы:
1. Нельзя переназначать код `MARINA_DEMO` или `MARINA_HOTEL01` под production.
2. Не включать tenant flag как обход проверки авторизации.
3. Не записывать секреты в GitHub, лог, отчёты и UI.
4. Не запускать миграции, seed, `docker compose up`, restart или изменение DNS как часть статического аудита.
5. Любое изменение должно иметь исходный SHA, целевой SHA, конкретный стек, backup ID, restore rehearsal, критерии отмены и журнал операций.
6. Другие проекты из монорепозитория не изменять.

## II. Проверенные факты и границы уверенности

| Факт | Доказательство | Статус |
|---|---|---|
| В репозитории присутствуют отдельные compose-файлы DEMO / fleet / production | `compose.marina-demo.yaml`, `compose.marina-fleet.yaml`, `compose.marina-production.yaml` | Подтверждено исходниками |
| DEMO отключает реальные платежи и AI-ключи в compose | `compose.marina-demo.yaml` | Подтверждено конфигурацией; runtime требуется сверить |
| Цель shared platform ещё не достигнута package per-hotel | `docs/MARINA_PRIMARY_PREPARATION.md` | Подтверждено документированными ограничениями |
| Привязка GreenAPI/QR и ограничения публичного DEMO описаны | `docs/MARINA_GREEN_QR_LAUNCH_2026-11-03.md` | Подтверждено кодовым контрактом/документацией, не живым сообщением |
| WhatsApp входящий webhook → CRM → ответ → фактическая доставка | Нет артефакта живого E2E с message ID | **НЕ ПРИНЯТО** |
| Выполнение CI | GitHub Actions для `prep/marina-shared-platform-20261103` | 72 success, 1 старое failure; успешный CI ≠ runtime |
| Фактические контейнеры на Ubuntu, DNS, сертификаты, состояние БД сегодня | В рамках этого протокола прямой доступ к хосту не выполнялся | **НЕ ПРОВЕРЕНО** |
| Готовность интеграции Booking.com, оплат, внешнего OTA | Не предъявлены действующие provider E2E | **НЕ ПРИНЯТО** |

## III. Единый протокол функциональной приёмки

Легенда: `CODE` — исходники/автотесты; `HOST` — запущенная целевая версия; `E2E` — сквозной бизнес-сценарий. Без `HOST+E2E` нельзя ставить `PASS` критической операции.

| ID | Приоритет | Проверка/критерий PASS | Вид доказательства | Итог |
|---|---|---|---|---|
| ENV-01 | P0 | Идентифицировать реальный контейнер, образ digest, commit, env-режим каждой среды | HOST | OPEN |
| ENV-02 | P0 | Отсутствие пересечений DB volume, network и секретов | HOST | OPEN |
| ENV-03 | P0 | Датированный backup, `pg_restore --list`, восстановление в отдельную БД, сравнение данных | HOST+E2E | OPEN |
| ENV-04 | P0 | HTTPS/домен и проверка реального ingress, cookie flags | HOST | OPEN |
| PMS-01 | P0 | Создание и чтение брони | HOST+E2E | OPEN |
| PMS-02 | P0 | Изменение дат и согласованность шахматки | HOST+E2E | OPEN |
| PMS-03 | P0 | HOLD, TTL, освобождение, гонка с обычной бронью | HOST+E2E | OPEN |
| PMS-04 | P0 | Отмена и возврат доступности | HOST+E2E | OPEN |
| PMS-05 | P0 | Оплата/отражение баланса без выдуманного статуса оплаты | HOST+E2E | OPEN |
| PMS-06 | P0 | Заселение и выселение | HOST+E2E | OPEN |
| PMS-07 | P0 | Параллельные брони одного номера не создают овербукинг | HOST+E2E | OPEN |
| AUTH-01 | P0 | Собственник выдаёт и отзывает permissions, повторная авторизация | HOST+E2E | OPEN |
| AUTH-02 | P0 | Owner/Manager/Reception/Maid/Technician/Cook/Waiter/Store/Agent/Guest: разрешённые и запрещённые операции | HOST+E2E | OPEN |
| AUTH-03 | P0 | Нет прямого доступа к чужому hotel ID через URL/API | HOST+E2E | OPEN |
| AUTH-04 | P0 | Два отеля с совпадающим username: корректная изоляция сессий | HOST+E2E | OPEN |
| AI-01 | P0 | AI доступен только утверждённым ролям и кабинету гостя | HOST+E2E | OPEN |
| AI-02 | P1 | AI работает по базе знаний именно своего отеля; не выдумывает цену и доступность | HOST+E2E | OPEN |
| WA-01 | P0 | QR авторизация из одного приватного отеля, token isolation | HOST+E2E | OPEN |
| WA-02 | P0 | Webhook, inbound, dedupe, верная привязка к гостинице | HOST+E2E | OPEN |
| WA-03 | P0 | Исходящий ответ с фактическим provider delivery ID | HOST+E2E | OPEN |
| WA-04 | P1 | Эскалация человеку, история CRM, отключение/повторное подключение | HOST+E2E | OPEN |
| CRM-01 | P1 | Заявка → гость → бронь → запись в историю без потерь | HOST+E2E | OPEN |
| FIN-01 | P1 | Оплаты, задолженности и отчёт совпадают с транзакциями | HOST+E2E | OPEN |
| LOCALE-01 | P1 | RU/KG/EN: основные кабинеты, ошибки, мобильные экраны | HOST+E2E | OPEN |
| OTA-01 | P1 | Подтверждённые provider credentials, import/change/cancel/reconcile без дублей | HOST+E2E | OPEN |
| PROD-01 | P0 | Реальный production: новый код объекта, host capacity, HTTPS, backups, monitoring, rollback | HOST+E2E | OPEN |

**OPEN** не означает «код отсутствует»: означает, что в этом аудите нет полного достаточного доказательства приёмки на целевом хосте.

## IV. Порядок исполнения и блокирующие правила

1. **Environment freeze:** идентификация реальной версии каждого окружения и непересекающихся persistent volumes; до окончания — никаких deploy/restart.
2. **Backup/restore:** отдельное проверенное восстановление из реального снапшота; если не проходит — релиз блокировать.
3. **PMS + RBAC:** на disposable/test hotel прогнать все P0-операции, фиксировать request ID, actor role, property ID и результат, без публикации персональных данных.
4. **WhatsApp:** проверять GREEN-API сначала в приватном тестовом hotel; никаких сообщений в публичном DEMO. Реальное сообщение и реальная доставка обязательны.
5. **Shared production design:** реализовать tenancy/login и onboarding независимо от прежней per-hotel topology, проверить два объекта и denial; до этого не объявлять shared production.
6. **P1:** CRM/финансы, языки, OTA, платежи, пользовательская и мобильная приёмка.
7. **Release gate:** зафиксировать release SHA, исходные артефакты, digest образов, snapshot, restore/rollback, тестовый протокол, sign-off. Только после — отдельное одобренное развёртывание.

## V. Запись результатов (копировать на каждую проверку)

```text
Test ID:
Дата и часовой пояс:
Env / hotel code (без PII):
Git SHA / container image digest:
Исполнитель / роль:
Начальные условия:
Тестовые шаги:
Ожидаемый результат:
Фактический результат:
HTTP / trace / message ID (секреты удалены):
Ссылка на артефакт:
Дефект / issue:
Повторная проверка:
PASS / FAIL / BLOCKED:
```

## VI. Непосредственно следующий безопасный шаг

Сопоставить ветку, из которой **фактически** запущен публичный DEMO, с `image digest` и текущим `git SHA` Ubuntu, не допуская предположения, что ветка `prep/marina-shared-platform-20261103` уже развёрнута. После этого проверить существующие read-only API и backup metadata. Никакие production endpoints, пароли и адреса не придумывать.

## VII. Подготовленная диагностика хоста (без изменений инфраструктуры)

В этой аудиторской ветке добавлен `scripts/marina_runtime_inventory_readonly.py`. Он читает только `git HEAD`, название ветки и состояние tracked-файлов, список контейнеров MARINA через `docker ps --all`, а также **только метаданные** файлов `marina-*.dump/.backup/.sql/.gz` в указанной папке. Не выводит значения env, секреты, Docker mount paths или содержимое базы.

На доверенном Ubuntu-хосте оператор может запустить:

```bash
python3 scripts/marina_runtime_inventory_readonly.py > marina-runtime-inventory-20261103.json
```

Проверка `MARINA P0 Runtime Inventory Safety CI` прошла на PR #272: https://github.com/stvelikiy-star/resort-os/actions/runs/41589504170 . Это тест безопасности диагностического кода **в GitHub CI**, а не доказательство его выполнения на Ubuntu. Проверка `git HEAD` НЕ подтверждает SHA работающих Docker-образов. Следующим отдельным шагом необходима проверка образов по digest, сетей, томов, backup restore и реальных endpoint’ов целевого хоста.

Подтверждённые успешные проверки базового коммита `8a68e48bd` включают:
- Full Stack Synthetic Smoke: https://github.com/stvelikiy-star/resort-os/actions/runs/41584060560
- Staff Roles CI: https://github.com/stvelikiy-star/resort-os/actions/runs/41584060713
- PMS Chessboard Mutation CI: https://github.com/stvelikiy-star/resort-os/actions/runs/41584060791
- MARINA Two-Property Isolation and Restore CI: https://github.com/stvelikiy-star/resort-os/actions/runs/41584060779

Эти проверки выполнялись на CI-окружениях; они не означают, что соответствующий SHA развёрнут на сервере.

## VIII. Разбор красного CI в общей монорепозитории — 03.11.2026

На SHA `d3617f316b` workflow `Three Crowns Full Staging Gate` завершился с ошибкой: https://github.com/stvelikiy-star/resort-os/actions/runs/41589592136

В шаге `Validate release/data truth and seed canonical hotel` проверка ожидает специфические тексты и данные гостиницы Three Crowns (пляж, пирс, размеры бассейна, roomCategories и контакт), которые не найдены в `apps/web/app/page.tsx` и `apps/web/lib/siteContent.ts`.

**Классификация:** cross-project regression / test scope mismatch, не доказанный дефект MARINA PMS. Не дополнять сайт чужими утверждениями ради прохождения теста. Не объявлять релиз зелёным, пока обязательные gates не определены по продуктовой области и failure не разрешён корректным владельцем Three Crowns.

Ветка аудита MARINA не меняет `apps/web`, `siteContent.ts`, данные гостиницы Three Crowns или этот staging gate. Требуется самостоятельная диагностика ownership и корректного scope-gating в общем CI с минимальными изменениями вне продуктов.

## IX. Идентификаторы работающих Docker-образов

`scripts/marina_runtime_inventory_readonly.py` теперь запрашивает у конкретных контейнеров MARINA только `docker inspect --type container --format '{{.Image}}'`. Это иммутабельный локальный image ID (`sha256:...`), который можно сопоставлять между замерами. Скрипт НЕ читает Docker Env, mounts или network settings. Локальный image ID сам по себе не доказывает source SHA или registry digest: provenance проверяется отдельно через labels/build metadata и deployment log, с исключением секретов.

Первоначальный CI проверки безопасности диагностического скрипта прошёл на старом коммите; после дополнения идентификаторами образов необходимо дождаться CI нового коммита. Эти метаданные пока не собраны на Ubuntu.

## X. Fail-closed review host metadata

Для исключения ложного «Готово» создан второй локальный инструмент `scripts/marina_runtime_inventory_review.py`. Он разбирает JSON от `marina_runtime_inventory_readonly.py` и выпускает статус `INCOMPLETE` либо `INVENTORY_METADATA_COLLECTED`, **но никогда** не выдаёт `release_approved=true`. Даже полный перечень контейнеров и файлов бэкапов не является проверкой восстановления или PMS.

Применение после копирования подготовленных скриптов на доверенную Ubuntu (не запускалось в текущей сессии):

```bash
python3 scripts/marina_runtime_inventory_readonly.py > marina-runtime-inventory.json
python3 scripts/marina_runtime_inventory_review.py marina-runtime-inventory.json
```

Оба инструмента работают без изменения Docker, конфигурации или БД. Инвентаризация читает только ограниченные метаданные. До передачи отчёта за пределы доверенного окружения необходимо проверить имена контейнеров и файлов, если они содержат внутренние сведения.

До реальной проверки Ubuntu поле `backup_restored` всегда `false`; статус `INVENTORY_METADATA_COLLECTED` не означает `PASS` production. Тесты этого контракта выполняются в `MARINA P0 Runtime Inventory Safety CI`.

## XI. Проверка читаемости резервных архивов без восстановления — 03.11.2026

Скрипт `scripts/marina_runtime_inventory_readonly.py` дополнен проверкой сигнатуры `PGDMP` и командой `pg_restore --list` только для локальных файлов `marina-*.dump` и `marina-*.backup`. Вывод списка объектов БД намеренно не сохраняется в JSON, чтобы не публиковать структуру и данные. При отсутствующей утилите `pg_restore` поле `custom_archive_listing_ok` остаётся `null`; повреждённая сигнатура даёт `false`. Архивы `.sql` и `.gz` этим способом не проверяются.

Анализатор `marina_runtime_inventory_review.py` требует хотя бы один архив с `custom_archive_listing_ok=true`, иначе статус `INCOMPLETE`. Успешный `pg_restore --list` означает **только читаемость каталога архива**, но не полноценность данных, не валидность каждого блока и не успешное восстановление. Поле `backup_restored` остаётся `false` даже при успехе этой проверки. Для закрытия ENV-03 обязательны восстановление в новую disposable БД, сравнение существенных данных и документированный откат без вмешательства в рабочую БД.

Папка резервных копий в существующей диагностике по умолчанию `/home/agent/marina-backups`, тогда как скрипт fleet backup пишет также в `.marina-backups/<slug>`. Эти каталоги следует инвентаризировать раздельно, указывая `--backup-dir`; не объединять разные гостиницы в один логический backup set.

**На текущую дату реальный архив Ubuntu не проверялся из этой сессии.**
