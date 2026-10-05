import test from 'node:test';
import assert from 'node:assert/strict';
import { reportText, eventTitle, locationNote } from '../src/lib/report-copy.ts';

test('saved reports show Spanish events and explain missing map locations', () => {
  assert.equal(reportText('Tu equipo obtuvo INHIBITOR_BUILDING tras DRAGON.'), 'Tu equipo destruyó un inhibidor tras dragón.');
  assert.equal(reportText('Compraste el objeto 2055.'), 'Compraste un objeto.');
  assert.equal(eventTitle({ type: 'BUILDING_KILL', detail: 'TOWER_BUILDING' }), 'Se destruyó una torre');
  assert.equal(eventTitle({ type: 'BUILDING_KILL', detail: 'FUTURE_BUILDING' }), 'Se destruyó una estructura');
  assert.equal(eventTitle({ type: 'ITEM_PURCHASED', detail: '2055' }), 'Compraste un objeto');
  assert.equal(locationNote({ type: 'ITEM_PURCHASED' }), null);
  assert.match(locationNote({ type: 'WARD_PLACED' }), /Riot no indica dónde/);
  assert.equal(locationNote({ type: 'WARD_PLACED', position_pct: { x: 1, y: 2 } }), null);
});
