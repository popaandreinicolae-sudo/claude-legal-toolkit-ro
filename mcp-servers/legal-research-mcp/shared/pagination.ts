export interface PaginatedResult<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
}

export function paginate<T>(items: T[], total: number, offset: number, limit: number): PaginatedResult<T> {
  return { items, total, offset, limit, hasMore: offset + items.length < total };
}
