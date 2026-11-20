# =============================================================================
# ARQUIVO: tiranocad_core/construtores/paineis.py
# RESPONSABILIDADE: Construir Painéis Avulsos, Tampos Duplados e Tampos
# Engrossados (Sanduíche/Sarrafeado) 100% Data-Driven pelo Perfil JSON.
# =============================================================================

from typing import List, Optional
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
        orientacao_espacial: str = "VERTICAL_FRONTAL",
        modo_espessura: str = "SIMPLES",
        espessura_chapa_base: Optional[float] = None,
        material: Optional[str] = None,
        fitas_4_lados: bool = True
    ) -> List[Peca]:
        modo = modo_espessura.strip().upper()
        orient = orientacao_espacial.strip().upper()
        esp_base = float(espessura_chapa_base or self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_efetivo = str(material or self.perfil.obter("materiais_padrao.material_frentes"))
        larg_regua = float(self.perfil.obter("geometria_caixaria.largura_regua_afastador"))
        tem_veio = self.perfil.material_possui_veio(mat_efetivo)

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
            dim_3d=montar_dim_3d(largura_x, altura_y, esp_base),
            pos_3d=(0.0, 0.0, 0.0),
            material=mat_efetivo,
            id_pai=id_modulo,
            tem_veio=tem_veio
        )
        if fitas_4_lados:
            face_principal.fitas.base = face_principal.fitas.direita = True
            face_principal.fitas.topo = face_principal.fitas.esquerda = True

        pecas_geradas.append(face_principal)

        # 2. Caso DUPLADO (Duas chapas inteiras coladas face a face)
        if modo == "DUPLADO":
            pos_sec = (0.0, 0.0, esp_base) if orient == "HORIZONTAL" else (
                (esp_base, 0.0, 0.0) if orient == "VERTICAL_LATERAL" else (0.0, esp_base, 0.0)
            )
            face_interna = Peca(
                categoria_industrial="painel_duplado_interno",
                nome_comercial=f"{nome_painel} (Chapa Duplagem)",
                dim_3d=montar_dim_3d(largura_x, altura_y, esp_base),
                pos_3d=pos_sec,
                material=mat_efetivo,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            if fitas_4_lados:
                face_interna.fitas.base = face_interna.fitas.direita = True
                face_interna.fitas.topo = face_interna.fitas.esquerda = True
            pecas_geradas.append(face_interna)

        # 3. Caso ENGROSSADO COM SARRAFOS (Quadro perimetral completo com 4 réguas)
        elif modo == "ENGROSSADO_SARRAFO":
            # 2 Réguas Compridas (Base/Frontal e Topo/Traseira)
            for sufixo_r, cota_2_pos in (("Frontal/Inf", 0.0), ("Traseiro/Sup", round(altura_y - larg_regua, 2))):
                if orient == "HORIZONTAL":
                    pos_r = (0.0, cota_2_pos, -esp_base)
                elif orient == "VERTICAL_LATERAL":
                    pos_r = (esp_base, 0.0, cota_2_pos)
                else:
                    pos_r = (0.0, esp_base, cota_2_pos)

                regua_h = Peca(
                    categoria_industrial="regua_engrosso",
                    nome_comercial=f"Engrosso {sufixo_r} ({nome_painel})",
                    dim_3d=montar_dim_3d(largura_x, larg_regua, esp_base),
                    pos_3d=pos_r,
                    material=mat_efetivo,
                    id_pai=id_modulo,
                    tem_veio=tem_veio
                )
                regua_h.fitas.base = True
                pecas_geradas.append(regua_h)

            # 2 Réguas Laterais Curtas (entre as compridas)
            cota_interna_lat = round(altura_y - (2.0 * larg_regua), 2)
            if cota_interna_lat > 20.0:
                for sufixo_l, cota_1_pos in (("Esq", 0.0), ("Dir", round(largura_x - larg_regua, 2))):
                    if orient == "HORIZONTAL":
                        pos_l = (cota_1_pos, larg_regua, -esp_base)
                    elif orient == "VERTICAL_LATERAL":
                        pos_l = (esp_base, cota_1_pos, larg_regua)
                    else:
                        pos_l = (cota_1_pos, esp_base, larg_regua)

                    regua_v = Peca(
                        categoria_industrial="regua_engrosso",
                        nome_comercial=f"Engrosso {sufixo_l} ({nome_painel})",
                        dim_3d=montar_dim_3d(larg_regua, cota_interna_lat, esp_base),
                        pos_3d=pos_l,
                        material=mat_efetivo,
                        id_pai=id_modulo,
                        tem_veio=tem_veio
                    )
                    regua_v.fitas.esquerda = True
                    pecas_geradas.append(regua_v)

        return pecas_geradas