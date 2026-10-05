import hmac
import logging
import os
import sqlite3
import time
import uuid
import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Literal

import requests
from fastapi import FastAPI, Header, HTTPException, Path, Query, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import storage
from analysis import VERSION, build_report
from models import Playbook, PlayerMatches, History, TrackedPlayer
from riot_api import RiotAPIClient

@asynccontextmanager
async def lifespan(_app):
    from manage import prune
    async def retention():
        while True:
            try:
                await asyncio.to_thread(prune)
            except sqlite3.Error:
                logging.getLogger('uvicorn.error').error('Retention could not complete; retrying next hour.')
            await asyncio.sleep(3600)
    task=asyncio.create_task(retention())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title='MacroLab API', version='2.0.0', lifespan=lifespan)
logger = logging.getLogger('uvicorn.error')


@app.middleware('http')
async def protect_service(request: Request, call_next):
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    if request.url.path not in ('/', '/api/v1/health'):
        secret = os.getenv('MACROLAB_SERVICE_SECRET', '')
        if len(secret) < 32:
            return JSONResponse(status_code=503, content={'detail':'Servicio sin configurar.'})
        if not hmac.compare_digest(request.headers.get('x-service-key',''), secret):
            return JSONResponse(status_code=401, content={'detail':'Acceso de servicio requerido.'})
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    response.headers['Cache-Control'] = 'no-store'
    # Never log paths: shared URLs are bearer secrets and queries contain identifiers.
    logger.info('request=%s status=%s duration_ms=%d', request_id, response.status_code, (time.monotonic()-started)*1000)
    return response


def owner(x_user_id: str = Header(min_length=1, max_length=200)):
    retry = storage.admit('user:'+x_user_id, 30, 60)
    if retry:
        raise HTTPException(429, 'Demasiadas solicitudes. Espera antes de reintentar.', headers={'Retry-After':str(retry)})
    return x_user_id


@app.exception_handler(requests.RequestException)
async def riot_api_error(_request, error):
    if isinstance(error, requests.Timeout):
        return JSONResponse(status_code=504, content={'detail':'Riot tardó demasiado. Intenta de nuevo.'})
    status = error.response.status_code if isinstance(error,requests.HTTPError) and error.response is not None else 502
    messages = {401:'La clave de Riot no es válida.',403:'Riot rechazó la clave del servicio.',404:'Jugador o partida no encontrados.',429:'Límite de Riot alcanzado. Espera antes de reintentar.'}
    retry = error.response.headers.get('Retry-After','60') if status==429 else None
    return JSONResponse(status_code=status if status in (404,429) else 502,
                        content={'detail':messages.get(status,'Riot no está disponible.')},
                        headers={'Retry-After':retry} if retry else None)


@app.exception_handler(sqlite3.Error)
async def database_error(_request, _error):
    return JSONResponse(status_code=503, content={'detail':'No fue posible guardar o recuperar los datos. Intenta de nuevo.'})


@app.get('/')
@app.get('/api/v1/health')
def health_check():
    return {'status':'healthy'}


def configured_client():
    client=RiotAPIClient()
    if not client.is_configured:
        raise HTTPException(503,'Configura RIOT_API_KEY para consultar partidas reales. La demo está disponible sin clave.')
    return client


@app.get('/api/v1/players/by-riot-id/{game_name}/{tag_line}/matches',response_model=PlayerMatches)
def get_player_matches(game_name: str=Path(min_length=3,max_length=16),tag_line: str=Path(pattern=r'^[A-Za-z0-9]{3,5}$'),
                       region: Literal['LAS']=Query('LAS'),count: int=Query(5,ge=1,le=10),user: str=Depends(owner)):
    client=configured_client()
    try:
        account=client.get_account_by_riot_id(game_name,tag_line)
        result=PlayerMatches(account=account,matches=client.get_recent_match_ids(account['puuid'],count))
        with storage.database() as db:
            db.execute('INSERT OR REPLACE INTO tracked_players VALUES(?,?,?)',(user,account['puuid'],account['gameName']+'#'+account['tagLine']))
        storage.record_event(user,'search_completed')
        return result
    except (ValueError,KeyError,TypeError) as error:
        raise HTTPException(502,'Riot devolvió datos inválidos.') from error


@app.get('/api/v1/matches/{match_id}/playbook',response_model=Playbook)
def get_match_playbook(match_id: str=Path(pattern=r'^LA2_[0-9]{1,20}$'),puuid: str=Query(min_length=10,max_length=100),user: str=Depends(owner)):
    client=configured_client()
    try:
        match=client.get_match_details(match_id)
        info=match.get('info',{}) if isinstance(match,dict) else {}
        supported=isinstance(info,dict) and info.get('mapId')==11 and info.get('queueId')==420
        timeline=client.get_match_timeline(match_id) if supported else {}
        report=build_report(match_id,match,timeline,puuid)
    except (ValueError,KeyError,TypeError,AttributeError) as error:
        raise HTTPException(502,'Riot devolvió datos incompletos o el jugador no pertenece a la partida.') from error
    if report.status=='ready':
        try:
            storage.save_analysis(user,puuid,report.model_dump())
            report.saved=True
            storage.record_event(user,'analysis_completed')
        except sqlite3.Error:
            report.data_quality.append('El análisis está disponible, pero no pudo guardarse. Reintenta para conservarlo.')
    return report


