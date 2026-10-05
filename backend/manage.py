"""Explicit local operations: backup, verify restore, retention, pilot counters."""
import argparse
import csv
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
import storage


def backup(destination):
    path=Path(destination)
    if path.exists():
        raise ValueError('Destination already exists; choose a new file.')
    path.parent.mkdir(parents=True,exist_ok=True)
    with storage.database() as source, closing(sqlite3.connect(path)) as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def restore(source, destination):
    src=Path(source).resolve(); dst=Path(destination).resolve()
    if not src.is_file() or dst.exists():
        raise ValueError('A valid source and a NEW destination are required.')
    dst.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(f'{src.as_uri()}?mode=ro',uri=True)) as original, closing(sqlite3.connect(dst)) as target:
        if original.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Backup integrity failed')
        original.backup(target)


def prune():
    with storage.database() as db:
        now=int(time.time())
        for table in ('cache','limits'):
            db.execute(f'DELETE FROM {table} WHERE expires<=?',(now,))
        db.execute('DELETE FROM telemetry WHERE created<?',(now-30*86400,))


def metrics():
    now=int(time.time())
    with storage.database() as db:
        since=now-30*86400
        counts=[dict(row) for row in db.execute('SELECT event,COUNT(*) AS occurrences,COUNT(DISTINCT owner) AS users FROM telemetry WHERE created>=? GROUP BY event',(since,))]
        analyses=db.execute('SELECT COUNT(*) FROM analyses').fetchone()[0]
        verdicts=[dict(row) for row in db.execute('SELECT verdict,COUNT(*) AS count FROM feedback GROUP BY verdict')]
        events=[dict(row) for row in db.execute('SELECT owner,event,created,resource FROM telemetry WHERE created>=? ORDER BY created,rowid',(since,))]
    searches={e['owner'] for e in events if e['event']=='search_completed'}
    reviews={}
    for event in events:
        if event['event']=='evidence_opened' and event['resource']:
            reviews.setdefault(event['owner'],[]).append(event)
    mature={owner:rows for owner,rows in reviews.items() if rows[0]['created']<=now-7*86400}
    returned=sum(any(e['resource']!=rows[0]['resource'] and rows[0]['created']<=e['created']<=rows[0]['created']+7*86400 for e in rows[1:]) for rows in mature.values())
    return {'window_days':30,'events':counts,'stored_analyses':analyses,'feedback':verdicts,
            'search_users_with_evidence':{'numerator':len(searches & reviews.keys()),'denominator':len(searches)},
            'second_match_review_in_7_days':{'numerator':returned,'denominator':len(mature)},
            'note':'7-day metric excludes recent cohorts and repeated views of the same match. First observations are limited to retained 30-day telemetry; not independent quality validation or causal improvement.'}


def evaluation_sheet(destination):
    """Local worksheet; leaves reviewer labels blank. Contains private match data."""
    with storage.database() as db:
        rows=db.execute('SELECT payload FROM analyses ORDER BY created').fetchall()
    seen=set()
    with Path(destination).open('x',encoding='utf-8-sig',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['case','match_id','version','rule','timestamp_ms','facts','limitations','reviewer_1','reviewer_2','notes'])
        for row in rows:
            report=json.loads(row['payload'])
            for decision in report['decisions']:
                key=(report['match_id'],report['analysis_version'],decision['id'])
                if key in seen: continue
                seen.add(key)
                writer.writerow([len(seen),report['match_id'],report['analysis_version'],decision['rule_id'],decision['timestamp'],
                                 ' | '.join(decision['facts']),' | '.join(decision['limitations']),'','',''])


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('metrics'); sub.add_parser('prune')
    b=sub.add_parser('backup'); b.add_argument('destination')
    e=sub.add_parser('evaluation'); e.add_argument('destination')
    r=sub.add_parser('restore'); r.add_argument('source'); r.add_argument('destination')
    args=parser.parse_args()
    if args.command=='metrics': print(json.dumps(metrics(),indent=2))
    elif args.command=='prune': prune()
    elif args.command=='backup': backup(args.destination)
    elif args.command=='evaluation': evaluation_sheet(args.destination)
    else: restore(args.source,args.destination)
