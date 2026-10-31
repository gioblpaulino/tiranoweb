# =============================================================================
# ARQUIVO: tiranocad_core/gerenciador_perfis.py
# RESPONSABILIDADE: Carregar, validar e fornecer parâmetros técnicos dos perfis
# JSON. Proíbe o uso de "Magic Numbers" e avisa instantaneamente se faltar algo.
# =============================================================================

import json
import os
from typing import Any, Dict


class ErroPerfilConfiguracao(Exception):
    """Exceção disparada quando uma chave obrigatória não existe no Perfil JSON."""
    pass


class GerenciadorPerfis:
    """
    Gerencia o carregamento e acesso seguro aos parâmetros de engenharia do CAD.
    Permite mesclar configurações do JSON base com overrides vindos da UI.
    """

    def __init__(self, pasta_perfis: str):
        self.pasta_perfis = pasta_perfis
        self.dados_perfil: Dict[str, Any] = {}
        self.id_perfil_ativo: str = ""

    def carregar_perfil(self, nome_arquivo_ou_id: str, overrides_ui: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Carrega o arquivo JSON do perfil e aplica eventuais customizações feitas
        pelo usuário na interface gráfica (overrides_ui).
        """
        if not nome_arquivo_ou_id.endswith(".json"):
            nome_arquivo = f"{nome_arquivo_ou_id}.json"
        else:
            nome_arquivo = nome_arquivo_ou_id

        caminho_completo = os.path.join(self.pasta_perfis, nome_arquivo)

        if not os.path.exists(caminho_completo):
            raise ErroPerfilConfiguracao(
                f"Arquivo de perfil não encontrado: '{caminho_completo}'. "
                f"Verifique a pasta de catálogos."
            )

        try:
            with open(caminho_completo, mode="r", encoding="utf-8") as f:
                self.dados_perfil = json.load(f)
        except json.JSONDecodeError as e:
            raise ErroPerfilConfiguracao(f"Erro de sintaxe no JSON do perfil '{nome_arquivo}': {e}")

        self.id_perfil_ativo = self.dados_perfil.get("id_perfil", nome_arquivo_ou_id)

        # Se a interface do usuário enviou alterações pontuais, mescla de forma segura
        if overrides_ui:
            self._mesclar_overrides(self.dados_perfil, overrides_ui)

        self._validar_estrutura_minima()
        return self.dados_perfil

    def obter(self, caminho_chave: str) -> Any:
        """
        Busca um valor no perfil usando notação de ponto.
        Exemplo: perfil.obter("geometria_caixaria.largura_sarrafo") -> 70.0
        Se a chave não existir, dispara um erro imediato explicando onde está a falha!
        """
        partes = caminho_chave.split(".")
        cursor: Any = self.dados_perfil

        for p in partes:
            if isinstance(cursor, dict) and p in cursor:
                cursor = cursor[p]
            else:
                raise ErroPerfilConfiguracao(
                    f"🚨 [BUG DETECTADO] O construtor tentou ler o parâmetro '{caminho_chave}', "
                    f"mas a chave '{p}' não existe no perfil ativo ('{self.id_perfil_ativo}')."
                )
        return cursor

    def obter_nome_peca(self, categoria_industrial: str) -> str:
        """Retorna o nome comercial padronizado para a categoria industrial da peça."""
        return str(self.obter(f"nomenclatura.{categoria_industrial}"))

    def calcular_qtd_dobradicas(self, altura_porta_mm: float) -> int:
        """Determina a quantidade de dobradiças com base nas faixas de altura do perfil."""
        regras = self.obter("regras_dobradicas")
        for faixa in sorted(regras, key=lambda r: float(r["altura_max_mm"])):
            if altura_porta_mm <= float(faixa["altura_max_mm"]):
                return int(faixa["quantidade"])
        return int(regras[-1]["quantidade"])

    def _mesclar_overrides(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> None:
        """Mescla recursivamente dicionários vindos da UI sobre o perfil carregado."""
        for chave, valor in overrides.items():
            if isinstance(valor, dict) and chave in base and isinstance(base[chave], dict):
                self._mesclar_overrides(base[chave], valor)
            else:
                base[chave] = valor

    def _validar_estrutura_minima(self) -> None:
        """Garante que todas as seções vitais estão presentes antes de liberar o cálculo."""
        secoes_obrigatorias = [
            "materiais_padrao",
            "restricoes_chapa",
            "geometria_caixaria",
            "folgas_frentes",
            "regras_gaveta",
            "parametros_usinagem",
            "nomenclatura"
        ]
        for secao in secoes_obrigatorias:
            if secao not in self.dados_perfil:
                raise ErroPerfilConfiguracao(
                    f"O perfil '{self.id_perfil_ativo}' está incompleto: falta a seção '{secao}'."
                )