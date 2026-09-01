export type PmsRoomDisplayInput = {
  code: string;
  room_type_name: string;
  beds_raw?: string | null;
};

function beds(room: PmsRoomDisplayInput) {
  return room.beds_raw?.trim() || "";
}

export function pmsOwnerRoomDisplayLabel(room: PmsRoomDisplayInput) {
  const raw = beds(room);

  if (room.room_type_name === "Одноместный, цоколь") {
    return room.code;
  }

  if (room.room_type_name === "Двухместный стандарт, цоколь") {
    return `${room.code}-цоколь${raw ? ` (${raw.replace("; доп. кровать", "")})` : ""}${raw.includes("доп. кровать") ? " — доп. кровать" : ""}`;
  }

  if (room.code === "501" || room.code === "502") {
    return `${room.code}${raw ? `-(${raw})` : ""} прачка мансарда`;
  }

  if (room.room_type_name === "Двухместный стандарт в коттеджном доме") {
    return room.code;
  }

  if (room.code === "311" || room.code === "314") {
    const [sleeping] = raw.split(";");
    return `${room.code}${sleeping ? ` (${sleeping.trim()})` : ""} + кухня`;
  }

  if (room.code === "421") {
    return `421 sea view${raw ? ` (${raw})` : ""}`;
  }

  if (raw.includes(";")) {
    const [sleeping, note] = raw.split(";", 2);
    return `${room.code}${sleeping.trim() ? ` (${sleeping.trim()})` : ""}${note?.trim() ? ` ${note.trim()}` : ""}`;
  }

  return `${room.code}${raw ? ` (${raw})` : ""}`;
}
