'use client';

import { signOut } from 'next-auth/react';

export default function SignOutButton() {
  return (
    <button
      type="button"
      onClick={() => signOut({ callbackUrl: '/' })}
      className="text-sm font-medium hover:text-white transition-colors border border-slate-700 px-4 py-2 rounded-lg bg-slate-800"
    >
      Cerrar sesión
    </button>
  );
}
