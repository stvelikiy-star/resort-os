# MARINA SMART · единая семантическая основа v0.1

Первый этап — **справочный, без миграции UI**. Источник машиночитаемых значений —
[`marina-smart.tokens.json`](./marina-smart.tokens.json), а не новый runtime-пакет. Он
фиксирует уже используемые значения и не меняет экраны, права или server-authoritative
grants. Mobile `tokens.ts`, admin/staff `globals.css` остаются runtime-источниками до
отдельно согласованной миграции.

## Семантика

- `background / surface / surfaceAlt / border` — холст, карточка, вторичная карточка и разделитель.
- `text / textMuted / primary / onPrimary / primarySoft / accent` — основной текст,
  вторичный текст, главное действие, текст на нём, мягкий акцент и декоративный акцент.
- `success / warning / danger / info` и парные `*Soft` — смысловые foreground/background.
  Цвет не должен быть единственным носителем статуса: обязателен текст, при необходимости иконка.
- `hero*`, `glass*`, `gold`, `cyan`, `iris`, `glow` — брендовые/композиционные значения,
  не замена текстовым или статусным токенам. Champagne/gold не используется как мелкий body text.

## Темы и точные расхождения

Mobile поддерживает утверждённые `light` и `dark` из `apps/mobile/src/theme/tokens.ts`.
Admin и Staff сейчас являются отдельными **light-only legacy темами**; тёмные значения для
них не утверждены. Поэтому mobile navy/cyan не подменяет web green, а web green не
подменяет mobile palette.

| Семантика | Mobile light | Mobile dark | Admin light | Staff light |
|---|---:|---:|---:|---:|
| background | `#F5FAFF` | `#061225` | `#f4f6f3` | `#f3f5f2` |
| surface | `#FFFFFF` | `#10213D` | `#ffffff` | `#fff` |
| text | `#10243D` | `#F4F8FF` | `#16231d` | `#15231d` |
| muted | `#586D80` | `#B3C6DC` | `#6f7c75` | `#6e7a74` |
| primary/brand | `#073B70` | `#00D8FF` | `#173f31` | `#173f31` |
| border | `#DCE8F3` | `#2C4260` | `#dfe5e1` | `#dfe5e1` |

Admin отдельно кодирует состояния номера/блока (`clean`, `dirty`, `inspection`, `tech`,
`unknown`, `reservation`, `maintenance`, `manual`). Staff отдельно кодирует приоритеты
`urgent/high` и gold. Это доменные значения, а не взаимозаменяемые aliases mobile
`success/warning/danger/info`. Hex-регистр и краткая запись сохранены точно как в CSS.

## Типографика и размеры

Mobile scale: display `34/800`, title `27/800`, h2 `19/700`, body `16/500/24`,
small `13/500/19`, label `12/700`, metric `30/800`; единицы React Native — density-independent.
Touch target — `56`. Space — `4, 8, 12, 16, 24, 32, 40`; radii — `12, 18, 24, 30, 999`.

Web использует стек Inter/system, но не имеет общей шкалы: например admin `h1` —
`clamp(25px, 3vw, 38px)`, а staff содержит локальные размеры компонентов. Их нельзя
механически заменить mobile scale без визуальной приёмки всех desktop/mobile breakpoints.

## Motion и reduced motion

Mobile: press `125ms`, tab `220ms`, card `320ms`, modal `340ms`, chart `700ms`, stagger
`55ms` максимум для шести позиций. `useMotionPreference` запрещает motion до чтения
настройки ОС, при `reduceMotion`, при background state и при ошибке чтения. Новые mobile
компоненты должны использовать этот gate.

В admin/staff нет централизованного motion API и нет общего `prefers-reduced-motion`
контракта. Это зафиксированный пробел, а не разрешение добавлять анимацию. До следующего
этапа новые web-анимации не вводятся; будущая реализация должна отключать non-essential
animation/transition через `@media (prefers-reduced-motion: reduce)` без изменения layout.

## Границы первого этапа

Спецификация не обещает идентичный внешний вид платформ, не выдаёт UI visibility за
авторизацию и не утверждает новую палитру. Текущие mobile роли перечислены в JSON только
как vocabulary; реальные доступы по-прежнему определяют сервер, property/module grants и
`workspaceForSession`. Проверка: `npm run design:validate`.

Справочник иконок и ролевые рекомендации: [`ICONS.md`](./ICONS.md).
