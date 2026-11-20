# =============================================================================
# ARQUIVO: tiranocad_core/construtores/bancadas_rodapes.py
# RESPONSABILIDADE: Construir Bancadas de Pedra/Marmoraria e Rodapés Estruturais
# (MDF para o TiranoCut ou Pedra) 100% Data-Driven pelo Perfil JSON.
# =============================================================================

import math
from typing import Any, Dict, List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import Peca


class ConstrutorBancadasRodapes:
    """
    Especialista na geração de Bancadas de Marmoraria (Bloco Guia 3D) e
    Rodapés Estruturais (MDF para corte CNC ou Pedra).
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_bancada_pedra(
        self,
        id_modulo: str,
        largura_x: float,
        profundidade_z: float,
        opcoes: Dict[str, Any]
    ) -> List[Peca]:
        esp_pedra = float(opcoes.get("espessura_pedra_mm", self.perfil.obter("regras_bancada_rodape.espessura_pedra_padrao_mm")))
        alt_saia = float(opcoes.get("altura_saia_frontal_mm", self.perfil.obter("regras_bancada_rodape.altura_saia_frontal_padrao_mm")))
        alt_frontao = float(opcoes.get("altura_frontao_traseiro_mm", self.perfil.obter("regras_bancada_rodape.altura_frontao_padrao_mm")))
        frontao_esq = bool(opcoes.get("frontao_lateral_esq", False))
        frontao_dir = bool(opcoes.get("frontao_lateral_dir", False))
        cascata_esq = bool(opcoes.get("cascata_esquerda", False))
        cascata_dir = bool(opcoes.get("cascata_direita", False))
        altura_piso_z = float(opcoes.get("altura_instalacao_z", self.perfil.obter("regras_bancada_rodape.altura_instalacao_bancada_z_mm")))
        margem_borda = float(self.perfil.obter("regras_bancada_rodape.margem_min_borda_acessorio_mm"))

        mat_pedra = str(opcoes.get("material_pedra", "pedra_preto_sao_gabriel"))

        possui_cuba = bool(opcoes.get("possui_cuba", False))
        pos_x_cuba = float(opcoes.get("pos_x_cuba_mm", largura_x * 0.5))
        larg_cuba = float(opcoes.get("largura_cuba_mm", self.perfil.obter("regras_bancada_rodape.largura_cuba_padrao_mm")))
        prof_cuba = float(opcoes.get("profundidade_cuba_mm", self.perfil.obter("regras_bancada_rodape.profundidade_cuba_padrao_mm")))
        alt_bojo_cuba = float(self.perfil.obter("regras_bancada_rodape.altura_bojo_cuba_mm"))

        possui_cooktop = bool(opcoes.get("possui_cooktop", False))
        pos_x_cooktop = float(opcoes.get("pos_x_cooktop_mm", largura_x * 0.5))
        larg_cooktop = float(opcoes.get("largura_cooktop_mm", self.perfil.obter("regras_bancada_rodape.largura_cooktop_padrao_mm")))
        prof_cooktop = float(opcoes.get("profundidade_cooktop_mm", self.perfil.obter("regras_bancada_rodape.profundidade_cooktop_padrao_mm")))
        esp_cooktop = float(self.perfil.obter("regras_bancada_rodape.espessura_cooktop_mm"))

        pecas: List[Peca] = []

        # 1. Tampo Principal Horizontal da Pedra
        tampo = Peca(
            categoria_industrial="marmoraria_bancada",
            nome_comercial=self.perfil.obter_nome_peca("marmoraria_bancada"),
            dim_3d=(largura_x, profundidade_z, esp_pedra),
            pos_3d=(0.0, 0.0, round(alt_saia - esp_pedra, 2)),
            material=mat_pedra,
            id_pai=id_modulo,
            tem_veio=False
        )
        pecas.append(tampo)

        # 2. Saia / Testeira Frontal
        if alt_saia > esp_pedra:
            saia = Peca(
                categoria_industrial="marmoraria_saia",
                nome_comercial=self.perfil.obter_nome_peca("marmoraria_saia"),
                dim_3d=(largura_x, esp_pedra, alt_saia),
                pos_3d=(0.0, 0.0, 0.0),
                material=mat_pedra,
                id_pai=id_modulo,
                tem_veio=False
            )
            pecas.append(saia)

        # 3. Frontão / Rodopia Traseiro e Laterais
        if alt_frontao > 0:
            frontao_tras = Peca(
                categoria_industrial="marmoraria_frontao",
                nome_comercial=self.perfil.obter_nome_peca("marmoraria_frontao_traseiro"),
                dim_3d=(largura_x, esp_pedra, alt_frontao),
                pos_3d=(0.0, round(profundidade_z - esp_pedra, 2), alt_saia),
                material=mat_pedra,
                id_pai=id_modulo,
                tem_veio=False
            )
            pecas.append(frontao_tras)

            prof_lat_frontao = round(profundidade_z - esp_pedra, 2)
            if frontao_esq:
                pecas.append(Peca(
                    categoria_industrial="marmoraria_frontao",
                    nome_comercial=self.perfil.obter_nome_peca("marmoraria_frontao_esq"),
                    dim_3d=(esp_pedra, prof_lat_frontao, alt_frontao),
                    pos_3d=(0.0, 0.0, alt_saia),
                    material=mat_pedra,
                    id_pai=id_modulo
                ))

            if frontao_dir:
                pecas.append(Peca(
                    categoria_industrial="marmoraria_frontao",
                    nome_comercial=self.perfil.obter_nome_peca("marmoraria_frontao_dir"),
                    dim_3d=(esp_pedra, prof_lat_frontao, alt_frontao),
                    pos_3d=(round(largura_x - esp_pedra, 2), 0.0, alt_saia),
                    material=mat_pedra,
                    id_pai=id_modulo
                ))

        # 4. Pé / Cascata Lateral até o Piso
        if cascata_esq:
            pecas.append(Peca(
                categoria_industrial="marmoraria_cascata",
                nome_comercial=self.perfil.obter_nome_peca("marmoraria_cascata_esq"),
                dim_3d=(esp_pedra, profundidade_z, altura_piso_z),
                pos_3d=(-esp_pedra, 0.0, round(alt_saia - altura_piso_z, 2)),
                material=mat_pedra,
                id_pai=id_modulo
            ))

        if cascata_dir:
            pecas.append(Peca(
                categoria_industrial="marmoraria_cascata",
                nome_comercial=self.perfil.obter_nome_peca("marmoraria_cascata_dir"),
                dim_3d=(esp_pedra, profundidade_z, altura_piso_z),
                pos_3d=(largura_x, 0.0, round(alt_saia - altura_piso_z, 2)),
                material=mat_pedra,
                id_pai=id_modulo
            ))

        # 5. Cuba Inox Embutida
        if possui_cuba:
            x_ini_cuba = max(margem_borda, min(largura_x - larg_cuba - margem_borda, pos_x_cuba - (larg_cuba / 2.0)))
            y_ini_cuba = round((profundidade_z - prof_cuba) / 2.0, 2)
            pecas.append(Peca(
                categoria_industrial="acessorio_cuba_inox",
                nome_comercial=f"Cuba Inox ({larg_cuba:.0f}x{prof_cuba:.0f}mm)",
                dim_3d=(larg_cuba, prof_cuba, alt_bojo_cuba),
                pos_3d=(round(x_ini_cuba, 2), y_ini_cuba, round(alt_saia - alt_bojo_cuba + 4.0, 2)),
                material="inox_escovado",
                id_pai=id_modulo
            ))

        # 6. Cooktop de Vidro Temperado Preto
        if possui_cooktop:
            x_ini_ck = max(margem_borda, min(largura_x - larg_cooktop - margem_borda, pos_x_cooktop - (larg_cooktop / 2.0)))
            y_ini_ck = round((profundidade_z - prof_cooktop) / 2.0, 2)
            pecas.append(Peca(
                categoria_industrial="acessorio_cooktop",
                nome_comercial=f"Cooktop ({larg_cooktop:.0f}x{prof_cooktop:.0f}mm)",
                dim_3d=(larg_cooktop, prof_cooktop, esp_cooktop),
                pos_3d=(round(x_ini_ck, 2), y_ini_ck, round(alt_saia + 1.0, 2)),
                material="generico_preto_tx",
                id_pai=id_modulo
            ))

        return pecas

    def construir_rodape(
        self,
        id_modulo: str,
        largura_x: float,
        altura_z: float,
        profundidade_modulo_base: float,
        opcoes: Dict[str, Any]
    ) -> List[Peca]:
        modelo = str(opcoes.get("modelo_rodape", "MDF_DUPLO_CALCOS")).strip().upper()
        recuo_frontal = float(opcoes.get("recuo_frontal_mm", self.perfil.obter("regras_bancada_rodape.recuo_frontal_rodape_padrao_mm")))
        recuo_traseiro = float(opcoes.get("recuo_traseiro_mm", self.perfil.obter("regras_bancada_rodape.recuo_traseiro_rodape_padrao_mm")))
        fechar_esq = bool(opcoes.get("fechar_lateral_esq", True))
        fechar_dir = bool(opcoes.get("fechar_lateral_dir", True))

        esp_pedra = float(self.perfil.obter("regras_bancada_rodape.espessura_pedra_padrao_mm"))
        esp_mdf_padrao = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa_padrao = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        prof_min_quadro = float(self.perfil.obter("regras_bancada_rodape.profundidade_min_quadro_rodape_mm"))
        dist_max_calcos = float(self.perfil.obter("regras_bancada_rodape.distancia_max_entre_calcos_rodape_mm"))

        eh_pedra = (modelo == "PEDRA_GRANITO")
        esp = esp_pedra if eh_pedra else float(opcoes.get("espessura_mdf_mm", esp_mdf_padrao))
        mat = str(opcoes.get("material_rodape", "pedra_preto_sao_gabriel" if eh_pedra else mat_caixa_padrao))
        tem_veio = False if eh_pedra else self.perfil.material_possui_veio(mat)

        cat_peca = "marmoraria_rodape" if eh_pedra else "rodape_mdf"
        prof_quadro = max(prof_min_quadro, round(profundidade_modulo_base - recuo_frontal - recuo_traseiro, 2))

        max_comp_chapa = float(self.perfil.obter("restricoes_chapa.comprimento_max_mdf"))
        refilo = float(self.perfil.obter("restricoes_chapa.refilo_seguranca"))
        limite_util = max_comp_chapa - (2.0 * refilo)

        qtd_tramos = 1 if eh_pedra else max(1, math.ceil(largura_x / limite_util))
        larg_tramo = round(largura_x / float(qtd_tramos), 2)
        tipo_lbl = "Pedra" if eh_pedra else "MDF"

        nome_front = self.perfil.obter_nome_peca("rodape_frontal")
        nome_tras = self.perfil.obter_nome_peca("rodape_traseiro")
        nome_calco = self.perfil.obter_nome_peca("rodape_calco_estrutural")

        pecas: List[Peca] = []

        # 1. Régua(s) Frontal(is) do Rodapé
        for idx in range(qtd_tramos):
            suf = f" {idx + 1}" if qtd_tramos > 1 else ""
            frontal = Peca(
                categoria_industrial=cat_peca,
                nome_comercial=f"{nome_front} ({tipo_lbl}){suf}",
                dim_3d=(larg_tramo, esp, altura_z),
                pos_3d=(round(idx * larg_tramo, 2), recuo_frontal, 0.0),
                material=mat,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            if not eh_pedra:
                frontal.fitas.base = True
            pecas.append(frontal)

        if modelo == "MDF_FRONTAL_SIMPLES":
            return pecas

        # 2. Régua(s) Traseira(s) do Quadro de Rodapé
        y_traseira = round(recuo_frontal + prof_quadro - esp, 2)
        for idx in range(qtd_tramos):
            suf = f" {idx + 1}" if qtd_tramos > 1 else ""
            traseira = Peca(
                categoria_industrial=cat_peca,
                nome_comercial=f"{nome_tras} ({tipo_lbl}){suf}",
                dim_3d=(larg_tramo, esp, altura_z),
                pos_3d=(round(idx * larg_tramo, 2), y_traseira, 0.0),
                material=mat,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            if not eh_pedra:
                traseira.fitas.base = True
            pecas.append(traseira)

        # 3. Fechamentos Laterais e Calços Transversais Internos
        prof_interna_calco = round(prof_quadro - (2.0 * esp), 2)
        y_ini_calco = round(recuo_frontal + esp, 2)

        if fechar_esq:
            lat_e = Peca(
                categoria_industrial=cat_peca,
                nome_comercial=self.perfil.obter_nome_peca("rodape_lateral_esq"),
                dim_3d=(esp, prof_interna_calco, altura_z),
                pos_3d=(0.0, y_ini_calco, 0.0),
                material=mat,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            if not eh_pedra:
                lat_e.fitas.esquerda = lat_e.fitas.base = True
            pecas.append(lat_e)

        if fechar_dir:
            lat_d = Peca(
                categoria_industrial=cat_peca,
                nome_comercial=self.perfil.obter_nome_peca("rodape_lateral_dir"),
                dim_3d=(esp, prof_interna_calco, altura_z),
                pos_3d=(round(largura_x - esp, 2), y_ini_calco, 0.0),
                material=mat,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            if not eh_pedra:
                lat_d.fitas.esquerda = lat_d.fitas.base = True
            pecas.append(lat_d)

        if modelo == "MDF_DUPLO_CALCOS" and largura_x > (dist_max_calcos + 50.0):
            qtd_vaos = math.ceil(largura_x / dist_max_calcos)
            passo_x = largura_x / float(qtd_vaos)
            for idx_c in range(1, qtd_vaos):
                x_calco = round((idx_c * passo_x) - (esp / 2.0), 2)
                calco = Peca(
                    categoria_industrial="rodape_mdf",
                    nome_comercial=f"{nome_calco} {idx_c}",
                    dim_3d=(esp, prof_interna_calco, altura_z),
                    pos_3d=(x_calco, y_ini_calco, 0.0),
                    material=mat,
                    id_pai=id_modulo,
                    tem_veio=False
                )
                calco.fitas.base = True
                pecas.append(calco)

        return pecas