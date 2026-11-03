# =============================================================================
# ARQUIVO: tiranocad_core/orquestradores/orquestrador_modulo.py
# RESPONSABILIDADE: Orquestrar a fabricação completa de Módulos, Painéis e
# Avulsos, despachando todas as operações espaciais para os construtores.
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
from tiranocad_core.construtores.tamponamentos import ConstrutorTamponamento


class OrquestradorModulo:
    """Maestro central do TiranoCAD em Python."""

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
        opcoes_especiais: Optional[Dict[str, Any]] = None,
        zonas_materiais: Optional[Dict[str, Any]] = None,
        overrides_pecas: Optional[Dict[str, Any]] = None,
        tamponamentos_agregados: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        familia = familia.strip().upper()
        opcoes_esp = opcoes_especiais or {}

        self.gerenciador_perfis.carregar_perfil(id_perfil, overrides_ui=overrides_perfil)
        validador = ValidadorEngenharia(self.gerenciador_perfis)
        validador.validar_dimensoes_modulo(familia, largura_x, altura_y, profundidade_z)

        mat_caixa = str(self.gerenciador_perfis.obter("materiais_padrao.material_caixaria"))
        mat_frentes = str(self.gerenciador_perfis.obter("materiais_padrao.material_frentes"))
        esp_caixa = float(self.gerenciador_perfis.obter("materiais_padrao.espessura_estrutural_mm"))

        if familia == "MODULO_PAINEL":
            c_paineis = ConstrutorPaineis(self.gerenciador_perfis)
            modo_esp = str(opcoes_esp.get("modo_espessura", "SIMPLES")).upper()
            orientacao = str(opcoes_esp.get("orientacao_espacial", "VERTICAL_FRONTAL")).upper()
            nome_p = str(opcoes_esp.get("nome_personalizado", f"Painel {modo_esp.title()}"))

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
                f"🪵 Construtor de Painéis: '{nome_p}' ({modo_esp}) fabricado com {len(pecas_painel)} peça(s)."
            )

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

            elif tipo_op == "PORTA_TEMPERO":
                pecas_temp = c_tempero.construir_porta_tempero(id_modulo=id_modulo, vao_alvo=vao_alvo)
                todas_pecas.extend(pecas_temp)

            elif tipo_op == "PORTAS_GIRO":
                pecas_portas = c_frentes.construir_portas_giro(
                    id_modulo=id_modulo, vao_alvo=vao_alvo, tipo_abertura=str(op.get("abertura", "DUPLA"))
                )
                todas_pecas.extend(pecas_portas)

            elif tipo_op == "PORTAS_BASCULANTES":
                pecas_basc = c_frentes.construir_portas_basculantes(
                    id_modulo=id_modulo, vao_alvo=vao_alvo, quantidade_basculantes=int(op.get("quantidade", 1))
                )
                todas_pecas.extend(pecas_basc)

        o_usinagens.aplicar_todas_usinagens(mapa_estrutural, vao_raiz)
        
        # Gera os Tamponamentos Agregados e a Vista em "L" (se ativos no módulo)
        if tamponamentos_agregados and tamponamentos_agregados.get("ativo"):
            c_tamp = ConstrutorTamponamento(self.gerenciador_perfis)
            pecas_tamp = c_tamp.construir_tamponamentos_agregados(
                id_modulo=id_modulo,
                largura_mod=largura_x,
                altura_mod=altura_y,
                profundidade_mod=profundidade_z,
                config_tamp=tamponamentos_agregados
            )
            todas_pecas.extend(pecas_tamp)
            
        self.aplicar_matriz_materiais(todas_pecas, zonas_materiais, overrides_pecas)

        alertas_engenharia: List[str] = []
        for p in todas_pecas:
            alertas_engenharia.extend(p.avisos_auditoria)

        return self._empacotar_payload(
            id_modulo, nome_projeto, familia, largura_x, altura_y, profundidade_z,
            mat_caixa, mat_frentes, operacoes_executadas, vao_raiz.to_dict(),
            alertas_engenharia, todas_pecas, None, zonas_materiais, overrides_pecas,
            tamponamentos_agregados
        )

    @staticmethod
    def aplicar_matriz_materiais(
        lista_pecas: List[Peca],
        zonas_materiais: Optional[Dict[str, Any]] = None,
        overrides_pecas: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> None:
        """
        Aplica a Matriz de 8 Zonas de Materiais/Fitas e os Overrides de Peças
        Individuais sem interferir na engenharia geométrica ou nas furações.
        """
        zonas = zonas_materiais or {}
        ov_pecas = overrides_pecas or {}

        def possui_veio(nome_mat: str) -> bool:
            return not any(iso in nome_mat.upper() for iso in ["BRANCO", "CRU", "PRETO", "CINZA", "GRAFITE", "TX"])

        # Categorias pertencentes a cada Zona
        cats_caixaria = {
            "base_inferior", "base_superior", "lateral_esquerda", "lateral_direita",
            "sarrafo_frontal", "sarrafo_traseiro_deitado", "sarrafo_traseiro_em_pe",
            "regua_mao_amiga_movel", "regua_mao_amiga_parede", "travessa_fixacao_aereo",
            "travessa_reforco_torre_sup", "travessa_reforco_torre_inf"
        }
        cats_frentes = {
            "porta_giro_esquerda", "porta_giro_direita", "porta_basculante",
            "frente_gaveta", "frente_porta_tempero", "painel_tamponamento"
        }
        cats_fundo_gaveta = {"fundo_gaveta", "fundo_sapateira"}

        for p in lista_pecas:
            cat = p.categoria_industrial.lower()

            # 1. Aplicação das 8 Zonas Globais do Módulo
            if cat in cats_caixaria:
                if zonas.get("cor_caixaria"):
                    p.material = str(zonas["cor_caixaria"])
                p.cor_fita_borda = str(zonas.get("fita_frontal_caixaria") or p.material)

            elif cat in cats_frentes:
                if zonas.get("cor_frentes"):
                    p.material = str(zonas["cor_frentes"])
                p.cor_fita_borda = str(zonas.get("fita_frentes") or p.material)

            elif cat in cats_fundo_gaveta:
                if zonas.get("cor_fundo_gaveta"):
                    p.material = str(zonas["cor_fundo_gaveta"])
                p.cor_fita_borda = "SEM_FITA"

            elif cat == "fundo_costa":
                if zonas.get("cor_fundo_costa"):
                    p.material = str(zonas["cor_fundo_costa"])
                p.cor_fita_borda = "SEM_FITA"

            else:
                # Zona 3: Todos os Internos (Divisórias, Prateleiras, Corpo de Gaveta, Sapateira, Internos Tempero)
                if zonas.get("cor_internos"):
                    p.material = str(zonas["cor_internos"])
                p.cor_fita_borda = str(zonas.get("fita_internos") or p.material)

            p.tem_veio = False if "fundo" in cat else possui_veio(p.material)

            # 2. Aplicação de Override de Peça Individual (Indexado por nome_comercial)
            ov = ov_pecas.get(p.nome_comercial)
            if ov:
                if ov.get("material"):
                    p.material = str(ov["material"])
                    p.tem_veio = False if "fundo" in cat else possui_veio(p.material)
                if ov.get("cor_fita_borda"):
                    p.cor_fita_borda = str(ov["cor_fita_borda"])
                if "fitas_borda" in ov and isinstance(ov["fitas_borda"], dict):
                    fb = ov["fitas_borda"]
                    p.fitas.base = bool(fb.get("base", p.fitas.base))
                    p.fitas.topo = bool(fb.get("topo", p.fitas.topo))
                    p.fitas.esquerda = bool(fb.get("esquerda", p.fitas.esquerda))
                    p.fitas.direita = bool(fb.get("direita", p.fitas.direita))
                    
    def _empacotar_payload(
        self, id_mod, nome_proj, familia, lx, ay, pz, mat_c, mat_f, ops, arvore,
        alertas, pecas, msg_custom, zonas_materiais=None, overrides_pecas=None,
        tamponamentos_agregados=None
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
                "perfil_ativo": self.gerenciador_perfis.dados_perfil,
                "zonas_materiais": zonas_materiais or {},
                "overrides_pecas": overrides_pecas or {},
                "tamponamentos_agregados": tamponamentos_agregados or {}
            },
            "operacoes_internas": ops,
            "arvore_espacial_vaos": arvore,
            "alertas_engenharia": alertas,
            "lista_de_pecas": [p.to_dict() for p in pecas]
        }
        if msg_custom:
            payload["resposta_copiloto"] = msg_custom
        return payload