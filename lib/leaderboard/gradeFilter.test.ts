import { describe, expect, it } from "vitest";
import {
  buildGradePredicateEnabled,
  normalizeGradeFilter,
  shouldApplyGradeFilter,
} from "./gradeFilter";

describe("grade filter normalization", () => {
  it("treats missing grades as no filter", () => {
    expect(normalizeGradeFilter(null)).toEqual(null);
    expect(shouldApplyGradeFilter(null)).toBe(false);
  });

  it("normalizes all-grades selection to a concrete filter array", () => {
    const all = normalizeGradeFilter("7,8,9,10,11,12");
    expect(all).toEqual([7, 8, 9, 10, 11, 12]);
    expect(shouldApplyGradeFilter(all)).toBe(true);
  });

  it("drops invalid grade values", () => {
    expect(normalizeGradeFilter("6,7,12,13,abc")).toEqual([7, 12]);
  });

  it("uses one predicate path for filtered and unfiltered requests", () => {
    expect(buildGradePredicateEnabled(null)).toBe(false);
    expect(buildGradePredicateEnabled([11])).toBe(true);
    expect(buildGradePredicateEnabled([7, 8, 9, 10, 11, 12])).toBe(true);
  });

  it("treats omitted grades and explicit all-grades as equivalent intent", () => {
    const omitted = normalizeGradeFilter(null);
    const explicitAll = normalizeGradeFilter("7,8,9,10,11,12");
    expect(omitted).toBeNull();
    expect(explicitAll).toEqual([7, 8, 9, 10, 11, 12]);
  });
});