@app.get('/api/v1/history',response_model=History)
def get_history(puuid: str=Query(min_length=10,max_length=100),user: str=Depends(owner)):
    return storage.history(user,puuid)


@app.get('/api/v1/players',response_model=list[TrackedPlayer])
def tracked_players(user: str=Depends(owner)):
    with storage.database() as db:
        return [dict(r) for r in db.execute('SELECT puuid,name FROM tracked_players WHERE owner=? ORDER BY name',(user,))]


class HabitInput(BaseModel):
    puuid: str=Field(min_length=10,max_length=100)


@app.post('/api/v1/habits',response_model=History)
def habit(body: HabitInput,user: str=Depends(owner)):
    reports=storage.history(user,body.puuid)['analyses']
    if not any(r['analysis_version']==VERSION and r['habit_metric']['eligible'] for r in reports):
        raise HTTPException(400,'Primero analiza una partida con objetivos evaluables.')
    storage.start_habit(user,body.puuid,VERSION)
    storage.record_event(user,'habit_started')
    return storage.history(user,body.puuid)


@app.delete('/api/v1/habits')
def stop_habit(puuid: str=Query(min_length=10,max_length=100),user: str=Depends(owner)):
    with storage.database() as db:
        db.execute('DELETE FROM habits WHERE owner=? AND puuid=?',(user,puuid))
    return {'ok':True}


class ShareInput(HabitInput):
    match_id: str=Field(pattern=r'^LA2_[0-9]{1,20}$')
    version: str=Field(min_length=1,max_length=40)


@app.post('/api/v1/shares')
def share(body: ShareInput,user: str=Depends(owner)):
    token=storage.create_share(user,body.puuid,body.match_id,body.version)
    if not token:
        raise HTTPException(404,'Análisis guardado no encontrado.')
    return {'token':token}


@app.get('/api/v1/shares/{token}',response_model=Playbook)
def shared(token: str=Path(pattern=r'^[A-Za-z0-9_-]{43}$')):
    report=storage.read_share(token)
    if report is None:
        raise HTTPException(404,'El enlace venció o fue revocado.')
    return report


@app.delete('/api/v1/shares/{token}')
def revoke(token: str=Path(pattern=r'^[A-Za-z0-9_-]{43}$'),user: str=Depends(owner)):
    storage.revoke_share(user,token)
    return {'ok':True}


class FeedbackInput(BaseModel):
    decision: str=Field(min_length=1,max_length=150)
    verdict: Literal['agree','context','incorrect']
    comment: str=Field(max_length=1000)


@app.post('/api/v1/shares/{token}/feedback')
def feedback(body: FeedbackInput,token: str=Path(pattern=r'^[A-Za-z0-9_-]{43}$'),user: str=Depends(owner)):
    with storage.database() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT a.payload FROM shares s JOIN analyses a ON a.owner=s.owner AND a.puuid=s.puuid AND a.match_id=s.match_id AND a.version=s.version WHERE s.token=? AND s.expires>?',(token,int(time.time()))).fetchone()
        if not row:
            raise HTTPException(404,'El enlace venció o fue revocado.')
        report=Playbook.model_validate_json(row['payload'])
        if body.decision not in {d.id for d in report.decisions}:
            raise HTTPException(400,'Decisión inexistente.')
        db.execute('INSERT OR REPLACE INTO feedback VALUES(?,?,?,?,?,?)',(token,user,body.decision,body.verdict,body.comment,int(time.time())))
    return {'ok':True}


class TelemetryInput(BaseModel):
    event: Literal['evidence_opened','alternative_selected']
    match_id: str=Field(pattern=r'^LA2_[0-9]{1,20}$')
    decision: str=Field(min_length=1,max_length=150)


@app.post('/api/v1/telemetry')
def telemetry(body: TelemetryInput,user: str=Depends(owner)):
    with storage.database() as db:
        rows=db.execute('SELECT payload FROM analyses WHERE owner=? AND match_id=?',(user,body.match_id)).fetchall()
    if not any(body.decision in {d.id for d in Playbook.model_validate_json(r['payload']).decisions} for r in rows):
        raise HTTPException(404,'Decisión guardada no encontrada.')
    storage.record_event(user,body.event,body.match_id,body.decision)
    return {'ok':True}


@app.get('/api/v1/account/export')
def export_account(user: str=Depends(owner)):
    with storage.database() as db:
        players=db.execute('SELECT DISTINCT puuid FROM analyses WHERE owner=?',(user,)).fetchall()
        tracked=[dict(r) for r in db.execute('SELECT puuid,name FROM tracked_players WHERE owner=?',(user,))]
        contributions=[dict(r) for r in db.execute('SELECT decision,verdict,comment,created FROM feedback WHERE reviewer=?',(user,))]
        telemetry=[dict(r) for r in db.execute('SELECT event,created,resource,decision FROM telemetry WHERE owner=?',(user,))]
    return {'players':{p['puuid']:storage.history(user,p['puuid']) for p in players},'tracked_players':tracked,'my_reviews':contributions,'telemetry':telemetry}


@app.delete('/api/v1/account')
def delete_account(user: str=Depends(owner)):
    storage.delete_user(user)
    return {'ok':True}
