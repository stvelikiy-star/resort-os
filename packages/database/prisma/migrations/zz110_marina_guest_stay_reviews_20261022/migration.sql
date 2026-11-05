-- Authenticated in-stay guest feedback. Separate from 0-10 NPS, review links and provider outreach.
CREATE TABLE IF NOT EXISTS guest_stay_reviews (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  "stayId" uuid NOT NULL REFERENCES stays(id) ON DELETE CASCADE,
  "guestId" uuid NOT NULL REFERENCES guests(id) ON DELETE CASCADE,
  rating integer NOT NULL CONSTRAINT guest_stay_reviews_rating_check CHECK (rating BETWEEN 1 AND 5),
  comment text NOT NULL DEFAULT '' CONSTRAINT guest_stay_reviews_comment_length_check CHECK (char_length(comment) <= 2000),
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  "updatedAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT guest_stay_reviews_stay_unique UNIQUE ("stayId")
);
CREATE INDEX IF NOT EXISTS guest_stay_reviews_guest_history_idx
 ON guest_stay_reviews ("propertyId","guestId","createdAt" DESC);
COMMENT ON TABLE guest_stay_reviews IS
 'Guest-submitted private stay experience via active verified QR/PIN session; never authorizes public review gating or outbound messages.';
