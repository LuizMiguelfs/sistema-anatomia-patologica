/** Matriz inicial de consulta, edição, revisão e liberação conforme perfil local ativo. */
import api from './api';
export interface PermissoesSAP {
  matriz: {
    versao: string;
    homologada_pelo_hc: boolean;
    consulta: string[];
    retirada_credencial: string[];
    desfazer_retirada_credencial: string[];
    liberar_laudo: string[];
    arquivar: string[];
    configuracoes: string[];
  };
  usuario: {
    perfil: string;
    pode_consultar: boolean;
    pode_confirmar_retirada: boolean;
    pode_liberar_laudo: boolean;
    pode_arquivar: boolean;
    fases: Record<string, { pode_consultar: boolean; pode_editar: boolean; pode_concluir: boolean }>;
  };
  simulacao_disponivel: boolean;
}
export async function consultarPermissoes(): Promise<PermissoesSAP> {
  return (await api.get<PermissoesSAP>('/api/permissoes')).data;
}
