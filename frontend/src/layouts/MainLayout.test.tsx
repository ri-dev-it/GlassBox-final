import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MainLayout from './MainLayout';

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { full_name: 'Test User', role: 'client' }, logout: vi.fn() }),
}));

vi.mock('../hooks/useTheme', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}));

vi.mock('../services/api', () => ({
  notificationApi: { list: vi.fn().mockResolvedValue([]), markRead: vi.fn() },
}));

describe('MainLayout dashboard chrome', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows the applicant dashboard at the top of the sidebar navigation', () => {
    render(<MemoryRouter><MainLayout /></MemoryRouter>);
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });
    const applicationLink = screen.getAllByRole('link', { name: 'New Application' })[0];
    expect(dashboardLink.compareDocumentPosition(applicationLink) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('opens and closes notifications by toggle and outside click', async () => {
    render(<MemoryRouter><MainLayout /></MemoryRouter>);
    const notificationButton = screen.getByRole('button', { name: 'Notifications' });

    fireEvent.click(notificationButton);
    await waitFor(() => expect(notificationButton.getAttribute('aria-expanded')).toBe('true'));
    expect((await screen.findByRole('dialog', { name: 'Notifications' })).textContent).toContain('No new notifications.');

    fireEvent.click(notificationButton);
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Notifications' })).toBeNull());

    fireEvent.click(notificationButton);
    await waitFor(() => expect(notificationButton.getAttribute('aria-expanded')).toBe('true'));
    expect(await screen.findByRole('dialog', { name: 'Notifications' })).not.toBeNull();
    fireEvent.pointerDown(document.body);
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Notifications' })).toBeNull());
  });
});
