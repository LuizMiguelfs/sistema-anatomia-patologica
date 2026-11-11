"""Formulários das fases do setor e matriz de perfis do MVP.

PROVISÓRIO: os campos abaixo são um ponto de partida para a demonstração. O conteúdo real
de cada formulário (e quais campos são obrigatórios) será definido com o setor; trocar só
este arquivo basta, porque backend e frontend leem as definições daqui (RNF011).

Matriz de perfis (decidida com a equipe):
* Recepção marca o material como retirado (fora deste arquivo).
* Macroscopia: Residentes.
* Congelação, Microscopia e Revisão de Lâmina: Residentes preenchem; o patologista
  (Preceptoria) revisa, valida e conclui.
* Processamento Técnico e IHQ: Laboratório / Técnicos.
* Chefia e os demais perfis apenas visualizam.
"""
from typing import Any, Dict, List

PERFIL_RECEPCAO = "RECEPCAO"
PERFIL_LABORATORIO = "LABORATORIO"
PERFIL_RESIDENTE = "RESIDENTE"
PERFIL_PRECEPTORIA = "PRECEPTORIA"

#: Dias em que uma fase concluída continua na fila para edição.
DIAS_EDICAO_APOS_CONCLUSAO = 6

_OBSERVACOES: Dict[str, Any] = {
    "nome": "observacoes", "rotulo": "Observações", "tipo": "texto_longo", "obrigatorio": False,
}

#: Fases com fila própria, na ordem do menu. `salvar`/`concluir` = perfis com permissão.
FASES: List[Dict[str, Any]] = [
    {
        "etapa": "MACROSCOPIA", "rotulo": "Macroscopia", "grupo": "PRE_ANALITICA",
        "salvar": [PERFIL_RESIDENTE], "concluir": [PERFIL_RESIDENTE],
        "campos": [
            {"nome": "descricao_macroscopica", "rotulo": "Descrição macroscópica", "tipo": "texto_longo", "obrigatorio": True},
            {"nome": "qtd_fragmentos", "rotulo": "Nº de fragmentos", "tipo": "numero", "obrigatorio": True},
            {"nome": "qtd_cassetes", "rotulo": "Nº de cassetes", "tipo": "numero", "obrigatorio": True},
            {"nome": "laudo_macroscopico", "rotulo": "Laudo macroscópico", "tipo": "texto_longo", "obrigatorio": True},
            _OBSERVACOES,
        ],
    },
    {
        "etapa": "CONGELACAO", "rotulo": "Congelação", "grupo": "PRE_ANALITICA",
        "salvar": [PERFIL_RESIDENTE, PERFIL_PRECEPTORIA], "concluir": [PERFIL_PRECEPTORIA],
        "campos": [
            {"nome": "analise_preliminar", "rotulo": "Análise macroscópica preliminar", "tipo": "texto_longo", "obrigatorio": True},
            {"nome": "resultado", "rotulo": "Resultado da Congelação", "tipo": "texto_longo", "obrigatorio": True},
            {"nome": "bloco_avisado", "rotulo": "Bloco Cirúrgico avisado", "tipo": "sim_nao", "obrigatorio": True},
            _OBSERVACOES,
        ],
    },
    {
        "etapa": "PROCESSAMENTO", "rotulo": "Processamento Técnico", "grupo": "PRE_ANALITICA",
        "salvar": [PERFIL_LABORATORIO], "concluir": [PERFIL_LABORATORIO],
        "campos": [
            {"nome": "inicio", "rotulo": "Início do processamento", "tipo": "opcao", "obrigatorio": True,
             "opcoes": ["Histotécnico", "Preparo manual"], "tipos_exame": ["HP"]},
            {"nome": "material_liquido", "rotulo": "Material líquido?", "tipo": "sim_nao", "obrigatorio": True,
             "tipos_exame": ["CG", "CCV"]},
            {"nome": "cell_block", "rotulo": "Tem fragmento (cell-block)?", "tipo": "sim_nao", "obrigatorio": False,
             "tipos_exame": ["CG", "CCV"]},
            {"nome": "qtd_blocos", "rotulo": "Nº de blocos", "tipo": "numero", "obrigatorio": True, "tipos_exame": ["HP"]},
            {"nome": "qtd_laminas", "rotulo": "Nº de lâminas", "tipo": "numero", "obrigatorio": True},
            {"nome": "coloracao", "rotulo": "Coloração", "tipo": "texto", "obrigatorio": False},
            _OBSERVACOES,
        ],
    },
    {
        "etapa": "IHQ", "rotulo": "IHQ", "grupo": "PRE_ANALITICA",
        "salvar": [PERFIL_LABORATORIO], "concluir": [PERFIL_LABORATORIO],
        "campos": [
            {"nome": "marcadores", "rotulo": "Marcadores (anticorpos)", "tipo": "texto", "obrigatorio": True},
            {"nome": "qtd_laminas", "rotulo": "Nº de lâminas", "tipo": "numero", "obrigatorio": True},
            {"nome": "resultado", "rotulo": "Resultado / laudo da IHQ", "tipo": "texto_longo", "obrigatorio": True},
            _OBSERVACOES,
        ],
    },
    {
        "etapa": "MICROSCOPIA", "rotulo": "Microscopia", "grupo": "ANALITICA",
        "salvar": [PERFIL_RESIDENTE, PERFIL_PRECEPTORIA], "concluir": [PERFIL_PRECEPTORIA],
        "campos": [
            {"nome": "pre_laudo", "rotulo": "Pré-laudo (Residente)", "tipo": "texto_longo", "obrigatorio": True},
            {"nome": "diagnostico", "rotulo": "Diagnóstico validado (Patologista)", "tipo": "texto_longo", "obrigatorio": True,
             "perfis": [PERFIL_PRECEPTORIA]},
            _OBSERVACOES,
        ],
    },
    {
        "etapa": "REVISAO", "rotulo": "Revisão de Lâmina", "grupo": "ANALITICA",
        "salvar": [PERFIL_RESIDENTE, PERFIL_PRECEPTORIA], "concluir": [PERFIL_PRECEPTORIA],
        "campos": [
            {"nome": "qtd_laminas", "rotulo": "Nº de lâminas revistas", "tipo": "numero", "obrigatorio": True},
            {"nome": "pre_laudo", "rotulo": "Pré-laudo (Residente)", "tipo": "texto_longo", "obrigatorio": True},
            {"nome": "diagnostico", "rotulo": "Diagnóstico validado (Patologista)", "tipo": "texto_longo", "obrigatorio": True,
             "perfis": [PERFIL_PRECEPTORIA]},
            _OBSERVACOES,
        ],
    },
]

FASES_POR_ETAPA: Dict[str, Dict[str, Any]] = {f["etapa"]: f for f in FASES}


def campos_da_fase(etapa: str, tipo_exame: str) -> List[Dict[str, Any]]:
    """Campos do formulário da fase que se aplicam ao tipo de exame da solicitação."""
    fase = FASES_POR_ETAPA[etapa]
    return [c for c in fase["campos"] if tipo_exame in c.get("tipos_exame", [tipo_exame])]
