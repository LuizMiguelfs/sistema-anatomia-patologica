import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}));

import api from './api';
import {
  PERFIS_SAP, alterarPerfil, alterarSituacao, buscarNoAD, incluirUsuario, listarUsuarios,
  mensagemDeErro, normalizarLogin, rotuloPerfil,
} from './usuarios';

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn>; patch: ReturnType<typeof vi.fn>;
};

describe('services/usuarios', () => {
  beforeEach(() => vi.clearAllMocks());

  it('tem exatamente os cinco perfis do SAP', () => {
    expect(PERFIS_SAP.map((p) => p.valor)).toEqual(['RECEPCAO', 'LABORATORIO', 'RESIDENTE', 'PRECEPTORIA', 'CHEFIA']);
    expect(rotuloPerfil('CHEFIA')).toContain('Chefia');
    expect(rotuloPerfil('DESCONHECIDO')).toBe('DESCONHECIDO');
  });

  it('normaliza o login como o backend', () => {
    expect(normalizarLogin('  Joao.Silva ')).toBe('joao.silva');
  });

  it('lista os usuários', async () => {
    mockApi.get.mockResolvedValue({ data: [{ username: 'admin' }] });
    await expect(listarUsuarios()).resolves.toEqual([{ username: 'admin' }]);
    expect(mockApi.get).toHaveBeenCalledWith('/api/admin/usuarios');
  });

  it('busca no AD com o login normalizado e codificado', async () => {
    mockApi.get.mockResolvedValue({ data: { exists: true } });
    await buscarNoAD(' Joao Silva ');
    expect(mockApi.get).toHaveBeenCalledWith('/api/admin/ad-user-search/joao%20silva');
  });

  it('inclui só com login e perfil (o nome vem do AD no backend)', async () => {
    mockApi.post.mockResolvedValue({ data: { username: 'joao.silva' } });
    await incluirUsuario(' Joao.Silva', 'RECEPCAO');
    expect(mockApi.post).toHaveBeenCalledWith('/api/admin/usuarios', { username: 'joao.silva', perfil: 'RECEPCAO' });
  });

  it('altera perfil e situação pelas rotas próprias, sem exclusão', async () => {
    mockApi.patch.mockResolvedValue({ data: {} });
    await alterarPerfil('joao.silva', 'LABORATORIO');
    await alterarSituacao('joao.silva', false);
    expect(mockApi.patch).toHaveBeenNthCalledWith(1, '/api/admin/usuarios/joao.silva/perfil', { perfil: 'LABORATORIO' });
    expect(mockApi.patch).toHaveBeenNthCalledWith(2, '/api/admin/usuarios/joao.silva/situacao', { ativo: false });
    expect(Object.keys(mockApi)).not.toContain('delete');
  });

  it('usa o detail da API ou a mensagem padrão', () => {
    expect(mensagemDeErro({ response: { data: { detail: 'Usuário já cadastrado no SAP.' } } }, 'x')).toBe('Usuário já cadastrado no SAP.');
    expect(mensagemDeErro(new Error('stack técnica'), 'Falha ao salvar.')).toBe('Falha ao salvar.');
  });
});
