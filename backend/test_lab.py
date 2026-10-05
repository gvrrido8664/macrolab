import copy
import json
import os
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import closing
from unittest.mock import patch

import requests
import uvicorn
import storage
from analysis import build_report, VERSION
from demo import fixtures, report, PUUID
from main import app
from riot_api import RiotAPIClient, PlaybookEngine


class EvidenceTest(unittest.TestCase):
    def test_three_rules_have_real_event_references(self):
        value=report()
        self.assertEqual(len(value.decisions),3)
        self.assertEqual(value.habit_metric.numerator,1)
        self.assertEqual(value.habit_metric.denominator,2)
        ids={e.id for e in value.events}
        self.assertTrue(all(set(d.evidence_ids)<=ids for d in value.decisions))
        self.assertTrue(all(len(d.alternatives)==2 for d in value.decisions))

    def test_window_boundary_and_no_future_information_in_context(self):
        match,timeline=fixtures()
        for frame in timeline['info']['frames']:
            for e in frame['events']:
                if e['type']=='CHAMPION_KILL' and e.get('victimId')==5:
                    e['timestamp']=599999
        value=build_report('DEMO_001',match,timeline,PUUID,'demo')
        self.assertFalse(any(d.rule_id=='death_before_objective' for d in value.decisions))
        for frame in timeline['info']['frames']:
            for e in frame['events']:
                if e['type']=='CHAMPION_KILL' and e.get('victimId')==5:
                    e['timestamp']=600000
        value=build_report('DEMO_001',match,timeline,PUUID,'demo')
        self.assertTrue(any(d.rule_id=='death_before_objective' for d in value.decisions))
        before=value.decisions
        match['info']['participants'][4]['goldEarned']=999999
        self.assertEqual(before,build_report('DEMO_001',match,timeline,PUUID,'demo').decisions)

    def test_unsupported_mode_has_no_strategy(self):
        match,timeline=fixtures(); match['info']['queueId']=450
        value=build_report('DEMO_001',match,{},PUUID)
        self.assertEqual(value.status,'unsupported'); self.assertEqual(value.decisions,[])
        self.assertIsNone(value.game_plan)

    def test_missing_frames_abstains_and_missing_statistics_are_null(self):
        match,timeline=fixtures(); del timeline['info']['frames'][10]
        del match['info']['participants'][4]['visionScore']
        value=build_report('DEMO_001',match,timeline,PUUID)
        self.assertEqual(value.status,'insufficient_data'); self.assertFalse(value.habit_metric.eligible)
        self.assertIsNone(value.match_stats.vision_score)

    def test_invalid_info_and_missing_player_are_rejected(self):
        match,timeline=fixtures()
        for invalid in ({'info':None}, {'info':[]}):
            with self.assertRaises(ValueError): build_report('DEMO_001',invalid,timeline,PUUID)
        with self.assertRaises(ValueError): build_report('DEMO_001',match,timeline,'not-a-participant')
        self.assertEqual(PlaybookEngine.select_archetype([])[0],'UNKNOWN')

    def test_wards_are_not_assigned_fake_positions(self):
        value=report(); ward=next(e for e in value.events if e.type=='WARD_PLACED')
        self.assertIsNone(ward.position_pct); self.assertTrue(ward.position_estimated)
        self.assertEqual(ward.timestamp,599000)


