-- MARINA SMART public CMS: add Kazakh locale without mutating existing content.
ALTER TABLE "site_content_documents"
  DROP CONSTRAINT IF EXISTS "site_content_documents_locale_check";

ALTER TABLE "site_content_documents"
  ADD CONSTRAINT "site_content_documents_locale_check"
  CHECK (locale IN ('ru', 'kg', 'kz', 'en'));
