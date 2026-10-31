# =============================================================================
# ARQUIVO: tiranocad_core/orquestradores/orquestrador_modulo.py
# RESPONSABILIDADE: Orquestrar a fabricação de Módulos Completos (Inferior,
# Aéreo, Torre), Painéis/Tamponamentos/Engrossados (MODULO_PAINEL) e Peças ou
# Subconjuntos Avulsos (MODULO_AVULSO), incluindo metadados de posição no Ambiente.
# =============================================================================

import uuid
from typing import Any, Dict, List, Optional
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import Peca
from tiranocad_core.modelos.no_espacial import NoEspacial
from tiranocad_core.regras.validador_engenharia import ValidadorEngenharia
from tiranocad_core.construtores.caixaria import ConstrutorCaixaria
from tiranocad_core.construtores.internos import ConstrutorInternos
from tiranocad_core.construtores.gavetas import ConstrutorGavetas
from tiranocad_core.construtores.frentes import ConstrutorFrentes
from tiranocad_core.construtores.porta_tempero import ConstrutorPortaTempero
from tiranocad_core.construtores.paineis import ConstrutorPaineis
from tiranocad_core.construtores.avulsos import ConstrutorAvulsos
from tiranocad_core.orquestradores.orquestrador_usinagens import OrquestradorUsinagens


