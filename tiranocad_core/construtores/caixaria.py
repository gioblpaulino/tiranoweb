# =============================================================================
# ARQUIVO: tiranocad_core/construtores/caixaria.py
# RESPONSABILIDADE: Construir a estrutura externa para Balcão Inferior, Aéreo e
# Torre, incluindo Mão Amiga 45°, Travessas de Duplo Reforço em Torres, opção
# Sem Travessa Traseira no Balcão e correção de Teto em Lateral Passante.
# =============================================================================

from typing import Dict, List, Tuple
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorCaixaria:
    """
    Especialista na montagem da estrutura externa de módulos de marcenaria.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir(
        self,
        id_modulo: str,
        familia: str,
        largura_x: float,
        altura_y: float,
        profundidade_z: float,
        com_fundo: bool = True
    ) -> Tuple[List[Peca], NoEspacial, Dict[str, Peca]]:
        familia = familia.strip().upper()

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_fundo = float(self.perfil.obter("materiais_padrao.espessura_fundo_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_fundo = str(self.perfil.obter("materiais_padrao.material_fundo"))

        modo_base = str(self.perfil.obter("geometria_caixaria.montagem_base_inferior")).strip().upper()
        modo_teto_balcao = str(self.perfil.obter("geometria_caixaria.montagem_teto_balcao")).strip().upper()
        pos_sarrafo_tras = str(self.perfil.obter("geometria_caixaria.posicao_sarrafo_traseiro_balcao")).strip().upper()
        modo_fundo = str(self.perfil.obter("geometria_caixaria.tipo_montagem_fundo")).strip().upper()

        fixacao_aereo = str(self.perfil.obter("geometria_caixaria.sistema_fixacao_aereo")).strip().upper()
        alt_total_mao_amiga = float(self.perfil.obter("geometria_caixaria.altura_total_mao_amiga"))
        folga_mao_amiga = float(self.perfil.obter("geometria_caixaria.folga_encaixe_mao_amiga"))

        reforco_torre = str(self.perfil.obter("geometria_caixaria.reforco_traseiro_torre")).strip().upper()
        alt_travessa_torre = float(self.perfil.obter("geometria_caixaria.altura_travessa_reforco_torre"))

        if not com_fundo:
            modo_fundo = "SEM_FUNDO"

        larg_sarrafo = float(self.perfil.obter("geometria_caixaria.largura_sarrafo"))
        recuo_fundo_padrao = float(self.perfil.obter("geometria_caixaria.recuo_canal_fundo"))
        folga_fundo = float(self.perfil.obter("geometria_caixaria.folga_encaixe_fundo"))

        larg_canal = float(self.perfil.obter("parametros_usinagem.largura_canal_fundo"))
        prof_canal = float(self.perfil.obter("parametros_usinagem.profundidade_canal_fundo"))

        tem_veio_caixa = not any(cor in mat_caixa.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        eh_aereo = (familia == "MODULO_AEREO")
        eh_torre = (familia in ("MODULO_ALTO", "MODULO_TORRE"))
        usa_teto_inteiro = eh_aereo or eh_torre or (modo_teto_balcao == "TAMPO_INTEIRO")
        base_eh_passante = (modo_base == "BASE_PASSANTE")
        tem_rasgo_fundo = (modo_fundo == "ENCAIXADO_RASGO")

        # Se for Aéreo com Mão Amiga 45° ou Torre com Reforço Traseiro atrás do fundo,
        # garante que o recuo do canal comporte a espessura da régua/travessa traseira!
        precisa_recuo_espessura_mdf = (
            (eh_aereo and fixacao_aereo == "REGUA_MAO_AMIGA_45") or
            (eh_torre and reforco_torre in ("TRAVESSA_DUPLO_REFORCO", "TRAVESSA_SIMPLES_TOPO"))
        )
        recuo_fundo_efetivo = max(recuo_fundo_padrao, esp_mdf + 1.0) if precisa_recuo_espessura_mdf else recuo_fundo_padrao

        largura_vao_interno = round(largura_x - (2.0 * esp_mdf), 2)
        cota_y_canal_fundo = round(profundidade_z - recuo_fundo_efetivo - esp_fundo, 2) if tem_rasgo_fundo else profundidade_z

        if cota_y_canal_fundo <= larg_sarrafo:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade ({profundidade_z}mm) insuficiente para a estrutura e recuo de fundo."
            )

        # Correção de Lateral Passante: Na Lateral Passante, tanto a Base quanto o Teto ficam ENTRE as laterais!
        z_inicio_lateral = esp_mdf if base_eh_passante else 0.0
        desconto_topo_lateral = esp_mdf if (usa_teto_inteiro and base_eh_passante) else 0.0
        altura_lateral = round(altura_y - z_inicio_lateral - desconto_topo_lateral, 2)

        largura_base_e_teto = largura_x if base_eh_passante else largura_vao_interno
        pos_x_base_e_teto = 0.0 if base_eh_passante else esp_mdf

        pecas_geradas: List[Peca] = []
        mapa_estrutural: Dict[str, Peca] = {}

        # =====================================================================
        # PEÇA 1: BASE INFERIOR
        # =====================================================================
        base_inf = Peca(
            categoria_industrial="base_inferior",
            nome_comercial=self.perfil.obter_nome_peca("base_inferior"),
            dim_3d=(largura_base_e_teto, profundidade_z, esp_mdf),
            pos_3d=(pos_x_base_e_teto, 0.0, 0.0),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio_caixa
        )
        base_inf.fitas.base = True
        if tem_rasgo_fundo:
            base_inf.adicionar_rasgo(0.0, cota_y_canal_fundo, larg_canal, largura_base_e_teto, prof_canal, "H", "CANAL_FUNDO")
        pecas_geradas.append(base_inf)
        mapa_estrutural["base_inferior"] = base_inf

        # =====================================================================
        # PEÇAS 2 e 3: LATERAL ESQUERDA E LATERAL DIREITA
        # =====================================================================
        for eh_direita, cat_lat, pos_x_lat in (
            (False, "lateral_esquerda", 0.0),
            (True, "lateral_direita", largura_x - esp_mdf)
        ):
            lat = Peca(
                categoria_industrial=cat_lat,
                nome_comercial=self.perfil.obter_nome_peca(cat_lat),
                dim_3d=(esp_mdf, profundidade_z, altura_lateral),
                pos_3d=(pos_x_lat, 0.0, z_inicio_lateral),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=eh_direita
            )
            lat.fitas.esquerda = True
            if tem_rasgo_fundo:
                lat.adicionar_rasgo(cota_y_canal_fundo, 0.0, larg_canal, altura_lateral, prof_canal, "V", "CANAL_FUNDO")
            pecas_geradas.append(lat)
            mapa_estrutural[cat_lat] = lat

        # =====================================================================
        # PEÇA 4: FECHAMENTO SUPERIOR (Teto Inteiro ou Sarrafos do Balcão)
        # =====================================================================
        cota_z_topo = round(altura_y - esp_mdf, 2)
        peca_vizinha_topo: Peca

        if usa_teto_inteiro:
            base_sup = Peca(
                categoria_industrial="base_superior",
                nome_comercial=self.perfil.obter_nome_peca("base_superior"),
                dim_3d=(largura_base_e_teto, profundidade_z, esp_mdf),
                pos_3d=(pos_x_base_e_teto, 0.0, cota_z_topo),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            base_sup.fitas.base = True
            if tem_rasgo_fundo:
                base_sup.adicionar_rasgo(0.0, cota_y_canal_fundo, larg_canal, largura_base_e_teto, prof_canal, "H", "CANAL_FUNDO")
            pecas_geradas.append(base_sup)
            mapa_estrutural["base_superior"] = base_sup
            peca_vizinha_topo = base_sup
        else:
            # 4A. Sarrafo Frontal (Sempre presente no Balcão)
            sarrafo_front = Peca(
                categoria_industrial="sarrafo_frontal",
                nome_comercial=self.perfil.obter_nome_peca("sarrafo_frontal"),
                dim_3d=(largura_vao_interno, larg_sarrafo, esp_mdf),
                pos_3d=(esp_mdf, 0.0, cota_z_topo),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            sarrafo_front.fitas.base = True
            pecas_geradas.append(sarrafo_front)
            mapa_estrutural["sarrafo_frontal"] = sarrafo_front
            peca_vizinha_topo = sarrafo_front

            # 4B. Sarrafo Traseiro do Balcão: DEITADO, EM_PE ou SEM_TRAVESSA_TRASEIRA!
            if pos_sarrafo_tras == "SEM_TRAVESSA_TRASEIRA":
                pass
            elif pos_sarrafo_tras == "EM_PE":
                pos_y_em_pe = round(cota_y_canal_fundo - esp_mdf, 2)
                pos_z_em_pe = round(altura_y - larg_sarrafo, 2)
                sarrafo_tras = Peca(
                    categoria_industrial="sarrafo_traseiro_em_pe",
                    nome_comercial=self.perfil.obter_nome_peca("sarrafo_traseiro_em_pe"),
                    dim_3d=(largura_vao_interno, esp_mdf, larg_sarrafo),
                    pos_3d=(esp_mdf, pos_y_em_pe, pos_z_em_pe),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa
                )
                sarrafo_tras.fitas.base = True
                pecas_geradas.append(sarrafo_tras)
                mapa_estrutural["sarrafo_traseiro_em_pe"] = sarrafo_tras
            else:
                pos_y_deitado = round(cota_y_canal_fundo - larg_sarrafo, 2)
                sarrafo_tras = Peca(
                    categoria_industrial="sarrafo_traseiro_deitado",
                    nome_comercial=self.perfil.obter_nome_peca("sarrafo_traseiro_deitado"),
                    dim_3d=(largura_vao_interno, larg_sarrafo, esp_mdf),
                    pos_3d=(esp_mdf, pos_y_deitado, cota_z_topo),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa
                )
                sarrafo_tras.fitas.base = True
                pecas_geradas.append(sarrafo_tras)
                mapa_estrutural["sarrafo_traseiro_deitado"] = sarrafo_tras

        # =====================================================================
        # PEÇA 5: SISTEMAS DE FIXAÇÃO DE AÉREO (Mão Amiga 45° / Travessa Interna)
        # =====================================================================
        if eh_aereo:
            if fixacao_aereo == "REGUA_MAO_AMIGA_45":
                alt_cada_mao_amiga = round((alt_total_mao_amiga / 2.0) + (esp_mdf / 2.0), 2)
                y_mao_amiga = round(profundidade_z - esp_mdf, 2)
                z_mao_movel = round(altura_y - esp_mdf - alt_cada_mao_amiga, 2)
                z_mao_parede = round(z_mao_movel - alt_cada_mao_amiga - folga_mao_amiga, 2)

                # Metade Superior (Presa no Móvel)
                regua_movel = Peca(
                    categoria_industrial="regua_mao_amiga_movel",
                    nome_comercial=self.perfil.obter_nome_peca("regua_mao_amiga_movel"),
                    dim_3d=(largura_vao_interno, esp_mdf, alt_cada_mao_amiga),
                    pos_3d=(esp_mdf, y_mao_amiga, z_mao_movel),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa
                )
                regua_movel.fitas.base = True

                # Metade Inferior (Vai presa na Parede)
                regua_parede = Peca(
                    categoria_industrial="regua_mao_amiga_parede",
                    nome_comercial=self.perfil.obter_nome_peca("regua_mao_amiga_parede"),
                    dim_3d=(largura_vao_interno - 10.0, esp_mdf, alt_cada_mao_amiga),
                    pos_3d=(esp_mdf + 5.0, y_mao_amiga, z_mao_parede),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa
                )
                regua_parede.fitas.topo = True

                pecas_geradas.extend([regua_movel, regua_parede])
                mapa_estrutural["regua_mao_amiga_movel"] = regua_movel
                mapa_estrutural["regua_mao_amiga_parede"] = regua_parede

            elif fixacao_aereo == "TRAVESSA_INTERNA_EM_PE":
                pos_y_trav_int = round(cota_y_canal_fundo - esp_mdf, 2)
                pos_z_trav_int = round(altura_y - esp_mdf - larg_sarrafo, 2)
                trav_aereo = Peca(
                    categoria_industrial="travessa_fixacao_aereo",
                    nome_comercial=self.perfil.obter_nome_peca("travessa_fixacao_aereo"),
                    dim_3d=(largura_vao_interno, esp_mdf, larg_sarrafo),
                    pos_3d=(esp_mdf, pos_y_trav_int, pos_z_trav_int),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa
                )
                trav_aereo.fitas.base = True
                pecas_geradas.append(trav_aereo)
                mapa_estrutural["travessa_fixacao_aereo"] = trav_aereo

        # =====================================================================
        # PEÇA 6: TRAVESSAS DE REFORÇO TRASEIRO EM TORRES / MÓDULOS ALTOS
        # =====================================================================
        if eh_torre and reforco_torre in ("TRAVESSA_DUPLO_REFORCO", "TRAVESSA_SIMPLES_TOPO"):
            y_reforco = round(profundidade_z - esp_mdf, 2)
            z_ref_sup = round(altura_y - esp_mdf - alt_travessa_torre, 2)

            trav_sup = Peca(
                categoria_industrial="travessa_reforco_torre_sup",
                nome_comercial=self.perfil.obter_nome_peca("travessa_reforco_torre_sup"),
                dim_3d=(largura_vao_interno, esp_mdf, alt_travessa_torre),
                pos_3d=(esp_mdf, y_reforco, z_ref_sup),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            trav_sup.fitas.base = True
            pecas_geradas.append(trav_sup)
            mapa_estrutural["travessa_reforco_torre_sup"] = trav_sup

            if reforco_torre == "TRAVESSA_DUPLO_REFORCO":
                z_ref_inf = round(altura_y * 0.45, 2)
                trav_inf = Peca(
                    categoria_industrial="travessa_reforco_torre_inf",
                    nome_comercial=self.perfil.obter_nome_peca("travessa_reforco_torre_inf"),
                    dim_3d=(largura_vao_interno, esp_mdf, alt_travessa_torre),
                    pos_3d=(esp_mdf, y_reforco, z_ref_inf),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa
                )
                trav_inf.fitas.base = trav_inf.fitas.topo = True
                pecas_geradas.append(trav_inf)
                mapa_estrutural["travessa_reforco_torre_inf"] = trav_inf

        # =====================================================================
        # PEÇA 7: FUNDO COSTA
        # =====================================================================
        if modo_fundo == "ENCAIXADO_RASGO":
            penetracao = prof_canal - folga_fundo
            larg_fundo = round(largura_vao_interno + (2.0 * penetracao), 2)
            alt_util_caixa = round(altura_y - (2.0 * esp_mdf if usa_teto_inteiro else esp_mdf), 2)
            alt_fundo = round(alt_util_caixa + ((2.0 * penetracao) if usa_teto_inteiro else penetracao), 2)

            fundo = Peca(
                categoria_industrial="fundo_costa",
                nome_comercial=self.perfil.obter_nome_peca("fundo_costa"),
                dim_3d=(larg_fundo, esp_fundo, alt_fundo),
                pos_3d=(esp_mdf - penetracao, cota_y_canal_fundo, esp_mdf - penetracao),
                material=mat_fundo,
                id_pai=id_modulo
            )
            pecas_geradas.append(fundo)
            mapa_estrutural["fundo_costa"] = fundo

        elif modo_fundo == "SOBREPOSTO":
            fundo = Peca(
                categoria_industrial="fundo_costa",
                nome_comercial=f"{self.perfil.obter_nome_peca('fundo_costa')} (Sobreposto)",
                dim_3d=(round(largura_x - 2.0, 2), esp_fundo, round(altura_y - 2.0, 2)),
                pos_3d=(1.0, profundidade_z, 1.0),
                material=mat_fundo,
                id_pai=id_modulo
            )
            pecas_geradas.append(fundo)
            mapa_estrutural["fundo_costa"] = fundo

        # =====================================================================
        # VÃO ESPACIAL RAIZ
        # =====================================================================
        prof_util_interna = cota_y_canal_fundo if tem_rasgo_fundo else profundidade_z
        if eh_aereo and fixacao_aereo == "TRAVESSA_INTERNA_EM_PE":
            prof_util_interna = round(prof_util_interna - esp_mdf, 2)

        alt_util_interna = round(altura_y - (2.0 * esp_mdf), 2)

        vao_raiz = NoEspacial(
            x=esp_mdf,
            y=0.0,
            z=esp_mdf,
            largura=largura_vao_interno,
            profundidade=prof_util_interna,
            altura=alt_util_interna,
            nome_vao="Vão Principal",
            id_vao="raiz",
            vizinhos={
                "esquerda": mapa_estrutural["lateral_esquerda"],
                "direita": mapa_estrutural["lateral_direita"],
                "base": base_inf,
                "topo": peca_vizinha_topo
            }
        )

        return pecas_geradas, vao_raiz, mapa_estrutural