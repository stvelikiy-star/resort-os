-- Optional wayfinding attached to existing physical room; no new room catalog.
CREATE TABLE IF NOT EXISTS room_wayfinding (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  "roomId" uuid NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  latitude double precision,
  longitude double precision,
  "parkingLabel" varchar(100),
  directions varchar(1200),
  "walkthroughVideoUrl" varchar(500),
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  "updatedAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT room_wayfinding_room_unique UNIQUE("roomId"),
  CONSTRAINT room_wayfinding_coordinates_pair_check CHECK (
    (latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)
  ),
  CONSTRAINT room_wayfinding_latitude_range_check CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CONSTRAINT room_wayfinding_longitude_range_check CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);
CREATE INDEX IF NOT EXISTS room_wayfinding_hotel_room_idx ON room_wayfinding ("propertyId","roomId");
COMMENT ON TABLE room_wayfinding IS 'Guest-safe room route; no lock PINs, Wi-Fi secrets or personal data.';
