export function sessionIdentity(subject: unknown, production: boolean): string | null {
  if (typeof subject !== 'string') return null;
  return /^github:[^:]+$/.test(subject) || (!production && /^riot-mock:[^:]+$/.test(subject)) ? subject : null;
}
