-- Internal manager-controlled guest engagement queue.
-- This table records follow-up work and factual feedback only; it grants no automatic outbound authority.

CREATE TABLE IF NOT EXISTS guest_engagements (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "guestId" uuid NOT NULL,
    "reservationId" uuid,
    kind text NOT NULL,
    status text NOT NULL DEFAULT 'OPEN',
    "dueDate" date,
    "channelHint" text,
    title text NOT NULL,
    notes text,
    score integer,
    "feedbackText" text,
    "completedAt" timestamptz,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT guest_engagements_property_fkey
        FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT guest_engagements_guest_fkey
        FOREIGN KEY ("guestId") REFERENCES guests(id) ON DELETE CASCADE,
    CONSTRAINT guest_engagements_reservation_fkey
        FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT guest_engagements_kind_check
        CHECK (kind IN ('POST_STAY_FEEDBACK','RETURN_GUEST','MANAGER_FOLLOWUP')),
    CONSTRAINT guest_engagements_status_check
        CHECK (status IN ('OPEN','IN_PROGRESS','DONE','CANCELLED')),
    CONSTRAINT guest_engagements_score_check
        CHECK (score IS NULL OR score BETWEEN 0 AND 10),
    CONSTRAINT guest_engagements_score_kind_check
        CHECK (score IS NULL OR kind = 'POST_STAY_FEEDBACK'),
    CONSTRAINT guest_engagements_feedback_reservation_check
        CHECK (kind <> 'POST_STAY_FEEDBACK' OR "reservationId" IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS guest_engagements_feedback_reservation_key
    ON guest_engagements ("reservationId")
    WHERE kind = 'POST_STAY_FEEDBACK';

CREATE INDEX IF NOT EXISTS guest_engagements_property_status_due_idx
    ON guest_engagements ("propertyId", status, "dueDate");

CREATE INDEX IF NOT EXISTS guest_engagements_guest_idx
    ON guest_engagements ("guestId", "createdAt" DESC);

CREATE INDEX IF NOT EXISTS guest_engagements_reservation_idx
    ON guest_engagements ("reservationId");

COMMENT ON TABLE guest_engagements IS
    'Internal manager follow-up and factual feedback queue; no automatic outbound messaging authority.';
