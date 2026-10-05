"""Explicit synthetic fixture shared by offline demo and regression checks."""
from analysis import build_report

PUUID = 'demo-player-support-001'


def fixtures():
    picks = [('Ornn',516),('Sejuani',113),('Orianna',61),('Jinx',222),('Lulu',117),('Garen',86),('Vi',254),('Ahri',103),('Ashe',22),('Nautilus',111)]
    roles = ['TOP','JUNGLE','MIDDLE','BOTTOM','UTILITY']*2
    participants = [dict(participantId=i+1, puuid=PUUID if i==4 else f'demo-participant-{i+1}', teamId=100 if i<5 else 200,
                         championName=name,championId=cid,teamPosition=roles[i],win=i<5,kills=2,deaths=3,assists=8,
                         totalMinionsKilled=30 if i==4 else 150,neutralMinionsKilled=0,goldEarned=8000,
                         visionScore=45,wardsPlaced=20,wardsKilled=5,totalDamageDealtToChampions=15000,damageDealtToTurrets=1000)
                    for i,(name,cid) in enumerate(picks)]
    moments = [dict(type='CHAMPION_KILL',timestamp=628000,killerId=7,victimId=5,position={'x':9500,'y':5500}),
               dict(type='ELITE_MONSTER_KILL',timestamp=660000,killerId=7,monsterType='DRAGON',position={'x':9800,'y':4500}),
               dict(type='ITEM_PURCHASED',timestamp=1180000,participantId=5,itemId=2055),
               dict(type='ELITE_MONSTER_KILL',timestamp=1210000,killerId=2,monsterType='DRAGON',position={'x':9800,'y':4500}),
               dict(type='CHAMPION_KILL',timestamp=1450000,killerId=4,victimId=8,assistingParticipantIds=[5],position={'x':7500,'y':7500}),
               dict(type='BUILDING_KILL',timestamp=1480000,killerId=4,teamId=200,buildingType='TOWER_BUILDING',position={'x':9000,'y':9000}),
               dict(type='WARD_PLACED',timestamp=599000,creatorId=5,wardType='YELLOW_TRINKET')]
    frames=[]
    for minute in range(31):
        frames.append(dict(timestamp=minute*60000, events=[e for e in moments if (minute-1)*60000 < e['timestamp'] <= minute*60000],
                           participantFrames={str(i):dict(position={'x':3000+minute*200,'y':4000+minute*100},totalGold=500+minute*300+i*10) for i in range(1,11)}))
    return (dict(info=dict(queueId=420,mapId=11,gameDuration=1800,gameCreation=1788652800000,gameVersion='16.17.1',participants=participants)),
            dict(metadata=dict(participants=[p['puuid'] for p in participants]),info=dict(frames=frames)))


def report():
    match,timeline=fixtures()
    return build_report('DEMO_001',match,timeline,PUUID,'demo')


if __name__ == '__main__':
    import sys
    from pathlib import Path
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(report().model_dump_json(indent=2),encoding='utf-8')
