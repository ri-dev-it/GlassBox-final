import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

  it('shows the applicant dashboard and application link in the top navigation', () => {
    render(<MemoryRouter><MainLayout /></MemoryRouter>);
    const navigation = screen.getByRole('navigation', { name: 'Main navigation' });
    expect(navigation.querySelector('a[href="/"]')?.textContent).toContain('Dashboard');
    expect(navigation.querySelector('a[href="/apply"]')?.textContent).toContain('New Application');
  });

  it('keeps applicant shortcuts reachable from the expandable mobile menu', async () => {
    render(<MemoryRouter><MainLayout /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    const navigation = screen.getByRole('navigation', { name: 'Mobile main navigation' });
    expect(navigation.querySelector('a[href="/status"]')?.textContent).toContain('Application Status');
    fireEvent.click(within(navigation).getByRole('button', { name: 'More' }));
    expect(within(navigation).getByRole('link', { name: 'AI Insights' })).not.toBeNull();
    expect(within(navigation).getByRole('link', { name: 'Application History' })).not.toBeNull();
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
