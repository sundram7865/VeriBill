import type { RequestHandler } from 'express';
import { forbidden, unauthorized } from '../lib/errors';
import { verifyAccessToken } from '../modules/auth/accessToken';
import type { AuthContext, Role } from '../modules/auth/auth.types';

/** Requires a valid Bearer access token and puts the auth context on req.auth. */
export function authenticate(secret: string): RequestHandler {
  return (req, _res, next) => {
    const header = req.header('authorization') ?? '';
    const token = header.startsWith('Bearer ') ? header.slice(7).trim() : '';
    if (!token) throw unauthorized();
    const auth = verifyAccessToken(token, secret);
    // Read-only tokens (the MCP server) can never change anything.
    if (auth.scope === 'mcp:read' && req.method !== 'GET') {
      throw forbidden('This token is read-only');
    }
    req.auth = auth;
    next();
  };
}

export function requireRole(...roles: Role[]): RequestHandler {
  return (req, _res, next) => {
    if (!req.auth) throw unauthorized();
    if (!roles.includes(req.auth.role)) throw forbidden(`Requires role: ${roles.join(' or ')}`);
    next();
  };
}

/** For handlers behind authenticate(): the auth context, guaranteed present. */
export function authOf(req: { auth?: AuthContext }): AuthContext {
  if (!req.auth) throw unauthorized();
  return req.auth;
}