class StoreTest(unittest.TestCase):
    def test_relative_database_and_backup_use_backend_directory(self):
        from pathlib import Path
        from manage import backup
        with tempfile.TemporaryDirectory() as directory, patch.object(storage, 'ROOT', Path(directory)), patch.dict(os.environ, {'MACROLAB_DB_PATH':'data/pilot.sqlite3'}):
            storage.record_event('operator-check', 'search_completed')
            backup(Path(directory) / 'backup.sqlite3')
            self.assertTrue((Path(directory) / 'data/pilot.sqlite3').is_file())
            with closing(sqlite3.connect(Path(directory) / 'backup.sqlite3')) as db:
                self.assertEqual(db.execute('SELECT owner FROM telemetry').fetchone()[0], 'operator-check')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'MACROLAB_DB_PATH':self.temp.name+'/test.sqlite3'})
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_isolation_idempotency_restart_and_revocation(self):
        value=report().model_dump()
        storage.save_analysis('alice',PUUID,value); storage.save_analysis('alice',PUUID,value)
        storage.save_analysis('alice','other-player',value)
        self.assertEqual(len(storage.history('alice',PUUID)['analyses']),1)
        self.assertEqual(storage.history('bob',PUUID)['analyses'],[])
        self.assertIsNone(storage.create_share('bob',PUUID,'DEMO_001',VERSION))
        token=storage.create_share('alice',PUUID,'DEMO_001',VERSION)
        storage.revoke_share('bob',token); self.assertIsNotNone(storage.read_share(token))
        storage.revoke_share('alice',token); self.assertIsNone(storage.read_share(token))
        self.assertEqual(len(storage.history('alice','other-player')['analyses']),1)

    def test_habit_uses_new_games_once_and_same_version(self):
        value=report().model_dump()
        with patch('storage.time.time',return_value=1000): storage.start_habit('alice',PUUID,VERSION)
        for n in range(7):
            item=copy.deepcopy(value); item['match_id']=f'LA2_{n}'; item['match_stats']['game_created_at']=1000001+n
            storage.save_analysis('alice',PUUID,item)
        old=copy.deepcopy(value); old['match_stats']['game_created_at']=999999
        storage.save_analysis('alice',PUUID,old)
        wrong=copy.deepcopy(value); wrong['match_id']='LA2_100'; wrong['analysis_version']='other'; wrong['match_stats']['game_created_at']=1000002
        storage.save_analysis('alice',PUUID,wrong)
        habit=storage.history('alice',PUUID)['habit']
        self.assertEqual(habit['completed'],5); self.assertEqual(habit['denominator'],10)
        self.assertEqual(habit['numerator'],5)

    def test_expiry_and_delete_cascade(self):
        storage.save_analysis('alice',PUUID,report().model_dump())
        token=storage.create_share('alice',PUUID,'DEMO_001',VERSION)
        with patch('storage.time.time',return_value=time.time()+8*86400): self.assertIsNone(storage.read_share(token))
        storage.delete_user('alice'); self.assertIsNone(storage.read_share(token))

    def test_cache_expiration_and_limits(self):
        with patch('storage.time.time',return_value=1000):
            storage.cache_set('test',{'v':1},10)
            self.assertEqual(storage.cache_get('test'),{'v':1})
            self.assertEqual(storage.admit('user',1,60),0)
            self.assertEqual(storage.admit('user',1,60),60)
        with patch('storage.time.time',return_value=1011): self.assertIsNone(storage.cache_get('test'))

    def test_backup_restore_and_refuse_overwrite(self):
        from manage import backup,restore
        storage.save_analysis('alice',PUUID,report().model_dump())
        backup(self.temp.name+'/backup.db')
        restore(self.temp.name+'/backup.db',self.temp.name+'/restored.db')
        with patch.dict(os.environ,{'MACROLAB_DB_PATH':self.temp.name+'/restored.db'}):
            self.assertEqual(len(storage.history('alice',PUUID)['analyses']),1)
        with self.assertRaises(ValueError): restore(self.temp.name+'/backup.db',self.temp.name+'/restored.db')

    def test_riot_cache_and_deadline(self):
        key='/example'+json.dumps(None,sort_keys=True)
        storage.cache_set(key,{'cached':True},60)
        with patch.dict(os.environ,{'RIOT_API_KEY':'test-key'}), patch('requests.get') as get:
            client=RiotAPIClient()
            self.assertEqual(client._get('/example'),{'cached':True}); get.assert_not_called()
            client.deadline=0
            with self.assertRaises(requests.Timeout): client._get('/uncached')
            get.assert_not_called()

    def test_migration_metrics_and_evaluation_sheet(self):
        from manage import metrics,evaluation_sheet
        with closing(sqlite3.connect(self.temp.name+'/test.sqlite3')) as db:
            db.execute('CREATE TABLE telemetry(owner TEXT,event TEXT,created INTEGER)')
            db.execute('PRAGMA user_version=1')
            db.execute('INSERT INTO telemetry VALUES(?,?,?)',('old','search_completed',1))
            db.commit()
        now=10_000_000
        with patch('storage.time.time',return_value=now-8*86400):
            storage.record_event('alice','search_completed')
            storage.record_event('alice','evidence_opened','LA2_1','decision')
            storage.record_event('repeat','evidence_opened','LA2_1','decision')
        with patch('storage.time.time',return_value=now-7*86400):
            storage.record_event('alice','evidence_opened','LA2_2','decision')
            storage.record_event('repeat','evidence_opened','LA2_1','decision')
        with patch('storage.time.time',return_value=now):
            storage.record_event('recent','evidence_opened','LA2_1','decision')
            result=metrics()
            self.assertEqual(result['second_match_review_in_7_days'],{'numerator':1,'denominator':2})
            self.assertEqual(result['search_users_with_evidence'],{'numerator':1,'denominator':1})
        storage.save_analysis('alice',PUUID,report().model_dump())
        evaluation_sheet(self.temp.name+'/review.csv')
        with open(self.temp.name+'/review.csv',encoding='utf-8-sig') as handle:
            self.assertIn('reviewer_1',handle.readline())
            self.assertEqual(len(handle.readlines()),3)
        with self.assertRaises(FileExistsError): evaluation_sheet(self.temp.name+'/review.csv')


