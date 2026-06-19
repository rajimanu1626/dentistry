import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/lib/api';
import { changePassword, createInvite, listInvites, revokeInvite } from '@/lib/auth-api';

vi.mock('@/lib/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('auth-api helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates invite via /auth/invites', async () => {
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      invite_id: 'id-1',
      email: 'dentist@example.com',
      role: 'dentist',
      invite_token: 'token-1',
      expires_at: '2026-01-01T00:00:00Z',
    });

    const result = await createInvite({
      email: 'dentist@example.com',
      role: 'dentist',
    });
    expect(apiClient.post).toHaveBeenCalledWith('/auth/invites', {
      email: 'dentist@example.com',
      role: 'dentist',
    });
    expect(result.invite_token).toBe('token-1');
  });

  it('lists and revokes invites', async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    await listInvites();
    expect(apiClient.get).toHaveBeenCalledWith('/auth/invites');

    (apiClient.delete as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    await revokeInvite('invite-123');
    expect(apiClient.delete).toHaveBeenCalledWith('/auth/invites/invite-123');
  });

  it('posts change password payload', async () => {
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    await changePassword('oldpass123!', 'newpass123!');
    expect(apiClient.post).toHaveBeenCalledWith('/auth/change-password', {
      current_password: 'oldpass123!',
      new_password: 'newpass123!',
    });
  });
});
