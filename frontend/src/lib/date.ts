/** Local-date helpers. The API speaks YYYY-MM-DD in the user's own timezone. */

export function toISODate(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function today(): string {
  return toISODate(new Date());
}

export function shiftDays(iso: string, days: number): string {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(year, month - 1, day + days);
  return toISODate(date);
}

export function friendlyDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  if (iso === today()) return "Today";
  if (iso === shiftDays(today(), -1)) return "Yesterday";
  if (iso === shiftDays(today(), 1)) return "Tomorrow";
  return date.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}