class HTTPTest(unittest.TestCase):
    """Actual ASGI/HTTP stack, using installed requests + uvicorn (no test framework)."""
    def setUp(self):
        StoreTest.setUp(self)
        self.secret='s'*40
        self.config=patch.dict(os.environ,{'MACROLAB_SERVICE_SECRET':self.secret,'RIOT_API_KEY':''})
        self.config.start()
        sock=socket.socket(); sock.bind(('127.0.0.1',0))
        self.url=f'http://127.0.0.1:{sock.getsockname()[1]}'
        self.server=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False))
        self.thread=threading.Thread(target=self.server.run,kwargs={'sockets':[sock]},daemon=True); self.thread.start()
        for _ in range(200):
            if self.server.started: break
            time.sleep(.01)
        self.assertTrue(self.server.started)
        self.headers={'X-Service-Key':self.secret,'X-User-ID':'alice'}

    def tearDown(self):
        self.server.should_exit=True; self.thread.join(5); self.config.stop(); StoreTest.tearDown(self)

    def test_service_auth_missing_key_and_validation(self):
        self.assertEqual(requests.get(self.url+'/api/v1/history?puuid='+PUUID,timeout=3).status_code,401)
        response=requests.get(self.url+'/api/v1/matches/LA2_123/playbook?puuid='+PUUID,headers=self.headers,timeout=3)
        self.assertEqual(response.status_code,503)
        self.assertEqual(requests.get(self.url+'/api/v1/matches/bad/playbook?puuid='+PUUID,headers=self.headers,timeout=3).status_code,422)

    def test_complete_http_analysis_and_feedback(self):
        match,timeline=fixtures()
        with patch.dict(os.environ,{'RIOT_API_KEY':'test-key'}), patch.object(RiotAPIClient,'get_match_details',return_value=match), patch.object(RiotAPIClient,'get_match_timeline',return_value=timeline):
            response=requests.get(self.url+'/api/v1/matches/LA2_123/playbook?puuid='+PUUID,headers=self.headers,timeout=3)
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.json()['saved'])
        response=requests.post(self.url+'/api/v1/shares',headers=self.headers,json={'puuid':PUUID,'match_id':'LA2_123','version':VERSION},timeout=3)
        token=response.json()['token']
        payload=requests.get(self.url+'/api/v1/shares/'+token,headers=self.headers,timeout=3).json()
        feedback={'decision':payload['decisions'][0]['id'],'verdict':'context','comment':'Revisar la oleada.'}
        response=requests.post(self.url+'/api/v1/shares/'+token+'/feedback',headers=self.headers,json=feedback,timeout=3)
        self.assertEqual(response.status_code,200,response.text)
        requests.delete(self.url+'/api/v1/shares/'+token,headers=self.headers,timeout=3)
        self.assertEqual(requests.post(self.url+'/api/v1/shares/'+token+'/feedback',headers=self.headers,json=feedback,timeout=3).status_code,404)

    def test_upstream_errors_preserve_retry_and_invalid_payload_is_502(self):
        for code in (401,403,429,500):
            error_response=requests.Response(); error_response.status_code=code; error_response.headers['Retry-After']='17'
            with patch.dict(os.environ,{'RIOT_API_KEY':'test-key'}), patch.object(RiotAPIClient,'get_match_details',side_effect=requests.HTTPError(response=error_response)):
                response=requests.get(self.url+'/api/v1/matches/LA2_123/playbook?puuid='+PUUID,headers=self.headers,timeout=3)
            self.assertEqual(response.status_code,429 if code==429 else 502)
            if code==429: self.assertEqual(response.headers['Retry-After'],'17')
        with patch.dict(os.environ,{'RIOT_API_KEY':'test-key'}), patch.object(RiotAPIClient,'get_match_details',return_value={'info':None}):
            self.assertEqual(requests.get(self.url+'/api/v1/matches/LA2_123/playbook?puuid='+PUUID,headers=self.headers,timeout=3).status_code,502)


if __name__=='__main__': unittest.main()
