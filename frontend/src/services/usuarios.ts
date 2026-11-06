/**
 * Serviço da gestão de usuários do SAP (RF028 / UC026).
 *
 * Fala com /api/admin/usuarios (restrito à Chefia no backend) e com a busca no AD.
 * Não existe exclusão: o acesso é inativado e reativado.
 */
import api from './api';
import type { SapRole } from '../stores/auth';

/** Usuário autorizado no SAP, como devolvido pela API. */
export interface UsuarioSap {
  username: string;
  nome: string | null;
  perfil: SapRole;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string | null;
}

/** Resultado da busca de um login no Active Directory. */
export interface UsuarioAD {
  exists: boolean;
  username: string;
  displayName: string;
  email: string;
  department: string;
}

/** Perfis do SAP com a descrição usada na tela (00-validacao-negocio, seção 6). */
export const PERFIS_SAP: ReadonlyArray<{ valor: SapRole; rotulo: string; descricao: string }> = [
  { valor: 'RECEPCAO', rotulo: 'Recepção', descricao: 'Abre o caso a partir do AGHU, recebe e confere a amostra e cadastra exames externos.' },
  { valor: 'LABORATORIO', rotulo: 'Laboratório / Técnicos', descricao: 'Registra macroscopia, Congelação, processamento técnico, pedidos adicionais, IHQ e envios externos.' },
  { valor: 'RESIDENTE', rotulo: 'Residentes', descricao: 'Preenche o pré-laudo na Microscopia e envia à Preceptoria.' },
  { valor: 'PRECEPTORIA', rotulo: 'Validação / Preceptoria', descricao: 'Revisa o pré-laudo, valida o diagnóstico, laudo e arquivamento.' },
  { valor: 'CHEFIA', rotulo: 'Técnico Administrativo (Chefia do UACAP)', descricao: 'Acompanha painéis e indicadores e gerencia os usuários e perfis do SAP.' },
];

/** Rótulo legível de um perfil; devolve o próprio valor se for desconhecido. */
export function rotuloPerfil(perfil: string): string {
  return PERFIS_SAP.find((p) => p.valor === perfil)?.rotulo ?? perfil;
}

/** Normaliza o login de rede como o backend: sem espaços nas pontas e em minúsculas. */
export function normalizarLogin(login: string): string {
  return login.trim().toLowerCase();
}

/** Lista os usuários autorizados (ativos e inativos). */
export async function listarUsuarios(): Promise<UsuarioSap[]> {
  const { data } = await api.get<UsuarioSap[]>('/api/admin/usuarios');
  return data;
}

/** Consulta um login no AD antes da inclusão. */
export async function buscarNoAD(login: string): Promise<UsuarioAD> {
  const { data } = await api.get<UsuarioAD>(`/api/admin/ad-user-search/${encodeURIComponent(normalizarLogin(login))}`);
  return data;
}

/** Autoriza um login do AD com o perfil escolhido. O nome é obtido do AD pelo backend. */
export async function incluirUsuario(login: string, perfil: SapRole): Promise<UsuarioSap> {
  const { data } = await api.post<UsuarioSap>('/api/admin/usuarios', { username: normalizarLogin(login), perfil });
  return data;
}

/** Troca o perfil de um usuário (o backend recusa o próprio usuário). */
export async function alterarPerfil(login: string, perfil: SapRole): Promise<UsuarioSap> {
  const { data } = await api.patch<UsuarioSap>(`/api/admin/usuarios/${encodeURIComponent(login)}/perfil`, { perfil });
  return data;
}

/** Inativa (ativo = false) ou reativa (ativo = true) o acesso de um usuário. */
export async function alterarSituacao(login: string, ativo: boolean): Promise<UsuarioSap> {
  const { data } = await api.patch<UsuarioSap>(`/api/admin/usuarios/${encodeURIComponent(login)}/situacao`, { ativo });
  return data;
}

/**
 * Extrai a mensagem de erro da API (`detail`) ou usa a mensagem padrão.
 * Nunca mostra detalhes técnicos da exceção ao usuário.
 */
export function mensagemDeErro(erro: unknown, padrao: string): string {
  const detail = (erro as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' && detail ? detail : padrao;
}
