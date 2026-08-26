import { describe, expect, it } from "vitest";
import { friendlyDate, shiftDays, toISODate, today } from "./date";

describe("date helpers", () => {
  it("formats a local date without drifting across timezones", () => {
    // Late-evening local time is the case a naive toISOString() gets wrong.
    expect(toISODate(new Date(2026, 7, 23, 23, 30))).toBe("2026-08-23");
    expect(toISODate(new Date(2026, 0, 1, 0, 5))).toBe("2026-01-01");
  });

  it("shifts days across month and year boundaries", () => {
    expect(shiftDays("2026-08-31", 1)).toBe("2026-09-01");
    expect(shiftDays("2026-01-01", -1)).toBe("2025-12-31");
    expect(shiftDays("2024-02-28", 1)).toBe("2024-02-29");
  });

  it("names the days around today", () => {
    expect(friendlyDate(today())).toBe("Today");
    expect(friendlyDate(shiftDays(today(), -1))).toBe("Yesterday");
    expect(friendlyDate(shiftDays(today(), 1))).toBe("Tomorrow");
    expect(friendlyDate("2026-03-14")).not.toBe("Today");
  });
});
