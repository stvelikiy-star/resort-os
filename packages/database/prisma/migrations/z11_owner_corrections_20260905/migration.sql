-- Owner-approved corrections received 2026-09-05.
-- This migration is intentionally data-preserving: it corrects canonical room facts
-- and enriches existing public CMS documents without recreating reservations/stays.

-- 501 / 502 are active two-person basement rooms located above the laundry area.
-- Keep existing bed/area raw facts unless explicitly superseded; only canonicalize
-- category/capacity source via the existing DOUBLE_STANDARD_BASEMENT room type.
WITH property_row AS (
    SELECT id FROM properties WHERE code = 'THREE_CROWNS'
), target_type AS (
    SELECT rt.id
    FROM room_types rt
    JOIN property_row p ON p.id = rt."propertyId"
    WHERE rt.code = 'DOUBLE_STANDARD_BASEMENT'
    LIMIT 1
)
UPDATE rooms r
SET "roomTypeId" = tt.id,
    "floorLabel" = 'BASEMENT',
    notes = concat_ws('; ', NULLIF(r.notes, ''), 'OWNER_APPROVED_2026-09-05: basement above laundry; operational; two-person room'),
    "updatedAt" = now()
FROM property_row p, target_type tt
WHERE r."propertyId" = p.id
  AND r.code IN ('501', '502');

-- The owner confirmed the public conference/banquet offer and corrected the manager
-- contact to +996 558 08 50 02. Update already-stored CMS documents as well as code
-- defaults so local/production data cannot keep the stale ...08 WhatsApp number.
UPDATE site_content_documents
SET "draftJson" =
      jsonb_set(
        jsonb_set(COALESCE("draftJson", '{}'::jsonb), '{contacts,whatsapp}', to_jsonb('+996 558 08 50 02'::text), true),
        '{conference}',
        CASE locale
          WHEN 'kg' THEN jsonb_build_object(
            'eyebrow','Конференциялар жана банкеттер',
            'title','20дан 120га чейин конок үчүн конференц-зал',
            'copy','Конференциялар, иш жолугушуулар, презентациялар жана топтук иш-чаралар үчүн өзүнчө мейкиндик. Конференц-зал банкет өткөрүүгө да даярдалат.',
            'capacity','20–120 конок',
            'banquet','Конференц-залда банкеттик отургузуу мүмкүн',
            'menu','Банкеттик меню жана тейлөө форматы өзүнчө макулдашылат',
            'cta','Иш-чараны талкуулоо'
          )
          WHEN 'en' THEN jsonb_build_object(
            'eyebrow','Conferences & banquets',
            'title','Conference hall for events from 20 to 120 guests',
            'copy','A dedicated venue for conferences, business meetings, presentations and group events. The conference hall can also be arranged for a banquet.',
            'capacity','20–120 guests',
            'banquet','Banquet seating is available in the conference hall',
            'menu','Banquet menu and service format are agreed individually',
            'cta','Discuss your event'
          )
          ELSE jsonb_build_object(
            'eyebrow','Конференции и банкеты',
            'title','Конференц-зал для мероприятий от 20 до 120 гостей',
            'copy','Отдельное пространство для конференций, деловых встреч, презентаций и групповых мероприятий. Конференц-зал также может быть подготовлен под банкет.',
            'capacity','20–120 гостей',
            'banquet','Банкетная рассадка доступна в конференц-зале',
            'menu','Банкетное меню и формат обслуживания согласовываются индивидуально',
            'cta','Обсудить мероприятие'
          )
        END,
        true
      ),
    "publishedJson" =
      jsonb_set(
        jsonb_set(COALESCE("publishedJson", '{}'::jsonb), '{contacts,whatsapp}', to_jsonb('+996 558 08 50 02'::text), true),
        '{conference}',
        CASE locale
          WHEN 'kg' THEN jsonb_build_object(
            'eyebrow','Конференциялар жана банкеттер',
            'title','20дан 120га чейин конок үчүн конференц-зал',
            'copy','Конференциялар, иш жолугушуулар, презентациялар жана топтук иш-чаралар үчүн өзүнчө мейкиндик. Конференц-зал банкет өткөрүүгө да даярдалат.',
            'capacity','20–120 конок',
            'banquet','Конференц-залда банкеттик отургузуу мүмкүн',
            'menu','Банкеттик меню жана тейлөө форматы өзүнчө макулдашылат',
            'cta','Иш-чараны талкуулоо'
          )
          WHEN 'en' THEN jsonb_build_object(
            'eyebrow','Conferences & banquets',
            'title','Conference hall for events from 20 to 120 guests',
            'copy','A dedicated venue for conferences, business meetings, presentations and group events. The conference hall can also be arranged for a banquet.',
            'capacity','20–120 guests',
            'banquet','Banquet seating is available in the conference hall',
            'menu','Banquet menu and service format are agreed individually',
            'cta','Discuss your event'
          )
          ELSE jsonb_build_object(
            'eyebrow','Конференции и банкеты',
            'title','Конференц-зал для мероприятий от 20 до 120 гостей',
            'copy','Отдельное пространство для конференций, деловых встреч, презентаций и групповых мероприятий. Конференц-зал также может быть подготовлен под банкет.',
            'capacity','20–120 гостей',
            'banquet','Банкетная рассадка доступна в конференц-зале',
            'menu','Банкетное меню и формат обслуживания согласовываются индивидуально',
            'cta','Обсудить мероприятие'
          )
        END,
        true
      ),
    version = version + 1,
    "publishedVersion" = GREATEST("publishedVersion" + 1, version + 1),
    "publishedAt" = now(),
    "updatedAt" = now()
WHERE scope = 'PUBLIC_SITE'
  AND locale IN ('ru','kg','en');
