import { describe, expect, it } from 'vitest';
import { dashboardPath } from '../../frontend/src/utils/roleAccess';

describe('role access', () => {
  it('routes each persisted role to its dashboard', () => {
    expect(dashboardPath('applicant')).toBe('/');
    expect(dashboardPath('client')).toBe('/');
    expect(dashboardPath('loan_officer')).toBe('/analytics');
    expect(dashboardPath('admin')).toBe('/admin');
  });
});
