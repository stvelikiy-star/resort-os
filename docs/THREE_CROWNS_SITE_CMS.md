# Three Crowns Site CMS — implementation contract

Status: active implementation branch (2026-09-30)

## Goal
Give OWNER/MANAGER a safe visual CMS for the public Three Crowns site without exposing layout/code editing.

## V1 surfaces
- Rooms: all 12 room categories; title, short/long description, area, capacity, amenities, rates, visibility.
- Room media: upload approved photos, preview, choose hero, reorder gallery, remove/replace, alt text.
- Site sections: hero, territory, SPA, beach, restaurant, transfer, tours, contacts, rules and SEO copy/media.
- Media library: previews, usage references, room/section filters, prevent deletion while in use.
- Publishing: DRAFT -> PREVIEW -> PUBLISHED with explicit confirmation.
- Revision history: actor, timestamp, changed fields, restore prior revision.

## Safety / authority
- OWNER: full CMS and publish/rollback.
- MANAGER: edit/upload/preview/publish.
- Other roles: no CMS access.
- CMS edits content only. Layout/components/code are not editable.
- Media upload never generates or stylistically changes hotel photography.
- Reject unsupported file types and enforce upload size/dimension limits.
- Every mutation is auditable.

## Data model
- site_content(id, property_id, key, locale, draft_json, published_json, published_at, updated_at, updated_by)
- site_media(id, property_id, storage_key, original_name, mime_type, width, height, bytes, sha256, created_at, created_by)
- site_media_usage(id, media_id, content_key, slot, sort_order)
- site_content_revision(id, content_id, revision_no, snapshot_json, created_at, created_by, action)

## API
- GET /api/v1/admin/site-cms/content
- GET/PATCH /api/v1/admin/site-cms/content/{key}
- POST /api/v1/admin/site-cms/media
- GET /api/v1/admin/site-cms/media
- DELETE /api/v1/admin/site-cms/media/{id} (fails if referenced)
- PUT /api/v1/admin/site-cms/content/{key}/media
- POST /api/v1/admin/site-cms/preview
- POST /api/v1/admin/site-cms/publish
- GET /api/v1/admin/site-cms/revisions
- POST /api/v1/admin/site-cms/revisions/{id}/restore
- GET /api/v1/public/site-content

## Admin UX
Primary navigation entry: "Сайт".
Tabs: "Номера", "Разделы", "Медиа", "Публикация".
Room editor uses large photo previews and drag/drop gallery ordering. Destructive actions require confirmation.
Show persistent state badge: "Черновик", "Есть изменения", "Опубликовано".
Preview opens the public site with draft content without making it public.

## Integration rule
Public site consumes only published CMS content. PMS/Core remains authority for live availability and booking data; CMS must not duplicate room availability state.

## Acceptance
1. OWNER can replace a room hero/gallery without touching code.
2. Text edits are previewable before publish.
3. Publish is atomic and leaves a restorable revision.
4. Deleting an in-use image is blocked.
5. Unauthorized roles receive 403.
6. Public endpoint never returns draft content.
7. Existing Three Crowns design remains unchanged when content values are unchanged.
