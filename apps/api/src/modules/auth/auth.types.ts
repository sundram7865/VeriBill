export type Role = 'admin' | 'reviewer';

/** Token scopes: normal users get "user"; the MCP server gets a read-only token. */
export type TokenScope = 'user' | 'mcp:read';

export interface AuthContext {
  userId: string;
  tenantId: string;
  role: Role;
  scope: TokenScope;
}
