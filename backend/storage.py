"""SQLite pilot store: one host with a persistent disk; use Postgres for replicas."""
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')

# ponytail: SQLite on one host; migrate to Postgres before adding replicas.


@contextmanager
def database():
    path = ROOT / os.getenv('MACROLAB_DB_PATH', 'data/macrolab.sqlite3')
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version > 2:
            raise sqlite3.DatabaseError('This database requires a newer application version')
        db.executescript('''
          CREATE TABLE IF NOT EXISTS tracked_players (
            owner TEXT NOT NULL, puuid TEXT NOT NULL, name TEXT NOT NULL,
            PRIMARY KEY(owner,puuid));
          CREATE TABLE IF NOT EXISTS analyses (
            owner TEXT NOT NULL, puuid TEXT NOT NULL, match_id TEXT NOT NULL,
            version TEXT NOT NULL, created INTEGER NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(owner, puuid, match_id, version));
          CREATE TABLE IF NOT EXISTS habits (
            owner TEXT NOT NULL, puuid TEXT NOT NULL, started INTEGER NOT NULL,
            version TEXT NOT NULL, PRIMARY KEY(owner, puuid));
          CREATE TABLE IF NOT EXISTS shares (
            token TEXT PRIMARY KEY, owner TEXT NOT NULL, puuid TEXT NOT NULL,
            match_id TEXT NOT NULL, version TEXT NOT NULL, expires INTEGER NOT NULL,
            FOREIGN KEY(owner, puuid, match_id, version)
              REFERENCES analyses(owner, puuid, match_id, version) ON DELETE CASCADE);
          CREATE TABLE IF NOT EXISTS feedback (
            token TEXT NOT NULL REFERENCES shares(token) ON DELETE CASCADE,
            reviewer TEXT NOT NULL, decision TEXT NOT NULL, verdict TEXT NOT NULL,
            comment TEXT NOT NULL, created INTEGER NOT NULL,
            PRIMARY KEY(token, reviewer, decision));
          CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, expires INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS telemetry (owner TEXT NOT NULL, event TEXT NOT NULL, created INTEGER NOT NULL);
        ''')
        if version < 2:
            # Transactional, idempotent migration from the original pilot database.
            with db:
                db.execute('BEGIN IMMEDIATE')
                columns={r['name'] for r in db.execute('PRAGMA table_info(telemetry)')}
                if 'resource' not in columns:
                    db.execute("ALTER TABLE telemetry ADD COLUMN resource TEXT NOT NULL DEFAULT ''")
                    db.execute("ALTER TABLE telemetry ADD COLUMN decision TEXT NOT NULL DEFAULT ''")
                db.execute('PRAGMA user_version=2')
        with db:
            yield db
    finally:
        db.close()


def cache_get(key):
    with database() as db:
        db.execute('DELETE FROM cache WHERE expires <= ?', (int(time.time()),))
        row = db.execute('SELECT payload FROM cache WHERE key=?', (key,)).fetchone()
        return json.loads(row['payload']) if row else None


def cache_set(key, payload, ttl):
    with database() as db:
        db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)', (key, json.dumps(payload), int(time.time()) + ttl))


def admit(key, limit=20, window=60):
    now = int(time.time())
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM limits WHERE expires<=?', (now,))
        row = db.execute('SELECT count,expires FROM limits WHERE key=?', (key,)).fetchone()
        if row and row['count'] >= limit:
            return max(1, row['expires'] - now)
        db.execute('INSERT INTO limits VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, now + window))
    return 0


def save_analysis(owner, puuid, report):
    with database() as db:
        db.execute('INSERT INTO analyses VALUES(?,?,?,?,?,?) ON CONFLICT(owner,puuid,match_id,version) DO NOTHING',
                   (owner, puuid, report['match_id'], report['analysis_version'], int(time.time()*1000), json.dumps(report | {'saved':True})))


def history(owner, puuid):
    with database() as db:
        rows = db.execute('SELECT payload FROM analyses WHERE owner=? AND puuid=? ORDER BY created DESC', (owner, puuid)).fetchall()
        habit = db.execute('SELECT started,version FROM habits WHERE owner=? AND puuid=?', (owner, puuid)).fetchone()
        shares = db.execute('SELECT token,match_id,expires FROM shares WHERE owner=? AND puuid=? AND expires>?', (owner, puuid, int(time.time()))).fetchall()
        feedback = db.execute('SELECT f.decision,f.verdict,f.comment,f.created,s.match_id FROM feedback f JOIN shares s ON s.token=f.token WHERE s.owner=? AND s.puuid=? ORDER BY f.created DESC LIMIT 100', (owner, puuid)).fetchall()
    reports = [json.loads(row['payload']) for row in rows]
    # One entry per match in the UI; versions remain available for exact shared reports.
    unique = {}
    for report in reports:
        unique.setdefault(report['match_id'], report)
    progress = None
    if habit:
        eligible = [r for r in reports if r['analysis_version'] == habit['version'] and r['habit_metric']['eligible'] and r['match_stats']['game_created_at'] > habit['started']]
        eligible.sort(key=lambda r: r['match_stats']['game_created_at'])
        eligible = eligible[:5]
        progress = dict(habit) | {'completed': len(eligible), 'target': 5,
            'numerator': sum(r['habit_metric']['numerator'] for r in eligible),
            'denominator': sum(r['habit_metric']['denominator'] for r in eligible)}
    return {'analyses': list(unique.values())[:30], 'habit': progress, 'shares': [dict(r) for r in shares], 'feedback': [dict(r) for r in feedback]}


def start_habit(owner, puuid, version):
    with database() as db:
        db.execute('INSERT INTO habits VALUES(?,?,?,?) ON CONFLICT(owner,puuid) DO NOTHING', (owner, puuid, int(time.time()*1000), version))


def create_share(owner, puuid, match_id, version):
    token = secrets.token_urlsafe(32)
    with database() as db:
        exists = db.execute('SELECT 1 FROM analyses WHERE owner=? AND puuid=? AND match_id=? AND version=?', (owner, puuid, match_id, version)).fetchone()
        if not exists:
            return None
        db.execute('INSERT INTO shares VALUES(?,?,?,?,?,?)', (token, owner, puuid, match_id, version, int(time.time()) + 7*86400))
    return token


def read_share(token):
    with database() as db:
        row = db.execute('SELECT a.payload FROM shares s JOIN analyses a ON a.owner=s.owner AND a.puuid=s.puuid AND a.match_id=s.match_id AND a.version=s.version WHERE s.token=? AND s.expires>?', (token, int(time.time()))).fetchone()
    return json.loads(row['payload']) if row else None


def revoke_share(owner, token):
    with database() as db:
        db.execute('UPDATE shares SET expires=0 WHERE owner=? AND token=?', (owner, token))


def delete_user(owner):
    with database() as db:
        for table in ('analyses', 'habits', 'telemetry', 'tracked_players'):
            db.execute(f'DELETE FROM {table} WHERE owner=?', (owner,))
        db.execute('DELETE FROM feedback WHERE reviewer=?', (owner,))


def record_event(owner, event, resource='', decision=''):
    with database() as db:
        db.execute('DELETE FROM telemetry WHERE created<?', (int(time.time()) - 30*86400,))
        db.execute('INSERT INTO telemetry(owner,event,created,resource,decision) VALUES(?,?,?,?,?)', (owner, event, int(time.time()), resource, decision))
