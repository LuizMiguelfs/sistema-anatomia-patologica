import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('./api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
import api from './api';
import { arquivarSolicitacao, consultarLaudos, listarPendentesLiberacao, listarRevisoes, simularLiberacao } from './laudos';
const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };
describe('services/laudos', () => {
  beforeEach(() => vi.clearAllMocks());
  it('consulta revisão e liberação separadas do AGHU', async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    await listarRevisoes(); await listarPendentesLiberacao(); await consultarLaudos(7);
    expect(mockApi.get).toHaveBeenNthCalledWith(1, '/api/laudos/revisoes');
    expect(mockApi.get).toHaveBeenNthCalledWith(2, '/api/laudos/pendentes-liberacao');
    expect(mockApi.get).toHaveBeenNthCalledWith(3, '/api/laudos/solicitacoes/7');
  });
  it('não faz PUT/POST ao AGHU', async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await simularLiberacao(7); await arquivarSolicitacao(7);
    expect(mockApi.post).toHaveBeenNthCalledWith(1, '/api/laudos/solicitacoes/7/liberacao-simulada');
    expect(mockApi.post).toHaveBeenNthCalledWith(2, '/api/laudos/solicitacoes/7/arquivar');
  });
});
