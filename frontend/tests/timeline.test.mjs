import test from 'node:test';
import assert from 'node:assert/strict';
import { visibleEvents } from '../src/lib/timeline.ts';
test('timeline excludes the future and respects time window and event filters', () => {
  const events = [{ timestamp: 599000, type: 'WARD_PLACED' }, { timestamp: 600000, type: 'CHAMPION_KILL' }, { timestamp: 659000, type: 'CHAMPION_KILL' }];
  assert.deepEqual(visibleEvents(events, 600000, 180000, 'all'), events.slice(0, 2));
  assert.deepEqual(visibleEvents(events, 660000, 60000, 'CHAMPION_KILL'), events.slice(1));
  assert.deepEqual(visibleEvents(events, 660000, 0, 'WARD_PLACED'), events.slice(0, 1));
});
