-- Distinct 1–5 post-stay guest experience score. Do not conflate with NPS (0–10).
-- Existing feedback rows remain valid and continue to use score.
ALTER TABLE guest_engagements
  ADD COLUMN IF NOT EXISTS "starRating" integer;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'guest_engagements_star_rating_range') THEN
    ALTER TABLE guest_engagements
      ADD CONSTRAINT guest_engagements_star_rating_range
      CHECK ("starRating" IS NULL OR ("starRating" BETWEEN 1 AND 5 AND kind = 'POST_STAY_FEEDBACK'));
  END IF;
END $$;
