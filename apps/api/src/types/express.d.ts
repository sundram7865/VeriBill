import type { AuthContext } from '../modules/auth/auth.types';

declare global {
  namespace Express {
    interface Request {
      /** Set by the auth middleware on authenticated routes. */
      auth?: AuthContext;
    }
  }
}

export {};
