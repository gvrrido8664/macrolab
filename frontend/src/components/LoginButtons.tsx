'use client';
import { signIn } from 'next-auth/react';
export default function LoginButtons({ github, local }: { github: boolean; local: boolean }) {
  return <div className="flex flex-wrap gap-3">{github && <button className="button" onClick={() => void signIn('github', { callbackUrl: '/dashboard' })}>Entrar con GitHub</button>}{local && <button className="button" onClick={() => void signIn('riot-mock', { summonerName: 'Desarrollo', callbackUrl: '/dashboard' })}>Cuenta local de desarrollo</button>}{!github && !local && <p className="muted">El acceso a cuentas estará disponible cuando se configure el proveedor. Puedes recorrer la demo ahora.</p>}</div>;
}
