import { describe, expect, it, vi } from 'vitest';
vi.mock('./api', () => ({ default: { get: vi.fn() } }));
import api from './api';
import { consultarPermissoes } from './permissoes';
describe('services/permissoes', () => {
  it('consulta a matriz no servidor em vez de inventar permissões localmente', async () => {
    const get = api.get as ReturnType<typeof vi.fn>;
    get.mockResolvedValue({ data: { usuario: { perfil: 'CHEFIA' }, matriz: {} } });
    expect((await consultarPermissoes()).usuario.perfil).toBe('CHEFIA');
    expect(get).toHaveBeenCalledWith('/api/permissoes');
  });
});
