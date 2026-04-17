export function normalizeGradeFilter(raw: string | null): number[] | null {
  if (!raw) return null;

  const parsed = raw
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((grade) => Number.isInteger(grade) && grade >= 7 && grade <= 12);

  return parsed.length > 0 ? parsed : null;
}

export function shouldApplyGradeFilter(
  grades: number[] | null
): grades is number[] {
  return Array.isArray(grades) && grades.length > 0;
}

export function buildGradePredicateEnabled(grades: number[] | null): boolean {
  return shouldApplyGradeFilter(grades);
}
