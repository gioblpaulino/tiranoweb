# =============================================================================
# ARQUIVO: tiranocad_core/regras/validador_engenharia.py
# RESPONSABILIDADE: Blindar o sistema contra combinações fisicamente impossíveis
# ou proibidas pelas regras de marcenaria, lendo 100% dos limites do Perfil JSON.
# =============================================================================

from typing import Any, Dict
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD
from tiranocad_core.modelos.no_espacial import NoEspacial


class ValidadorEngenharia:
    """
    Fiscal de chão de fábrica do TiranoCAD.
    Inspeciona cada operação antes da fabricação e bloqueia erros instantaneamente.
    """

    OPERACOES_PROIBIDAS_POR_FAMILIA = {
        "MODULO_AEREO": {
            "GAVETEIRO": "Módulos Aéreos não permitem Gaveteiros por segurança e ergonomia.",
            "GAVETEIRO_INTERNO": "Módulos Aéreos não permitem Gaveteiros Internos.",
            "SAPATEIRA": "Módulos Aéreos não permitem Sapateiras corrediças.",
            "PORTA_TEMPERO": "Módulos Aéreos não permitem Porta-Tempero extraível."
        }
    }

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def validar_dimensoes_modulo(
        self,
        familia: str,
        largura_x: float,
        altura_y: float,
        profundidade_z: float
    ) -> None:
        """Verifica se as medidas externas do módulo respeitam os limites da chapa e da família."""
        familia = familia.strip().upper()
        min_bancada_rodape = float(self.perfil.obter("limites_engenharia.medida_min_bancada_rodape_mm"))

        # Bancadas de Pedra (Marmoraria) e Rodapés (que já seccionam chapas automaticamente)
        # não sofrem bloqueio pelo comprimento de uma única chapa de MDF!
        if familia in ("MODULO_BANCADA_PEDRA", "MODULO_RODAPE"):
            if largura_x <= min_bancada_rodape or profundidade_z <= min_bancada_rodape:
                raise ErroGeometriaCAD(
                    f"🚨 As dimensões da bancada/rodapé devem ser maiores que {min_bancada_rodape:.0f}mm."
                )
            return

        max_comp = float(self.perfil.obter("restricoes_chapa.comprimento_max_mdf"))
        max_larg = float(self.perfil.obter("restricoes_chapa.largura_max_mdf"))
        refilo = float(self.perfil.obter("restricoes_chapa.refilo_seguranca"))
        prof_max_aereo = float(self.perfil.obter("limites_engenharia.profundidade_max_aereo_mm"))

        util_x = max_comp - (2.0 * refilo)
        util_y = max_larg - (2.0 * refilo)

        maior_cota = max(largura_x, altura_y, profundidade_z)
        menor_cota_plana = min(largura_x, profundidade_z)

        if maior_cota > util_x:
            raise ErroGeometriaCAD(
                f"🚨 [LIMITE DE CHAPA EXCEDIDO] A medida de {maior_cota:.0f}mm ultrapassa o "
                f"comprimento útil da chapa de MDF ({util_x:.0f}mm já descontando refilo de {refilo:.0f}mm)."
            )

        if menor_cota_plana > util_y:
            raise ErroGeometriaCAD(
                f"🚨 [LARGURA DE CHAPA EXCEDIDA] A medida de {menor_cota_plana:.0f}mm ultrapassa a "
                f"largura útil da chapa ({util_y:.0f}mm)."
            )

        if familia == "MODULO_AEREO" and profundidade_z > prof_max_aereo:
            raise ErroGeometriaCAD(
                f"🚨 [TRAVA DE SEGURANÇA] Um Módulo Aéreo com {profundidade_z:.0f}mm de profundidade "
                f"apresenta risco estrutural de alavanca na parede (máximo configurado: {prof_max_aereo:.0f}mm)."
            )

    def validar_operacao_no_vao(
        self,
        familia: str,
        vao_alvo: NoEspacial,
        operacao: Dict[str, Any]
    ) -> None:
        """
        Audita se a operação solicitada pode ser executada naquele Nó Espacial específico.
        """
        familia = familia.strip().upper()
        tipo_op = str(operacao.get("tipo", "")).strip().upper()

        # 1. Trava de Contexto da Família
        regras_familia = self.OPERACOES_PROIBIDAS_POR_FAMILIA.get(familia, {})
        if tipo_op in regras_familia:
            raise ErroGeometriaCAD(f"🚨 [REGRA DE FAMÍLIA] {regras_familia[tipo_op]}")

        # 2. Trava de Nó já Subdividido
        tipos_que_exigem_folha = (
            "DIVISORIA_VERTICAL", "DIVISORIA_HORIZONTAL",
            "GAVETEIRO", "GAVETEIRO_INTERNO", "SAPATEIRA", "PORTA_TEMPERO"
        )
        if not vao_alvo.eh_folha and tipo_op in tipos_que_exigem_folha:
            raise ErroGeometriaCAD(
                f"🚨 [CONFLITO ESPACIAL] O '{vao_alvo.nome_vao}' ({vao_alvo.id_vao}) já foi dividido "
                f"internamente ({vao_alvo.tipo_divisao}). Aplique o componente em um dos sub-vãos filhos!"
            )

        # 3. Trava de Colisão Frontal
        tem_portas_no_vao = hasattr(vao_alvo, "metadados_portas") and bool(getattr(vao_alvo, "metadados_portas"))

        if tipo_op in ("PORTAS_GIRO", "PORTAS_BASCULANTES", "PORTAS_CORRER"):
            if vao_alvo.ocupacao_interna in ("GAVETEIRO", "PORTA_TEMPERO"):
                raise ErroGeometriaCAD(
                    f"🚨 [COLISÃO DE FRENTES] O '{vao_alvo.nome_vao}' já está ocupado por "
                    f"'{vao_alvo.ocupacao_interna}'. Não é permitido fechar com Portas um vão "
                    f"que já possui frentes externas extraíveis!"
                )
            if tem_portas_no_vao:
                raise ErroGeometriaCAD(
                    f"🚨 [DUPLICIDADE] O '{vao_alvo.nome_vao}' já possui Portas instaladas."
                )

        # 4. Trava de Ocupação Interna
        if tipo_op in ("GAVETEIRO", "GAVETEIRO_INTERNO", "SAPATEIRA", "PORTA_TEMPERO"):
            if tem_portas_no_vao and tipo_op in ("GAVETEIRO", "PORTA_TEMPERO"):
                raise ErroGeometriaCAD(
                    f"🚨 [COLISÃO DE FRENTES] O '{vao_alvo.nome_vao}' já possui Portas externas. "
                    f"Para colocar gavetas atrás de portas, utilize 'Gavetas Internas' ou 'Sapateira'!"
                )
            if vao_alvo.ocupacao_interna is not None:
                raise ErroGeometriaCAD(
                    f"🚨 [VÃO OCUPADO] O '{vao_alvo.nome_vao}' já está ocupado por '{vao_alvo.ocupacao_interna}'."
                )

        # 5. Limites Físicos de Largura (100% vindos do Perfil JSON)
        if tipo_op == "PORTA_TEMPERO":
            larg_min_pt = float(self.perfil.obter("limites_engenharia.largura_min_porta_tempero_mm"))
            larg_max_pt = float(self.perfil.obter("limites_engenharia.largura_max_porta_tempero_mm"))
            if not (larg_min_pt <= vao_alvo.largura <= larg_max_pt):
                raise ErroGeometriaCAD(
                    f"🚨 [LARGURA INCOMPATÍVEL] O Porta-Tempero exige um vão livre entre {larg_min_pt:.0f}mm e {larg_max_pt:.0f}mm "
                    f"(o '{vao_alvo.nome_vao}' possui {vao_alvo.largura:.1f}mm). Divida o vão antes!"
                )

        if tipo_op in ("GAVETEIRO", "GAVETEIRO_INTERNO", "SAPATEIRA"):
            larg_min_gav = float(self.perfil.obter("limites_engenharia.largura_min_gaveta_mm"))
            larg_max_gav = float(self.perfil.obter("limites_engenharia.largura_max_gaveta_mm"))
            if vao_alvo.largura < larg_min_gav or vao_alvo.largura > larg_max_gav:
                raise ErroGeometriaCAD(
                    f"🚨 [LARGURA INVÁLIDA] O '{vao_alvo.nome_vao}' possui {vao_alvo.largura:.1f}mm. "
                    f"Componentes corrediços exigem vão livre entre {larg_min_gav:.0f}mm e {larg_max_gav:.0f}mm."
                )