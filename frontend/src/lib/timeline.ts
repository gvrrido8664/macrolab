export function visibleEvents<T extends { timestamp: number; type: string }>(events: T[], time: number, windowMs: number, filter: string): T[] {
  return events.filter(event => event.timestamp <= time && (windowMs === 0 || event.timestamp >= time - windowMs) && (filter === 'all' || event.type === filter));
}
