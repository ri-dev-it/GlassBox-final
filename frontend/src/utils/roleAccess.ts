import type { Role } from '../types';

export function dashboardPath(role: Role): string {
  if (role === 'admin') return '/admin';
  if (role === 'loan_officer') return '/analytics';
  return '/';
}