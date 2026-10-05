import os
import json
import time
import storage
from typing import Any
from urllib.parse import quote

import requests

class RiotAPIClient:
    BASE_URL_AMERICAS = "https://americas.api.riotgames.com"

    def __init__(self):
        self.api_key = os.getenv("RIOT_API_KEY")
        self.deadline = time.monotonic() + 18

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("RGAPI-xxxx"))

    def _get(self, path: str, params: dict[str, int] | None = None):
        if not self.is_configured:
            raise ValueError("RIOT_API_KEY is not configured")
        key = path + json.dumps(params, sort_keys=True)
        cached = storage.cache_get(key)
        if cached is not None:
            return cached
        retry = storage.admit('riot-global', 15, 1) or storage.admit('riot-two-minutes', 80, 120)
        if retry:
            response = requests.Response()
            response.status_code = 429
            response.headers['Retry-After'] = str(retry)
            raise requests.HTTPError(response=response)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise requests.Timeout()
        # Streaming checks the total deadline as well as socket timeouts.
        with requests.get(f"{self.BASE_URL_AMERICAS}{path}", headers={"X-Riot-Token": self.api_key},
                          params=params, timeout=(min(2, remaining), min(4, remaining)), stream=True) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                if time.monotonic() >= self.deadline:
                    raise requests.Timeout()
                size += len(chunk)
                if size > 10_000_000:
                    raise ValueError('Riot response too large')
                chunks.append(chunk)
            if time.monotonic() >= self.deadline:
                raise requests.Timeout()
            data = json.loads(b''.join(chunks))
        storage.cache_set(key, data, 60 if params else 30*86400 if '/matches/' in path else 300)
        return data

    def get_account_by_riot_id(self, game_name: str, tag_line: str):
        return self._get(
            f"/riot/account/v1/accounts/by-riot-id/{quote(game_name, safe='')}/{quote(tag_line, safe='')}"
        )

    def get_recent_match_ids(self, puuid: str, count: int = 5):
        return self._get(
            f"/lol/match/v5/matches/by-puuid/{quote(puuid, safe='')}/ids",
            {"start": 0, "count": count, "queue": 420},
        )
        
    def get_match_timeline(self, match_id: str):
        """
        Obtiene el timeline real; la demo es un flujo explícito y separado.
        """
        return self._get(f"/lol/match/v5/matches/{quote(match_id, safe='')}/timeline")

    def get_match_details(self, match_id: str):
        return self._get(f"/lol/match/v5/matches/{quote(match_id, safe='')}")


