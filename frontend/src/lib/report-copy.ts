import type { Event } from '../types/playbook';

export const eventNames: Record<string, string> = {
  WARD_PLACED: 'Visión colocada', CHAMPION_KILL: 'Bajas de campeones',
  ELITE_MONSTER_KILL: 'Objetivos neutrales', BUILDING_KILL: 'Estructuras destruidas', ITEM_PURCHASED: 'Compras',
};

const names: Record<string, string> = {
  INHIBITOR_BUILDING: 'un inhibidor', TOWER_BUILDING: 'una torre',
  BARON_NASHOR: 'Barón Nashor', DRAGON: 'dragón', RIFTHERALD: 'Heraldo de la Grieta',
  HORDE: 'larvas del Vacío', ATAKHAN: 'Atakhan',
  YELLOW_TRINKET: 'Tótem de visión', SIGHT_WARD: 'Guardián invisible',
  CONTROL_WARD: 'Guardián de control', BLUE_TRINKET: 'Guardián de visión lejana',
  BLUE_WARD: 'Guardián de visión lejana', TEEMO_MUSHROOM: 'Trampa de Teemo',
};

// Presentation only: saved reports and shared links keep their original evidence.
export function reportText(text: string): string {
  return text.replace(/\b[A-Z][A-Z0-9_]+\b/g, token => names[token] ?? token)
    .replace(/Compraste el objeto \d+/g, 'Compraste un objeto')
    .replace(/obtuvo (una torre|un inhibidor)/g, 'destruyó $1')
    .replace('Posiciones muestreadas; no reconstruyen rutas ni visión activa.', 'Riot registra tu posición a intervalos. El mapa no muestra todos tus movimientos ni lo que podías ver.')
    .replace('Las reglas son experimentales; las secuencias temporales no prueban causalidad.', 'Estos momentos sirven para reflexionar: que dos eventos ocurran seguidos no significa que uno haya causado el otro.')
    .replace('Timeline incompleto; se muestran solo las observaciones disponibles.', 'Faltan tramos de la partida. Solo mostramos los eventos disponibles.')
    .replace('La ventana de 60 s es una heurística experimental, no una calificación de tu decisión.', 'Buscamos eventos separados por un minuto o menos para elegir qué revisar. No asignamos una nota a tu jugada.')
    .replace('No conocemos la visión disponible, todos los enfriamientos ni el estado detallado de las oleadas.', 'Falta saber qué veías, qué habilidades estaban disponibles y cómo estaban las oleadas.')
    .replace(/Diferencia de oro del equipo en la muestra previa: ([+-]\d+)\. Antigüedad: (\d+) s\. Dato de revisión, no visión del jugador\./, 'Balance de oro de tu equipo: $1 frente al rival, registrado $2 segundos antes. Este dato es para revisar la partida; puede que no lo conocieras mientras jugabas.');
}

export function eventTitle(event: Event): string {
  if (event.type === 'ITEM_PURCHASED') return 'Compraste un objeto';
  if (event.type === 'CHAMPION_KILL') return ({ 'Tu muerte': 'Moriste', 'Tu baja': 'Eliminaste a un rival', 'Baja global': 'Un campeón fue eliminado' })[event.detail] ?? 'Un campeón fue eliminado';
  const name = names[event.detail];
  if (event.type === 'BUILDING_KILL') return name ? `Se destruyó ${name}` : 'Se destruyó una estructura';
  if (event.type === 'ELITE_MONSTER_KILL') return name ? `Objetivo conseguido: ${name}` : 'Se consiguió un objetivo neutral';
  return name ? `Colocaste visión: ${name.toLocaleLowerCase('es')}` : 'Colocaste visión';
}

export function locationNote(event: Event): string | null {
  if (event.position_pct || event.type === 'ITEM_PURCHASED') return null;
  return event.type === 'WARD_PLACED'
    ? 'Sabemos cuándo colocaste visión, pero Riot no indica dónde. Por eso no hay un punto en el mapa.'
    : 'Riot registra este evento sin ubicación. Puedes revisar cuándo ocurrió, pero no dónde.';
}
