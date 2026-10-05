import type { NextAuthOptions } from 'next-auth';
import GitHubProvider from 'next-auth/providers/github';
import CredentialsProvider from 'next-auth/providers/credentials';
import { createHash } from 'node:crypto';
import { sessionIdentity } from './identity';

export const authOptions: NextAuthOptions = {
  providers: [
    ...(process.env.GITHUB_ID && process.env.GITHUB_SECRET ? [GitHubProvider({ clientId: process.env.GITHUB_ID, clientSecret: process.env.GITHUB_SECRET })] : []),
    ...(process.env.NODE_ENV !== 'production' && process.env.ALLOW_MOCK_AUTH === 'true' ? [CredentialsProvider({
      id: 'riot-mock', name: 'Cuenta local de desarrollo', credentials: { summonerName: { label: 'Nombre local', type: 'text' } },
      async authorize(credentials) {
        const name = credentials?.summonerName?.trim();
        if (!name || name.length > 32) return null;
        return { id: createHash('sha256').update(name).digest('hex'), name };
      },
    })] : []),
  ],
  session: { strategy: 'jwt' },
  secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  callbacks: {
    async jwt({ token, account }) {
      if (account) token.sub = `${account.provider}:${account.providerAccountId}`;
      return token;
    },
    async session({ session, token }) {
      const id = sessionIdentity(token.sub, process.env.NODE_ENV === 'production');
      if (session.user) session.user.id = id ?? '';
      return session;
    },
  },
};