class PlaybookEngine:
    """Motor que procesa los datos crudos y evalúa la disciplina macro."""
    
    SR_MAX_X = 14820
    SR_MAX_Y = 14881

    ARCHETYPES = {
        "SPLIT_PUSH_131": {
            "name": "Presión lateral (4-1 / 1-3-1)",
            "description": "Un duelista presiona una lateral; dos amenazas permiten ocupar ambas. La visión debe cubrir rutas de colapso."
        },
        "FRONT_TO_BACK": {
            "name": "Teamfight (Front-to-Back)",
            "description": "Peleas 5v5 estructuradas con primera línea y daño sostenido. La visión se concentra en objetivos neutrales."
        },
        "POKE": {
            "name": "Asedio y poke",
            "description": "Desgaste a distancia antes de disputar objetivos. Requiere visión segura alrededor del río."
        },
        "PROTECT_CARRY": {
            "name": "Proteger al carry",
            "description": "La condición de victoria es mantener con vida al tirador. Requiere visión defensiva y de flancos."
        },
        "ENGAGE": {
            "name": "Iniciación y teamfight",
            "description": "Busca peleas decisivas desde niebla de guerra. Requiere control del río y entradas a objetivos."
        },
        "PICK": {
            "name": "Cazadas y picks",
            "description": "Busca aislar rivales antes del objetivo. Requiere visión profunda en rutas de rotación."
        },
        "DIVE": {
            "name": "Dive / acceso a retaguardia",
            "description": "Amenaza a los carries enemigos con entradas profundas y flancos coordinados."
        },
        "COUNTER_ENGAGE": {
            "name": "Counter-engage / disengage",
            "description": "Absorbe la iniciación rival, protege la retirada y castiga al enemigo cuando entra."
        }
    }

    # ponytail: listas acotadas; reemplazar por clasificación versionada cuando haya datos validados por parche.
    SPLIT_PUSH_CHAMPIONS = {"Camille", "Fiora", "Gwen", "Illaoi", "Irelia", "Jax", "Nasus", "Quinn", "Singed", "Trundle", "Tryndamere", "Yorick"}
    POKE_CHAMPIONS = {"Ashe", "Caitlyn", "Corki", "Ezreal", "Hwei", "Jayce", "Jhin", "Karma", "Lux", "Mel", "Nidalee", "Taliyah", "Varus", "Velkoz", "Xerath", "Ziggs", "Zoe"}
    ENGAGE_CHAMPIONS = {"Alistar", "Amumu", "Diana", "Fiddlesticks", "Galio", "Gragas", "Hecarim", "JarvanIV", "Kennen", "Leona", "Lissandra", "Malphite", "Maokai", "MonkeyKing", "Nautilus", "Neeko", "Ornn", "Poppy", "Rakan", "Rammus", "Rell", "Sejuani", "Sion", "Skarner", "Vi", "Zac"}
    PICK_CHAMPIONS = {"Ahri", "Ashe", "Bard", "Blitzcrank", "Camille", "Elise", "Leblanc", "Lux", "Morgana", "Nautilus", "Neeko", "Nocturne", "Pyke", "Rengar", "Skarner", "Thresh", "TwistedFate", "Vi", "Zoe"}
    DIVE_CHAMPIONS = {"Akali", "Ambessa", "Camille", "Diana", "Ekko", "Evelynn", "Fizz", "Hecarim", "Irelia", "JarvanIV", "Kassadin", "Katarina", "Kayn", "Khazix", "Leblanc", "LeeSin", "Malphite", "MasterYi", "Naafiri", "Nilah", "Nocturne", "Pantheon", "Qiyana", "Rakan", "Rengar", "Samira", "Talon", "Vi", "Viego", "MonkeyKing", "XinZhao", "Yasuo", "Yone", "Zac", "Zed"}
    DISENGAGE_CHAMPIONS = {"Alistar", "Anivia", "Ashe", "Bard", "Braum", "Gragas", "Ivern", "Janna", "Karma", "Lulu", "Milio", "Morgana", "Nami", "Orianna", "Poppy", "Renata", "Seraphine", "Shen", "Sona", "Soraka", "TahmKench", "Taric", "Thresh", "Trundle", "Vex", "Xayah", "Yuumi", "Zilean", "Zyra"}
    PROTECTORS = {"Braum", "Ivern", "Janna", "Karma", "Lulu", "Milio", "Nami", "Orianna", "Renata", "Seraphine", "Shen", "Sona", "Soraka", "TahmKench", "Taric", "Yuumi", "Zilean"}
    HYPER_CARRIES = {"Aphelios", "Jinx", "Kaisa", "KogMaw", "Smolder", "Twitch", "Vayne", "Yunara", "Zeri"}
    FRONTLINE_CHAMPIONS = {"Alistar", "Amumu", "Braum", "Chogath", "DrMundo", "Galio", "KSante", "Leona", "Malphite", "Maokai", "Nautilus", "Nunu", "Ornn", "Poppy", "Rammus", "Rell", "Sejuani", "Shen", "Sion", "Skarner", "TahmKench", "Zac"}
    ROLE_ORDER = {"TOP": 0, "JUNGLE": 1, "MIDDLE": 2, "BOTTOM": 3, "UTILITY": 4}
    PLAN_GUIDES = {
        "SPLIT_PUSH_131": ("Crear una amenaza lateral que obligue al rival a dividirse y convertirla en torres.", ["Gana prioridad y conserva Teleport.", "Presiona la lateral opuesta al próximo objetivo.", "Amenaza inhibidor; rota solo si el rival responde con uno."]),
        "FRONT_TO_BACK": ("Mantener al daño sostenido detrás de la primera línea y pelear de frente.", ["Escala sin ceder oleadas ni objetivos gratuitos.", "Agrupa primero y controla las entradas al objetivo.", "Avanza de tanque a carry; no rompas la formación."]),
        "POKE": ("Desgastar al rival antes de que pueda iniciar o disputar un objetivo.", ["Consigue prioridad sin intercambios largos.", "Llega antes, coloca visión y asedia desde rango.", "No entres cuerpo a cuerpo; reinicia el asedio si fallan habilidades."]),
        "PROTECT_CARRY": ("Mantener vivo al carry para que gane la pelea con daño sostenido.", ["Acelera el oro del carry y evita riesgos aislados.", "Controla flancos y acompaña sus rotaciones.", "Reserva control y escudos para quien alcance al carry."]),
        "ENGAGE": ("Forzar una pelea favorable cuando el equipo esté agrupado y pueda seguir la iniciación.", ["Identifica quién inicia y qué enfriamientos necesita.", "Niega visión y busca superioridad antes del objetivo.", "Inicia solo con seguimiento; evita entradas escalonadas."]),
        "PICK": ("Eliminar a un rival aislado antes de disputar el objetivo.", ["Genera prioridad para entrar primero al río.", "Controla rutas de rotación y juega desde niebla.", "Convierte cada captura en torre, inhibidor o objetivo."]),
        "DIVE": ("Alcanzar juntos la retaguardia enemiga y sacar de la pelea a su carry.", ["Conserva recursos de movilidad y localiza al objetivo.", "Prepara un flanco y sincroniza las entradas.", "Entra sobre el mismo carry y define una ruta de salida."]),
        "COUNTER_ENGAGE": ("Absorber la entrada rival, separar a sus amenazas y responder con ventaja.", ["Evita gastar las herramientas defensivas sin necesidad.", "Cubre flancos y obliga al rival a entrar por una ruta visible.", "Protege primero; contraataca cuando termine la iniciación rival."]),
    }

    @staticmethod
    def extract_composition(match_data: dict[str, Any], puuid: str, enemy: bool = False) -> list[dict[str, Any]]:
        participants = match_data.get("info", {}).get("participants", [])
        if not isinstance(participants, list):
            raise ValueError("Match participants must be a list")

        player = next((participant for participant in participants if participant.get("puuid") == puuid), None)
        if not player:
            raise ValueError("Player is not present in match")

        composition = [
            {
                "champion_name": participant.get("championName", "Desconocido"),
                "champion_id": participant.get("championId", 0),
                "role": participant.get("teamPosition") or participant.get("individualPosition") or "UNKNOWN",
            }
            for participant in participants
            if (participant.get("teamId") != player.get("teamId")) == enemy
        ]
        return sorted(composition, key=lambda pick: PlaybookEngine.ROLE_ORDER.get(pick["role"], 99))

    @staticmethod
    def select_archetype(composition: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
        if not composition:
            return "UNKNOWN", "No hay composición suficiente.", []
        names = {pick["champion_name"] for pick in composition}
        split = [pick["champion_name"] for pick in composition if pick["role"] in {"TOP", "MIDDLE"} and pick["champion_name"] in PlaybookEngine.SPLIT_PUSH_CHAMPIONS]
        poke = sorted(names & PlaybookEngine.POKE_CHAMPIONS)
        engage = sorted(names & PlaybookEngine.ENGAGE_CHAMPIONS)
        picks = sorted(names & PlaybookEngine.PICK_CHAMPIONS)
        dive = sorted(names & PlaybookEngine.DIVE_CHAMPIONS)
        disengage = sorted(names & PlaybookEngine.DISENGAGE_CHAMPIONS)
        carry = next((pick["champion_name"] for pick in composition if pick["role"] == "BOTTOM" and pick["champion_name"] in PlaybookEngine.HYPER_CARRIES), None)
        protector = next((pick["champion_name"] for pick in composition if pick["role"] == "UTILITY" and pick["champion_name"] in PlaybookEngine.PROTECTORS), None)
        frontline = sorted(names & PlaybookEngine.FRONTLINE_CHAMPIONS)

        evaluations = [
            {"key": "PROTECT_CARRY", "score": 7 if carry and protector else 0, "reason": f"Sinergia directa {protector} + {carry}." if carry and protector else "Falta una pareja de hipercarry y protector."},
            {"key": "SPLIT_PUSH_131", "score": 4 + len(split) * 2 if split else 0, "reason": f"Amenaza lateral: {', '.join(split)} ({'dos líneas posibles' if len(split) > 1 else 'una línea'})." if split else "No hay duelista lateral en TOP o MID."},
            {"key": "POKE", "score": len(poke) * 2 if len(poke) >= 2 else 0, "reason": f"Alcance coordinado de {', '.join(poke)}." if len(poke) >= 2 else "Se necesitan al menos dos fuentes de poke."},
            {"key": "ENGAGE", "score": 1 + len(engage) * 2 if len(engage) >= 2 else 0, "reason": f"Iniciación fiable de {', '.join(engage)}." if len(engage) >= 2 else "Se necesitan al menos dos iniciadores fiables."},
            {"key": "PICK", "score": 1 + len(picks) * 2 if len(picks) >= 2 else 0, "reason": f"Herramientas de captura de {', '.join(picks)}." if len(picks) >= 2 else "Se necesitan al menos dos herramientas de captura."},
            {"key": "DIVE", "score": 1 + len(dive) * 2 if len(dive) >= 2 else 0, "reason": f"Acceso a retaguardia de {', '.join(dive)}." if len(dive) >= 2 else "Se necesitan al menos dos amenazas de dive."},
            {"key": "COUNTER_ENGAGE", "score": 1 + len(disengage) * 2 if len(disengage) >= 2 else 0, "reason": f"Respuesta y disengage de {', '.join(disengage)}." if len(disengage) >= 2 else "Se necesitan al menos dos herramientas de respuesta o disengage."},
            {"key": "FRONT_TO_BACK", "score": 4 if frontline and any(pick["role"] == "BOTTOM" for pick in composition) else 2, "reason": f"Primera línea de {', '.join(frontline)} y daño desde retaguardia." if frontline else "Plan agrupado base al no dominar otra sinergia."},
        ]
        for evaluation in evaluations:
            evaluation["name"] = PlaybookEngine.ARCHETYPES[evaluation["key"]]["name"]
        winner = max(evaluations, key=lambda evaluation: evaluation["score"])
        return winner["key"], winner["reason"], evaluations




    @staticmethod
    def build_game_plan(archetype_key: str) -> dict[str, Any]:
        win_condition, actions = PlaybookEngine.PLAN_GUIDES[archetype_key]
        return {
            "win_condition": win_condition,
            "phases": [
                {"title": "Early game", "start": 0, "end": 14, "action": actions[0]},
                {"title": "Mid game", "start": 15, "end": 24, "action": actions[1]},
                {"title": "Late game", "start": 25, "end": None, "action": actions[2]},
            ],
        }

    @staticmethod
    def normalize_coordinates(x: float, y: float):
        pct_x = (x / PlaybookEngine.SR_MAX_X) * 100
        pct_y = 100 - ((y / PlaybookEngine.SR_MAX_Y) * 100)
        return {"x": max(0, min(100, pct_x)), "y": max(0, min(100, pct_y))}


