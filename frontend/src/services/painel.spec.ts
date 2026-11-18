import { describe, expect, it } from 'vitest';
import {
  ROTAS_DAS_FASES, ROTA_NAO_RETIRADAS, fasesDoGrupo, locaisAguardandoPatologista, locaisComUrgentes, rotaDaFase,
  type RetratoFilas,
} from './painel';

function fase(etapa: string, rotulo: string, grupo: string, pendentes = 0, urgentes = 0, aguardando: number | null = null) {
  return { etapa, rotulo, grupo, pendentes, urgentes, aguardando_patologista: aguardando };
}

const FILAS: RetratoFilas = {
  nao_retiradas: 4,
  nao_retiradas_urgentes: 1,
  urgentes: 3,
  aguardando_patologista: 3,
  fases: [
    fase('MACROSCOPIA', 'Macroscopia', 'PRE_ANALITICA', 5),
    fase('CONGELACAO', 'Congelação', 'PRE_ANALITICA', 2, 2, 1),
    fase('PROCESSAMENTO', 'Processamento Técnico', 'PRE_ANALITICA', 3),
    fase('IHQ', 'IHQ', 'PRE_ANALITICA'),
    fase('MICROSCOPIA', 'Microscopia', 'ANALITICA', 6, 0, 2),
    fase('REVISAO', 'Revisão de Lâmina', 'ANALITICA', 1, 0, 0),
  ],
};

describe('services/painel · retrato das filas', () => {
  it('cada fase leva à aba do menu', () => {
    expect(rotaDaFase('MACROSCOPIA')).toBe('/fases/macroscopia');
    expect(rotaDaFase('REVISAO')).toBe('/fases/revisao-de-lamina');
    expect(rotaDaFase('DESCONHECIDA')).toBe('/');
    expect(Object.keys(ROTAS_DAS_FASES)).toEqual(FILAS.fases.map((f) => f.etapa));
  });

  it('separa as fases pelos grupos do menu, na ordem', () => {
    expect(fasesDoGrupo(FILAS, 'PRE_ANALITICA').map((f) => f.etapa)).toEqual(['MACROSCOPIA', 'CONGELACAO', 'PROCESSAMENTO', 'IHQ']);
    expect(fasesDoGrupo(FILAS, 'ANALITICA').map((f) => f.etapa)).toEqual(['MICROSCOPIA', 'REVISAO']);
  });

  it('mostra onde estão as urgentes, cada uma com sua aba', () => {
    const locais = locaisComUrgentes(FILAS);
    expect(locais).toEqual([
      { rotulo: 'Não retiradas', quantidade: 1, rota: ROTA_NAO_RETIRADAS },
      { rotulo: 'Congelação', quantidade: 2, rota: '/fases/congelacao' },
    ]);
    expect(locais.reduce((soma, l) => soma + l.quantidade, 0)).toBe(FILAS.urgentes);
  });

  it('mostra onde o patologista tem pré-laudo para validar', () => {
    expect(locaisAguardandoPatologista(FILAS)).toEqual([
      { rotulo: 'Congelação', quantidade: 1, rota: '/fases/congelacao' },
      { rotulo: 'Microscopia', quantidade: 2, rota: '/fases/microscopia' },
    ]);
  });

  it('sem nada pendente, não há locais a mostrar', () => {
    const vazio: RetratoFilas = { ...FILAS, nao_retiradas_urgentes: 0, urgentes: 0, aguardando_patologista: 0,
      fases: FILAS.fases.map((f) => ({ ...f, urgentes: 0, aguardando_patologista: f.aguardando_patologista === null ? null : 0 })) };
    expect(locaisComUrgentes(vazio)).toEqual([]);
    expect(locaisAguardandoPatologista(vazio)).toEqual([]);
  });
});
