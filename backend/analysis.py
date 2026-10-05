"""Post-match evidence, not a reconstruction of player knowledge or causality."""
import math
from models import Playbook, Stats
from riot_api import PlaybookEngine

VERSION = 'evidence-1'
WINDOW_MS = 60_000
SUPPORTED_EVENTS = {'WARD_PLACED', 'CHAMPION_KILL', 'ELITE_MONSTER_KILL', 'BUILDING_KILL', 'ITEM_PURCHASED'}


def object_info(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('info'), dict):
        raise ValueError('Invalid info object')
    return payload['info']


def position(raw):
    if isinstance(raw, dict) and all(type(raw.get(k)) in (int, float) and math.isfinite(raw[k]) for k in ('x', 'y')):
        return PlaybookEngine.normalize_coordinates(raw['x'], raw['y'])
    return None


def extract_stats(info, player, participants):
    duration = info.get('gameDuration')
    if type(duration) is not int or duration <= 0 or type(info.get('gameCreation')) is not int:
        raise ValueError('Invalid match duration or date')
    role = player.get('teamPosition') or player.get('individualPosition') or 'UNKNOWN'
    opponent = next((p for p in participants if p['teamId'] != player['teamId'] and p.get('teamPosition') == role), None)
    def measurement(key):
        value = player.get(key)
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    def rate(value):
        return round(value * 60 / duration, 2) if value is not None else None
    cs = measurement('totalMinionsKilled')
    neutral = measurement('neutralMinionsKilled')
    cs = cs + neutral if cs is not None and neutral is not None else None
    kills, deaths, assists = [measurement(k) for k in ('kills', 'deaths', 'assists')]
    team_kills = [p.get('kills') for p in participants if p['teamId'] == player['teamId']]
    total = sum(team_kills) if all(type(v) is int and v >= 0 for v in team_kills) else None
    result = dict(champion_name=player.get('championName', 'Desconocido'), champion_id=player.get('championId', 0),
                  role=role, team_id=player['teamId'], win=player.get('win', False), game_created_at=info['gameCreation'],
                  duration_seconds=duration, queue_id=info['queueId'], patch=str(info.get('gameVersion', '')),
                  kills=kills, deaths=deaths, assists=assists,
                  kda=round((kills+assists)/max(1,deaths),2) if None not in (kills,deaths,assists) else None,
                  cs_per_min=rate(cs), gold_per_min=rate(measurement('goldEarned')),
                  vision_score=measurement('visionScore'), vision_per_min=rate(measurement('visionScore')),
                  damage_per_min=rate(measurement('totalDamageDealtToChampions')),
                  wards_placed=measurement('wardsPlaced'), wards_killed=measurement('wardsKilled'),
                  turret_damage=measurement('damageDealtToTurrets'),
                  kill_participation_pct=round((kills+assists)*100/total,1) if total and kills is not None and assists is not None else None,
                  lane_opponent=opponent.get('championName') if opponent else None)
    if opponent:
        opp_cs = [opponent.get('totalMinionsKilled'), opponent.get('neutralMinionsKilled')]
        if cs is not None and all(type(v) is int for v in opp_cs):
            result['cs_delta'] = cs - sum(opp_cs)
        gold = measurement('goldEarned')
        if gold is not None and type(opponent.get('goldEarned')) is int:
            result['gold_delta'] = gold - opponent['goldEarned']
    return Stats.model_validate(result)


