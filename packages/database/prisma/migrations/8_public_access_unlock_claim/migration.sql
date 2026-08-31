-- Serialize paid public-access unlock attempts before contacting the physical controller.
--
-- Without an intermediate state, two concurrent requests can both observe PAID,
-- create separate grants and send duplicate UNLOCK commands before either request
-- records USED. UNLOCKING is a short-lived claim state; controller failure returns
-- the intent to PAID, while controller success advances it to USED.

ALTER TABLE public_access_payment_intents
    DROP CONSTRAINT IF EXISTS public_access_payment_intents_status_check;

ALTER TABLE public_access_payment_intents
    ADD CONSTRAINT public_access_payment_intents_status_check
    CHECK (status IN ('PENDING','PAID','UNLOCKING','USED','EXPIRED','CANCELLED'));

COMMENT ON CONSTRAINT public_access_payment_intents_status_check ON public_access_payment_intents IS
    'UNLOCKING serializes one physical unlock attempt; failure returns to PAID and success advances to USED.';
