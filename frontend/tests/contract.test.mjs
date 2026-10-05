import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { isPlaybook, isHistory } from '../src/types/playbook.ts';
const demo = JSON.parse(readFileSync(new URL('../src/data/demo.json',import.meta.url),'utf8'));
test('contract accepts demo and rejects malformed nested data without throwing', () => {
  assert.equal(isPlaybook(demo),true);
  assert.equal(isPlaybook(null),false);
  assert.equal(isPlaybook({...demo,events:[{timestamp:0}]}),false);
  assert.equal(isPlaybook({...demo,match_stats:{...demo.match_stats,duration_seconds:-1}}),false);
  assert.equal(isPlaybook({...demo,decisions:[{...demo.decisions[0],alternatives:null}]}),false);
  assert.equal(isHistory({analyses:[demo],habit:null,shares:[],feedback:[]}),true);
  assert.equal(isHistory({analyses:[demo],habit:{completed:99},shares:[],feedback:[]}),false);
});