class OrquestradorModulo:
    """
    Maestro central do TiranoCAD em Python.
    Unifica Módulos de Caixaria, Painéis Compostos e Componentes Avulsos.
    """

    def __init__(self, pasta_perfis: str):
        self.gerenciador_perfis = GerenciadorPerfis(pasta_perfis)

    @staticmethod
    def _resolver_vao_alvo(vao_raiz: NoEspacial, op: Dict[str, Any]) -> NoEspacial:
        id_vao = op.get("id_vao")
        if id_vao:
            achado = vao_raiz.buscar_vao_por_id(str(id_vao).strip())
            if achado:
                return achado

        semantica = str(op.get("alvo_semantica", "RAIZ")).strip().upper()
        if semantica in ("FILHO_ESQUERDO", "FILHO_INFERIOR") and len(vao_raiz.filhos) >= 1:
            return vao_raiz.filhos[0]
        elif semantica == "FILHO_DIREITO" and len(vao_raiz.filhos) >= 2:
            return vao_raiz.filhos[1]
        elif semantica == "FILHO_CENTRAL" and len(vao_raiz.filhos) >= 2:
            return vao_raiz.filhos[1].filhos[0] if len(vao_raiz.filhos[1].filhos) >= 1 else vao_raiz.filhos[1]
        elif semantica == "FILHO_SUPERIOR" and len(vao_raiz.filhos) >= 2:
            return vao_raiz.filhos[1].filhos[1] if len(vao_raiz.filhos[1].filhos) >= 2 else vao_raiz.filhos[1]

        return vao_raiz

    def fabricar_modulo(
        self,
        id_modulo: str = "001",
        nome_projeto: str = "PROJETO_WEB_CAD",
        familia: str = "MODULO_INFERIOR",
        largura_x: float = 800.0,
        altura_y: float = 700.0,
        profundidade_z: float = 550.0,
        com_fundo: bool = True,
        id_perfil: str = "padrao_convencional_15mm",
        overrides_perfil: Optional[Dict[str, Any]] = None,
        operacoes_internas: Optional[List[Dict[str, Any]]] = None,
        opcoes_especiais: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Constrói qualquer família do ecossistema e retorna o JSON industrial validado."""
        familia = familia.strip().upper()
        opcoes_esp = opcoes_especiais or {}

        self.gerenciador_perfis.carregar_perfil(id_perfil, overrides_ui=overrides_perfil)
        validador = ValidadorEngenharia(self.gerenciador_perfis)
        validador.validar_dimensoes_modulo(familia, largura_x, altura_y, profundidade_z)

        mat_caixa = str(self.gerenciador_perfis.obter("materiais_padrao.material_caixaria"))
        mat_frentes = str(self.gerenciador_perfis.obter("materiais_padrao.material_frentes"))
        esp_caixa = float(self.gerenciador_perfis.obter("materiais_padrao.espessura_estrutural_mm"))

        # =====================================================================
        # ROTA ESPECIAL 1: CONSTRUTOR DE PAINÉIS, TAMPONAMENTOS E ENGROSSADOS
        # =====================================================================
        if familia == "MODULO_PAINEL":
            c_paineis = ConstrutorPaineis(self.gerenciador_perfis)
            modo_esp = str(opcoes_esp.get("modo_espessura", "SIMPLES")).upper()
            orientacao = str(opcoes_esp.get("orientacao_espacial", "VERTICAL_FRONTAL")).upper()
            nome_p = str(opcoes_esp.get("nome_personalizado", f"Painel {modo_esp.title()}"))

            # Se for horizontal (Tampo/Bancada), usa Largura x Profundidade; senão usa Largura x Altura
            cota_1 = largura_x
            cota_2 = profundidade_z if orientacao == "HORIZONTAL" else altura_y

            pecas_painel = c_paineis.construir_painel(
                id_modulo=id_modulo,
                nome_painel=nome_p,
                largura_x=cota_1,
                altura_y=cota_2,
                orientacao_espacial=orientacao,
                modo_espessura=modo_esp,
                espessura_chapa_base=esp_caixa,
                material=mat_frentes
            )
            return self._empacotar_payload(
                id_modulo, nome_projeto, familia, largura_x, altura_y, profundidade_z,
                mat_caixa, mat_frentes, [], None, [], pecas_painel,
                f"🪵 Construtor de Painéis: '{nome_p}' ({modo_esp}) fabricado com {len(pecas_painel)} peça(s) de corte."
            )

        # =====================================================================
        # ROTA ESPECIAL 2: CONSTRUTOR DE PEÇAS E SUBCONJUNTOS AVULSOS
        # =====================================================================
        if familia == "MODULO_AVULSO":
            c_avulsos = ConstrutorAvulsos(self.gerenciador_perfis)
            subtipo = str(opcoes_esp.get("subtipo_avulso", "GAVETA_COMPLETA")).upper()
            qtd_avulso = int(opcoes_esp.get("quantidade_avulso", 1))

            pecas_avulsas = c_avulsos.construir_item_avulso(
                id_modulo=id_modulo,
                subtipo_avulso=subtipo,
                largura_x=largura_x,
                altura_y=altura_y,
                profundidade_z=profundidade_z,
                quantidade=qtd_avulso
            )
            return self._empacotar_payload(
                id_modulo, nome_projeto, familia, largura_x, altura_y, profundidade_z,
                mat_caixa, mat_frentes, [], None, [], pecas_avulsas,
                f"🔩 Construtor Avulso: '{subtipo}' fabricado com {len(pecas_avulsas)} peça(s)."
            )

        # =====================================================================
        # ROTA PADRÃO: MÓDULOS DE CAIXARIA (INFERIOR, AÉREO, TORRE)
        # =====================================================================
        c_caixaria = ConstrutorCaixaria(self.gerenciador_perfis)
        c_internos = ConstrutorInternos(self.gerenciador_perfis)
        c_gavetas = ConstrutorGavetas(self.gerenciador_perfis)
        c_frentes = ConstrutorFrentes(self.gerenciador_perfis)
        c_tempero = ConstrutorPortaTempero(self.gerenciador_perfis)
        o_usinagens = OrquestradorUsinagens(self.gerenciador_perfis)

        todas_pecas, vao_raiz, mapa_estrutural = c_caixaria.construir(
            id_modulo=id_modulo,
            familia=familia,
            largura_x=largura_x,
            altura_y=altura_y,
            profundidade_z=profundidade_z,
            com_fundo=com_fundo
        )

        operacoes_executadas = operacoes_internas or []

        for op in operacoes_executadas:
            tipo_op = str(op.get("tipo", "")).strip().upper()
            vao_alvo = self._resolver_vao_alvo(vao_raiz, op)

            validador.validar_operacao_no_vao(familia, vao_alvo, op)

            if tipo_op == "DIVISORIA_VERTICAL":
                peca_div, _ = c_internos.inserir_divisoria_vertical(
                    id_modulo=id_modulo, vao_alvo=vao_alvo, posicao_x_relativa=op.get("posicao_x")
                )
                todas_pecas.append(peca_div)

            elif tipo_op == "DIVISORIA_HORIZONTAL":
                peca_prat_fixa, _ = c_internos.inserir_prateleira(
                    id_modulo=id_modulo, vao_alvo=vao_alvo, fixa=True, posicao_z_relativa=op.get("posicao_z")
                )
                todas_pecas.append(peca_prat_fixa)

            elif tipo_op == "PRATELEIRAS":
                novas_prats = c_internos.distribuir_prateleiras_iguais(
                    id_modulo=id_modulo,
                    vao_alvo=vao_alvo,
                    quantidade=int(op.get("quantidade", 1)),
                    fixas=bool(op.get("fixas", False))
                )
                todas_pecas.extend(novas_prats)

            elif tipo_op == "GAVETEIRO":
                pecas_gav = c_gavetas.construir_gaveteiro(
                    id_modulo=id_modulo, vao_alvo=vao_alvo, quantidade_gavetas=int(op.get("quantidade", 4))
                )
                todas_pecas.extend(pecas_gav)

            elif tipo_op == "PORTA_TEMPERO":
                pecas_temp = c_tempero.construir_porta_tempero(id_modulo=id_modulo, vao_alvo=vao_alvo)
                todas_pecas.extend(pecas_temp)

            elif tipo_op == "PORTAS_GIRO":
                pecas_portas = c_frentes.construir_portas_giro(
                    id_modulo=id_modulo, vao_alvo=vao_alvo, tipo_abertura=str(op.get("abertura", "DUPLA"))
                )
                todas_pecas.extend(pecas_portas)
            
            elif tipo_op == "GAVETEIRO_INTERNO":
             pecas_gav_int = c_gavetas.construir_gaveteiro_interno(
                 id_modulo=id_modulo, vao_alvo=vao_alvo, quantidade_gavetas=int(op.get("quantidade", 3))
             )
             todas_pecas.extend(pecas_gav_int)
            
            elif tipo_op == "SAPATEIRA":
             pecas_sap = c_gavetas.construir_sapateira(
                 id_modulo=id_modulo, vao_alvo=vao_alvo, quantidade_sapateiras=int(op.get("quantidade", 2))
             )
             todas_pecas.extend(pecas_sap)
             
            elif tipo_op == "PORTAS_BASCULANTES":
             pecas_basc = c_frentes.construir_portas_basculantes(
                 id_modulo=id_modulo, vao_alvo=vao_alvo, quantidade_basculantes=int(op.get("quantidade", 1))
             )
             todas_pecas.extend(pecas_basc)
            
        o_usinagens.aplicar_todas_usinagens(mapa_estrutural, vao_raiz)

        alertas_engenharia: List[str] = []
        for p in todas_pecas:
            alertas_engenharia.extend(p.avisos_auditoria)

        return self._empacotar_payload(
            id_modulo, nome_projeto, familia, largura_x, altura_y, profundidade_z,
            mat_caixa, mat_frentes, operacoes_executadas, vao_raiz.to_dict(),
            alertas_engenharia, todas_pecas, None
        )

    def _empacotar_payload(
        self, id_mod, nome_proj, familia, lx, ay, pz, mat_c, mat_f, ops, arvore, alertas, pecas, msg_custom
    ) -> Dict[str, Any]:
        payload = {
            "id_modulo": id_mod,
            "guid": str(uuid.uuid4()),
            "nome_projeto": nome_proj,
            "familia": familia,
            "dimensoes_ocupadas": {
                "largura_x": round(float(lx), 2),
                "altura_y": round(float(ay), 2),
                "profundidade_z": round(float(pz), 2)
            },
            "parametros": {
                "material_caixaria": mat_c,
                "material_frentes": mat_f,
                "id_perfil_ativo": self.gerenciador_perfis.id_perfil_ativo,
                "perfil_ativo": self.gerenciador_perfis.dados_perfil
            },
            "operacoes_internas": ops,
            "arvore_espacial_vaos": arvore,
            "alertas_engenharia": alertas,
            "lista_de_pecas": [p.to_dict() for p in pecas]
        }
        if msg_custom:
            payload["resposta_copiloto"] = msg_custom
        return payload