import fs from "node:fs";
import { pmsOwnerRoomDisplayLabel } from "../apps/admin/components/PMSRoomDisplayLabel.ts";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const cases = [
  [{ code: "301", room_type_name: "Одноместный, цоколь", beds_raw: null }, "301"],
  [{ code: "101", room_type_name: "Двухместный стандарт, цоколь", beds_raw: "1сп+1сп+д" }, "101-цоколь (1сп+1сп+д)"],
  [{ code: "102", room_type_name: "Двухместный стандарт, цоколь", beds_raw: null }, "102-цоколь"],
  [{ code: "103", room_type_name: "Двухместный стандарт, цоколь", beds_raw: "1сп+1сп+кр" }, "103-цоколь (1сп+1сп+кр)"],
  [{ code: "104", room_type_name: "Двухместный стандарт, цоколь", beds_raw: "1сп+1сп" }, "104-цоколь (1сп+1сп)"],
  [{ code: "201", room_type_name: "Двухместный стандарт, цоколь", beds_raw: "2сп+кр" }, "201-цоколь (2сп+кр)"],
  [{ code: "202", room_type_name: "Двухместный стандарт, цоколь", beds_raw: "2сп+д+к; доп. кровать" }, "202-цоколь (2сп+д+к) — доп. кровать"],
  [{ code: "501", room_type_name: "Одноместный, улучшенный", beds_raw: "1сп+1сп+крк" }, "501-(1сп+1сп+крк) прачка мансарда"],
  [{ code: "502", room_type_name: "Одноместный, улучшенный", beds_raw: "1сп+1сп+крк" }, "502-(1сп+1сп+крк) прачка мансарда"],
  [{ code: "1А", room_type_name: "Двухместный стандарт в коттеджном доме", beds_raw: null }, "1А"],
  [{ code: "112", room_type_name: "Двухместный улучшенный", beds_raw: "1сп+1сп" }, "112 (1сп+1сп)"],
  [{ code: "312", room_type_name: "Люкс двухместный", beds_raw: "1сп+1сп+д" }, "312 (1сп+1сп+д)"],
  [{ code: "311", room_type_name: "Люкс трехместный", beds_raw: "2сп+1сп; кухня" }, "311 (2сп+1сп) + кухня"],
  [{ code: "314", room_type_name: "Люкс трехместный", beds_raw: "2сп+1сп+д; кухня" }, "314 (2сп+1сп+д) + кухня"],
  [{ code: "421", room_type_name: "Апартаменты", beds_raw: "2сп+1сп+1сп+д+кр+кр+кр" }, "421 sea view (2сп+1сп+1сп+д+кр+кр+кр)"],
  [{ code: "1", room_type_name: "Квартиры / апартаменты с кухней", beds_raw: "2сп+1сп+1сп+д+кр" }, "1 (2сп+1сп+1сп+д+кр)"],
];

for (const [room, expected] of cases) {
  const actual = pmsOwnerRoomDisplayLabel(room);
  assert(actual === expected, `${room.code}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

const css = fs.readFileSync(new URL("../apps/admin/app/pms-owner-workflow-corrections.css", import.meta.url), "utf8");
assert(!css.includes("owner-room-row:has"), "room names must not be faked with CSS :has()/::after substitutions");
assert(css.includes('repeat(31,26px)!important'), "31-day cells must remain 26px wide");
assert(css.includes('repeat(14,34px)!important'), "14-day cells must remain 34px wide");
assert(css.includes('height:32px'), "owner room/night rows must remain compact at 32px");

console.log(`PASS: ${cases.length} owner room-label cases + compact grid contract`);
