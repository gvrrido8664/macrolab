import test from 'node:test';
import assert from 'node:assert/strict';
import { sessionIdentity } from '../src/lib/identity.ts';
test('production rejects previously issued mock sessions as well as unknown providers', () => {
  assert.equal(sessionIdentity('riot-mock:local',true),null);
  assert.equal(sessionIdentity('riot-mock:local',false),'riot-mock:local');
  assert.equal(sessionIdentity('github:123',true),'github:123');
  assert.equal(sessionIdentity('unknown:123',false),null);
  assert.equal(sessionIdentity(undefined,true),null);
});
