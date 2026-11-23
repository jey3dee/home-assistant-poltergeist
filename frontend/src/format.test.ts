import { describe, expect, it } from "vitest";
import { formatCount, formatPercent } from "./format";

describe("format", () => {
  it("rounds a probability to whole percent", () => {
    expect(formatPercent(22.14)).toBe("22 %");
    expect(formatPercent(99.96)).toBe("100 %");
  });

  it("shows tiny probabilities as below one percent instead of zero", () => {
    expect(formatPercent(0.2)).toBe("< 1 %");
    expect(formatPercent(0)).toBe("0 %");
  });

  it("shows the expected head count with two decimals", () => {
    expect(formatCount(0.284)).toBe("0.28");
    expect(formatCount(2)).toBe("2.00");
  });
});
