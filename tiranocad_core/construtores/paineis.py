# =============================================================================
# ARQUIVO: tiranocad_core/construtores/paineis.py
# RESPONSABILIDADE: Construir Painéis Avulsos, Tamponamentos, Fechamentos,
# Tampos Duplados (30mm/36mm) e Tampos Engrossados (Sanduíche/Sarrafeado),
# enviando as peças reais de corte e flags de engrosso para o TiranoCut.
# =============================================================================

from typing import Any, Dict, List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import Peca


class ConstrutorPaineis:
    """
    Especialista na geração de painéis arquitetônicos, tamponamentos e tampos compostos.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_painel(
        self,
        id_modulo: str,
        nome_painel: str,
        largura_x: float,
        altura_y: float,
        orientacao_espacial: str = "VERTICAL_FRONTAL", # "HORIZONTAL", "VERTICAL_LATERAL", "VERTICAL_FRONTAL"
        modo_espessura: str = "SIMPLES",               # "SIMPLES", "DUPLADO", "ENGROSSADO_SARRAFO"
        espessura_chapa_base: float = 15.0,
        material: str = "generico_branco_tx",
        fitas_4_lados: bool = True
    ) -> List[Peca]:
        """
        Gera a(s) peça(s) de MDF necessárias para fabricar o painel/tamponamento.
        Se for DUPLADO ou ENGROSSADO, já cria as peças secundárias de corte para a CNC!
        """
        modo = modo_espessura.strip().upper()
        orient = orientacao_espacial.strip().upper()
        larg_regua = float(self.perfil.obter("geometria_caixaria.largura_regua_afastador"))
        tem_veio = not any(c in material.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        # Define as cotas 3D conforme a posição do painel no ambiente
        def montar_dim_3d(cota_1: float, cota_2: float, esp: float):
            if orient == "HORIZONTAL":
                return (cota_1, cota_2, esp)
            elif orient == "VERTICAL_LATERAL":
                return (esp, cota_1, cota_2)
            return (cota_1, esp, cota_2)

        pecas_geradas: List[Peca] = []

        # 1. Chapa Principal Visível
        face_principal = Peca(
            categoria_industrial="painel_tamponamento",
            nome_comercial=nome_painel,
            dim_3d=montar_dim_3d(largura_x, altura_y, espessura_chapa_base),
            pos_3d=(0.0, 0.0, 0.0),
            material=material,
            id_pai=id_modulo,
            tem_veio=tem_veio
        )
        if fitas_4_lados:
            face_principal.fitas.base = face_principal.fitas.direita = True
            face_principal.fitas.topo = face_principal.fitas.esquerda = True

        pecas_geradas.append(face_principal)

        # 2. Caso DUPLADO (Duas chapas inteiras coladas face a face -> Ex: 15+15 = 30mm)
        if modo == "DUPLADO":
            pos_sec = (0.0, 0.0, espessura_chapa_base) if orient == "HORIZONTAL" else (
                (espessura_chapa_base, 0.0, 0.0) if orient == "VERTICAL_LATERAL" else (0.0, espessura_chapa_base, 0.0)
            )
            face_interna = Peca(
                categoria_industrial="painel_duplado_interno",
                nome_comercial=f"{nome_painel} (Chapa Duplagem)",
                dim_3d=montar_dim_3d(largura_x, altura_y, espessura_chapa_base),
                pos_3d=pos_sec,
                material=material,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            if fitas_4_lados:
                face_interna.fitas.base = face_interna.fitas.direita = True
                face_interna.fitas.topo = face_interna.fitas.esquerda = True
            pecas_geradas.append(face_interna)

        # 3. Caso ENGROSSADO COM SARRAFOS (1 Chapa Principal + Quadro Perimetral de Réguas de 60mm)
        elif modo == "ENGROSSADO_SARRAFO":
            # 2 Réguas Compridas (Frontal e Traseira) + 2 Réguas Curtas (Laterais)
            for sufixo_r, pos_z_r in (("Frontal", 0.0), ("Traseiro", altura_y - larg_regua)):
                regua_h = Peca(
                    categoria_industrial="regua_engrosso",
                    nome_comercial=f"Engrosso {sufixo_r} ({nome_painel})",
                    dim_3d=montar_dim_3d(largura_x, larg_regua, espessura_chapa_base),
                    pos_3d=(0.0, pos_z_r, -espessura_chapa_base) if orient == "HORIZONTAL" else (0.0, 0.0, 0.0),
                    material=material,
                    id_pai=id_modulo,
                    tem_veio=tem_veio
                )
                regua_h.fitas.base = True
                pecas_geradas.append(regua_h)

        return pecas_geradas