def build_report(match_id, match, timeline, puuid, source='riot'):
    info = object_info(match)
    base = dict(analysis_version=VERSION, match_id=match_id, data_source=source,
                queue_id=info.get('queueId'), map_id=info.get('mapId'), patch=str(info.get('gameVersion', '')))
    if info.get('queueId') != 420 or info.get('mapId') != 11:
        return Playbook(**base, status='unsupported', data_quality=['Solo se admite Solo/Dúo en la Grieta del Invocador.'])
    participants = info.get('participants')
    if not isinstance(participants, list) or not participants or any(not isinstance(p, dict) or type(p.get('participantId')) is not int or p.get('teamId') not in (100,200) for p in participants):
        raise ValueError('Invalid participants')
    ids = {p['participantId']: p['teamId'] for p in participants}
    if len(ids) != 10 or sum(t == 100 for t in ids.values()) != 5:
        raise ValueError('Duplicate participant IDs')
    player = next((p for p in participants if p.get('puuid') == puuid), None)
    if player is None:
        raise ValueError('Player absent from match')
    pid, team = player['participantId'], player['teamId']
    stats = extract_stats(info, player, participants)
    ally = PlaybookEngine.extract_composition(match, puuid)
    enemy = PlaybookEngine.extract_composition(match, puuid, enemy=True)
    key, reason, evaluations = PlaybookEngine.select_archetype(ally)
    # These are compositional alternatives, never labels learned from the outcome.
    enemy_names = {p['champion_name'] for p in enemy}
    for evaluation in evaluations:
        if evaluation['key'] == 'COUNTER_ENGAGE' and enemy_names & PlaybookEngine.ENGAGE_CHAMPIONS:
            evaluation['score'] += 1
            evaluation['reason'] += ' El rival tiene herramientas de iniciación.'
        if evaluation['key'] == 'POKE' and len(enemy_names & PlaybookEngine.DIVE_CHAMPIONS) >= 2:
            evaluation['score'] -= 1
            evaluation['reason'] += ' Hay varias amenazas de acceso rival.'
    winner = max(evaluations, key=lambda e: e['score'])
    key, reason = winner['key'], winner['reason']
    raw = object_info(timeline)
    frames = raw.get('frames')
    if not isinstance(frames, list):
        raise ValueError('Invalid frames')
    metadata = timeline.get('metadata', {})
    if not isinstance(metadata, dict) or not isinstance(metadata.get('participants'), list) or puuid not in metadata['participants']:
        raise ValueError('Player absent from timeline')
    if metadata.get('matchId', match_id) != match_id:
        raise ValueError('Mismatched timeline')
    quality = ['Posiciones muestreadas; no reconstruyen rutas ni visión activa.',
               'Las reglas son experimentales; las secuencias temporales no prueban causalidad.']
    events, route, records = [], [], []
    damaged = False
    for fi, frame in enumerate(frames):
        if not isinstance(frame, dict) or type(frame.get('timestamp')) is not int or not isinstance(frame.get('events'), list):
            damaged = True
            continue
        samples = frame.get('participantFrames')
        sample = samples.get(str(pid), {}) if isinstance(samples, dict) else {}
        point = position(sample.get('position')) if isinstance(sample, dict) else None
        if point and 0 <= frame['timestamp'] <= stats.duration_seconds*1000:
            route.append(dict(timestamp=frame['timestamp'], position_pct=point))
        for ei, raw_event in enumerate(frame['events']):
            if not isinstance(raw_event, dict):
                damaged = True
                continue
            kind, ts = raw_event.get('type'), raw_event.get('timestamp')
            if kind not in SUPPORTED_EVENTS:
                continue
            if type(ts) is not int or not 0 <= ts <= stats.duration_seconds*1000:
                damaged = True
                continue
            required = {'CHAMPION_KILL': ('killerId','victimId'), 'ELITE_MONSTER_KILL': ('killerId',), 'BUILDING_KILL': ('teamId',), 'ITEM_PURCHASED': ('participantId','itemId'), 'WARD_PLACED': ('creatorId',)}[kind]
            if any(type(raw_event.get(k)) is not int for k in required):
                damaged = True
                continue
            if kind == 'WARD_PLACED' and (raw_event['creatorId'] != pid or raw_event.get('wardType') in (None,'UNDEFINED')):
                continue
            if kind == 'ITEM_PURCHASED' and raw_event['participantId'] != pid:
                continue
            detail = str(raw_event.get('monsterType') or raw_event.get('buildingType') or raw_event.get('wardType') or raw_event.get('itemId') or '')
            if kind == 'CHAMPION_KILL':
                detail = 'Tu muerte' if raw_event['victimId'] == pid else 'Tu baja' if raw_event['killerId'] == pid else 'Baja global'
            point = position(raw_event.get('position'))
            estimated = kind == 'WARD_PLACED' and point is None
            if estimated:
                # A sample can follow the event; show it only at its own time, not as exact ward location.
                point = None
            event = dict(id=f'{fi}:{ei}', type=kind, timestamp=ts, detail=detail, position_pct=point, position_estimated=estimated)
            events.append(event)
            records.append(raw_event | {'id': event['id']})
    events.sort(key=lambda e: e['timestamp'])
    records.sort(key=lambda e: e['timestamp'])
    route.sort(key=lambda r: r['timestamp'])
    frame_times = [f.get('timestamp') for f in frames if isinstance(f, dict)]
    complete = (bool(frames) and not damaged and frame_times[0] == 0
                and all(type(t) is int for t in frame_times)
                and all(0 < b-a <= 65_000 for a,b in zip(frame_times,frame_times[1:]))
                and frame_times[-1] >= (stats.duration_seconds-60)*1000)
    if damaged:
        quality.append('Hay eventos incompletos: no se evalúan hábitos ni decisiones en esta partida.')
    if not complete:
        quality.append('Timeline incompleto; se muestran solo las observaciones disponibles.')
    decisions, metric = detect_decisions(records, frames, pid, team, ids) if complete else ([], dict(eligible=False,numerator=0,denominator=0))
    return Playbook(**base, status='ready' if complete else 'insufficient_data', data_quality=quality,
                    archetype=PlaybookEngine.ARCHETYPES[key]['name'], model_key=key, model_reason=reason,
                    model_evaluation=evaluations, composition=ally, enemy_composition=enemy,
                    match_stats=stats, game_plan=PlaybookEngine.build_game_plan(key),
                    events=events, player_route=route, decisions=decisions, habit_metric=metric)


