"""Versioned public contract. Unknown measurements stay null."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class Position(Model):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class Event(Model):
    id: str
    type: Literal['WARD_PLACED', 'CHAMPION_KILL', 'ELITE_MONSTER_KILL', 'BUILDING_KILL', 'ITEM_PURCHASED']
    timestamp: int = Field(ge=0)
    detail: str
    position_pct: Position | None = None
    position_estimated: bool = False


class RoutePoint(Model):
    timestamp: int = Field(ge=0)
    position_pct: Position


class Pick(Model):
    champion_name: str
    champion_id: int
    role: str


class Evaluation(Model):
    key: str
    name: str
    score: int
    reason: str


class Phase(Model):
    title: str
    start: int
    end: int | None
    action: str


class GamePlan(Model):
    win_condition: str
    phases: list[Phase]


class Stats(Model):
    champion_name: str
    champion_id: int
    role: str
    team_id: int
    win: bool
    game_created_at: int
    duration_seconds: int = Field(gt=0)
    queue_id: int
    patch: str
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    kda: float | None = None
    cs_per_min: float | None = None
    vision_score: float | None = None
    vision_per_min: float | None = None
    damage_per_min: float | None = None
    gold_per_min: float | None = None
    wards_placed: int | None = None
    wards_killed: int | None = None
    turret_damage: int | None = None
    kill_participation_pct: float | None = None
    lane_opponent: str | None = None
    cs_delta: int | None = None
    gold_delta: int | None = None


class Alternative(Model):
    label: str
    tradeoff: str


class Decision(Model):
    id: str
    rule_id: str
    timestamp: int
    title: str
    prompt: str
    facts: list[str]
    interpretation: str
    evidence_ids: list[str]
    alternatives: list[Alternative]
    limitations: list[str]
    confidence: Literal['observed_sequence'] = 'observed_sequence'
    context: list[str] = Field(default_factory=list)


class HabitMetric(Model):
    eligible: bool
    numerator: int
    denominator: int


class Playbook(Model):
    schema_version: Literal[2] = 2
    analysis_version: str
    match_id: str
    data_source: Literal['riot', 'demo']
    status: Literal['ready', 'unsupported', 'insufficient_data']
    queue_id: int | None = None
    map_id: int | None = None
    patch: str = ''
    data_quality: list[str] = Field(default_factory=list)
    archetype: str = 'Evidencia insuficiente'
    model_key: str = 'UNKNOWN'
    model_reason: str = ''
    model_evaluation: list[Evaluation] = Field(default_factory=list)
    composition: list[Pick] = Field(default_factory=list)
    enemy_composition: list[Pick] = Field(default_factory=list)
    match_stats: Stats | None = None
    game_plan: GamePlan | None = None
    player_route: list[RoutePoint] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    habit_metric: HabitMetric = Field(default_factory=lambda: HabitMetric(eligible=False, numerator=0, denominator=0))
    saved: bool = False


class Account(Model):
    puuid: str = Field(min_length=10, max_length=100)
    gameName: str
    tagLine: str


class PlayerMatches(Model):
    account: Account
    matches: list[str]


class TrackedPlayer(Model):
    puuid: str
    name: str


class HabitProgress(Model):
    started: int
    version: str
    completed: int = Field(ge=0,le=5)
    target: Literal[5]
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)


class ShareSummary(Model):
    token: str
    match_id: str
    expires: int


class FeedbackSummary(Model):
    decision: str
    verdict: Literal['agree','context','incorrect']
    comment: str
    match_id: str
    created: int


class History(Model):
    analyses: list[Playbook]
    habit: HabitProgress | None
    shares: list[ShareSummary]
    feedback: list[FeedbackSummary]
