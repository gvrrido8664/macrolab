"""Local end-to-end test server: temporary DB and synthetic Riot responses only."""
import os
import tempfile
from unittest.mock import patch
import uvicorn
from main import app
from demo import fixtures, PUUID
from riot_api import RiotAPIClient

if __name__ == '__main__':
    match,timeline=fixtures()
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'MACROLAB_DB_PATH':directory+'/test.sqlite3','RIOT_API_KEY':'fixture-only'}), \
         patch.object(RiotAPIClient,'get_account_by_riot_id',return_value={'puuid':PUUID,'gameName':'Ejemplo','tagLine':'LAS'}), \
         patch.object(RiotAPIClient,'get_recent_match_ids',return_value=['LA2_123']), \
         patch.object(RiotAPIClient,'get_match_details',return_value=match), \
         patch.object(RiotAPIClient,'get_match_timeline',return_value=timeline):
        uvicorn.run(app,host='127.0.0.1',port=8011,access_log=False)