def detect_decisions(events, frames, pid, team, teams):
    objectives = [e for e in events if e['type']=='ELITE_MONSTER_KILL' and e.get('monsterType') in ('DRAGON','BARON_NASHOR') and teams.get(e.get('killerId')) in (100,200)]
    deaths = [e for e in events if e['type']=='CHAMPION_KILL' and e['victimId']==pid]
    purchases = [e for e in events if e['type']=='ITEM_PURCHASED']
    kills = [e for e in events if e['type']=='CHAMPION_KILL' and (e['killerId']==pid or pid in (e.get('assistingParticipantIds') or []))]
    cards, exposed = [], 0
    for objective in objectives:
        preceding = [d for d in deaths if 0 < objective['timestamp']-d['timestamp'] <= WINDOW_MS]
        if preceding:
            exposed += 1
            d = preceding[-1]
            seconds = (objective['timestamp']-d['timestamp'])//1000
            cards.append(card('death_before_objective', d, objective, 'Riesgo antes de un objetivo',
                f'Tu muerte precedió en {seconds} s a una captura de {objective["monsterType"]}.',
                'Revisa si exponerte tenía una compensación razonable. El desenlace no prueba que debieras disputar.',
                [('Reducir exposición', 'Conservar recursos puede ceder presión o territorio.'), ('Aceptar el riesgo', 'Necesita una compensación concreta; el intercambio puede salir mal.')]))
        buying = [p for p in purchases if 0 < objective['timestamp']-p['timestamp'] <= WINDOW_MS]
        if buying:
            p = buying[-1]
            cards.append(card('purchase_before_objective', p, objective, 'Compra y preparación',
                f'Compraste el objeto {p["itemId"]} {(objective["timestamp"]-p["timestamp"])//1000} s antes de una captura de {objective["monsterType"]}.',
                'Revisa el tiempo disponible para volver al mapa. Una compra no demuestra un recall tardío.',
                [('Preparar recursos antes', 'Puede requerir abandonar una oleada o presión.'), ('Posponer la compra', 'Conservas presencia, pero sigues sin gastar el oro.')]))
    structures = [e for e in events if e['type']=='BUILDING_KILL' and e.get('teamId') != team]
    conversions = structures + [e for e in objectives if teams.get(e['killerId']) == team]
    for objective in conversions:
        previous = [k for k in kills if 0 < objective['timestamp']-k['timestamp'] <= WINDOW_MS]
        if previous:
            k = previous[-1]
            cards.append(card('kill_conversion', k, objective, 'De la baja al objetivo',
                f'Participaste en una baja y tu equipo obtuvo {objective.get("monsterType") or objective.get("buildingType")} {(objective["timestamp"]-k["timestamp"])//1000} s después.',
                'Es una secuencia que vale la pena revisar; no demuestra que tu baja causara el objetivo.',
                [('Buscar un objetivo', 'Exige recursos y posición favorables; puede exponerte a una respuesta.'), ('Reagrupar y gastar oro', 'Reduce exposición, pero puede cerrar una ventana de presión.')]))
    selected = {}
    for item in sorted(cards, key=lambda c: c['timestamp'], reverse=True):
        if item['rule_id'] in selected:
            continue
        # Context uses only samples at or before the question, never final gold.
        previous = [f for f in frames if f['timestamp'] <= item['timestamp'] and isinstance(f.get('participantFrames'),dict)]
        if previous:
            f = previous[-1]
            values = f['participantFrames']
            if all(isinstance(values.get(str(i)),dict) and type(values[str(i)].get('totalGold')) is int for i in teams):
                delta = sum(values[str(i)]['totalGold'] * (1 if t==team else -1) for i,t in teams.items())
                item['context'] = [f'Diferencia de oro del equipo en la muestra previa: {delta:+}. Antigüedad: {(item["timestamp"]-f["timestamp"])//1000} s. Dato de revisión, no visión del jugador.']
        selected[item['rule_id']] = item
    return list(selected.values())[:3], dict(eligible=bool(objectives), numerator=exposed, denominator=len(objectives))


def card(rule, before, after, title, fact, interpretation, alternatives):
    return dict(id=f'{rule}:{before["id"]}:{after["id"]}', rule_id=rule, timestamp=max(0,before['timestamp']-1000), title=title,
                prompt='En este instante, ¿qué alternativa considerarías y qué información necesitarías?',
                facts=[fact], interpretation=interpretation, evidence_ids=[before['id'], after['id']],
                alternatives=[dict(label=a,tradeoff=b) for a,b in alternatives],
                limitations=['No conocemos la visión disponible, todos los enfriamientos ni el estado detallado de las oleadas.',
                             'La ventana de 60 s es una heurística experimental, no una calificación de tu decisión.'])
