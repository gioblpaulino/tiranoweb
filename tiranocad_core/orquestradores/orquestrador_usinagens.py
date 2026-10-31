# =============================================================================
# ARQUIVO: tiranocad_core/orquestradores/orquestrador_usinagens.py
# RESPONSABILIDADE: Aplicar furações automáticas guiadas pelo Perfil JSON,
# adaptando-se a Base Passante vs. Lateral Passante, Sarrafo Deitado vs. Em Pé,
# Soberbo, Cavilha, Minifix, Gaveteiros, Porta-Tempero e Portas de Giro.
# =============================================================================

from typing import Dict, Tuple
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class OrquestradorUsinagens:
    """
    Motor matemático de furação automática Data-Driven.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    @staticmethod
    def converter_global_para_2d_peca(
        peca: Peca,
        x_global: float,
        y_global: float,
        z_global: float
    ) -> Tuple[float, float]:
        """Converte coordenadas (X, Y, Z) do armário 3D para (X_2D, Y_2D) da peça planificada."""
        dx, dy, dz = peca.dimensoes_3d["x"], peca.dimensoes_3d["y"], peca.dimensoes_3d["z"]
        px, py, pz = peca.posicao_relativa["pos_x"], peca.posicao_relativa["pos_y"], peca.posicao_relativa["pos_z"]
        esp = peca.espessura

        if esp == dz:
            return round(x_global - px, 2), round(y_global - py, 2)
        elif esp == dx:
            return round(y_global - py, 2), round(z_global - pz, 2)
        else:
            return round(x_global - px, 2), round(z_global - pz, 2)

    def aplicar_todas_usinagens(
        self,
        mapa_estrutural: Dict[str, Peca],
        vao_raiz: NoEspacial
    ) -> None:
        self._furar_caixaria_externa(mapa_estrutural)
        self._furar_arvore_recursiva(vao_raiz)

    # =========================================================================
    # 1. FURAÇÃO DA CAIXARIA EXTERNA
    # =========================================================================
    def _furar_caixaria_externa(self, mapa: Dict[str, Peca]) -> None:
        tipo_montagem = str(self.perfil.obter("tipo_montagem_caixa")).strip().upper()
        modo_base = str(self.perfil.obter("geometria_caixaria.montagem_base_inferior")).strip().upper()
        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))

        diam_estrutural = float(self.perfil.obter("parametros_usinagem.broca_parafuso_estrutural"))
        diam_cavilha = float(self.perfil.obter("parametros_usinagem.broca_cavilha"))
        prof_cavilha = float(self.perfil.obter("parametros_usinagem.profundidade_cavilha"))
        offset_cav = float(self.perfil.obter("parametros_usinagem.offset_cavilha_parafuso"))

        diam_minifix = float(self.perfil.obter("parametros_usinagem.broca_tambor_minifix"))
        prof_minifix = float(self.perfil.obter("parametros_usinagem.profundidade_tambor_minifix"))
        dist_borda_minifix = float(self.perfil.obter("parametros_usinagem.distancia_centro_minifix_borda"))

        recuo_f = float(self.perfil.obter("parametros_usinagem.recuo_furo_estrutural_frontal"))
        recuo_t = float(self.perfil.obter("parametros_usinagem.recuo_furo_estrutural_traseiro"))

        usa_cavilha = ("CAVILHA" in tipo_montagem or "MINIFIX" in tipo_montagem)
        usa_minifix = ("MINIFIX" in tipo_montagem)

        base_inf = mapa.get("base_inferior")
        lat_esq = mapa.get("lateral_esquerda")
        lat_dir = mapa.get("lateral_direita")
        base_sup = mapa.get("base_superior")
        sarrafo_front = mapa.get("sarrafo_frontal")
        sarrafo_tras_deit = mapa.get("sarrafo_traseiro_deitado")
        sarrafo_tras_pe = mapa.get("sarrafo_traseiro_em_pe")

        meia_esp = esp_mdf / 2.0

        # 1A. União Base Inferior <-> Laterais (Respeita Base Passante vs. Lateral Passante)
        if base_inf and lat_esq and lat_dir:
            prof_total = base_inf.dimensoes_3d["y"]
            cotas_y_base = [recuo_f, prof_total / 2.0, prof_total - recuo_t]

            for cy in cotas_y_base:
                if modo_base == "LATERAL_PASSANTE":
                    # Na Lateral Passante, o parafuso entra pelas Laterais (Z = meia_esp)
                    # ou o Tambor Minifix fica nas bordas da Base Inferior!
                    if usa_minifix:
                        larg_b = base_inf.dimensoes_3d["x"]
                        for x_local_b in (dist_borda_minifix, larg_b - dist_borda_minifix):
                            bx, by = self.converter_global_para_2d_peca(
                                base_inf, base_inf.posicao_relativa["pos_x"] + x_local_b, cy, 0.0
                            )
                            base_inf.adicionar_furo(bx, by, diam_minifix, prof_minifix, "FACE_INTERNA", "MINIFIX")
                    else:
                        for lat in (lat_esq, lat_dir):
                            lx, ly = self.converter_global_para_2d_peca(lat, 0.0, cy, meia_esp)
                            lat.adicionar_furo(lx, ly, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")
                            if usa_cavilha:
                                cy_cav = cy + offset_cav if (cy + offset_cav) < (prof_total - 20.0) else (cy - offset_cav)
                                lx_c, ly_c = self.converter_global_para_2d_peca(lat, 0.0, cy_cav, meia_esp)
                                lat.adicionar_furo(lx_c, ly_c, diam_cavilha, prof_cavilha, "FACE_INTERNA", "CAVILHA")
                else:
                    # Na Base Passante, o parafuso entra por baixo da Base Inferior
                    larg_total = base_inf.dimensoes_3d["x"]
                    if usa_minifix:
                        z_tambor_inf = esp_mdf + dist_borda_minifix
                        for lat in (lat_esq, lat_dir):
                            lx, ly = self.converter_global_para_2d_peca(lat, 0.0, cy, z_tambor_inf)
                            lat.adicionar_furo(lx, ly, diam_minifix, prof_minifix, "FACE_INTERNA", "MINIFIX")
                    else:
                        for x_borda in (meia_esp, larg_total - meia_esp):
                            bx, by = self.converter_global_para_2d_peca(base_inf, x_borda, cy, 0.0)
                            base_inf.adicionar_furo(bx, by, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")

                    if usa_cavilha:
                        cy_cav = cy + offset_cav if (cy + offset_cav) < (prof_total - 20.0) else (cy - offset_cav)
                        for x_borda in (meia_esp, larg_total - meia_esp):
                            bx_c, by_c = self.converter_global_para_2d_peca(base_inf, x_borda, cy_cav, 0.0)
                            base_inf.adicionar_furo(bx_c, by_c, diam_cavilha, prof_cavilha, "FACE_INTERNA", "CAVILHA")

        # 1B. União Base Superior (Teto Inteiro) <-> Laterais
        if base_sup and lat_esq and lat_dir:
            larg_total = base_sup.dimensoes_3d["x"]
            prof_total = base_sup.dimensoes_3d["y"]
            z_topo = base_sup.posicao_relativa["pos_z"]
            cotas_y_sup = [recuo_f, prof_total / 2.0, prof_total - recuo_t]

            for cy in cotas_y_sup:
                if usa_minifix:
                    z_tambor_sup = z_topo - dist_borda_minifix
                    for lat in (lat_esq, lat_dir):
                        lx, ly = self.converter_global_para_2d_peca(lat, 0.0, cy, z_tambor_sup)
                        lat.adicionar_furo(lx, ly, diam_minifix, prof_minifix, "FACE_INTERNA", "MINIFIX")
                else:
                    for x_borda in (meia_esp, larg_total - meia_esp):
                        sx, sy = self.converter_global_para_2d_peca(base_sup, x_borda, cy, z_topo)
                        base_sup.adicionar_furo(sx, sy, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")

                if usa_cavilha:
                    cy_cav = cy + offset_cav if (cy + offset_cav) < (prof_total - 20.0) else (cy - offset_cav)
                    for x_borda in (meia_esp, larg_total - meia_esp):
                        sx_c, sy_c = self.converter_global_para_2d_peca(base_sup, x_borda, cy_cav, z_topo)
                        base_sup.adicionar_furo(sx_c, sy_c, diam_cavilha, prof_cavilha, "FACE_INTERNA", "CAVILHA")

        # 1C. Fixação de Sarrafos Deitados (Frontal e Traseiro Deitado)
        for sarrafo in (sarrafo_front, sarrafo_tras_deit):
            if not sarrafo or not lat_esq or not lat_dir:
                continue

            y_ini_s = sarrafo.posicao_relativa["pos_y"]
            larg_s = sarrafo.dimensoes_3d["y"]
            z_meio_s = sarrafo.posicao_relativa["pos_z"] + meia_esp
            cotas_y_sarrafo = [y_ini_s + 20.0, y_ini_s + larg_s - 20.0]

            if usa_minifix:
                larg_s_x = sarrafo.dimensoes_3d["x"]
                for cy in cotas_y_sarrafo:
                    for x_tambor in (dist_borda_minifix, larg_s_x - dist_borda_minifix):
                        sx, sy = self.converter_global_para_2d_peca(
                            sarrafo, sarrafo.posicao_relativa["pos_x"] + x_tambor, cy, z_meio_s
                        )
                        sarrafo.adicionar_furo(sx, sy, diam_minifix, prof_minifix, "FACE_INTERNA", "MINIFIX")
            else:
                for cy in cotas_y_sarrafo:
                    for lat in (lat_esq, lat_dir):
                        lx, ly = self.converter_global_para_2d_peca(lat, 0.0, cy, z_meio_s)
                        lat.adicionar_furo(lx, ly, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")

        # 1D. Fixação de todas as Travessas/Réguas Traseiras EM PÉ nas Laterais
        chaves_travessas_em_pe = [
            "sarrafo_traseiro_em_pe",
            "regua_mao_amiga_movel",
            "travessa_fixacao_aereo",
            "travessa_reforco_torre_sup",
            "travessa_reforco_torre_inf"
        ]
        for chave_t in chaves_travessas_em_pe:
            peca_pe = mapa.get(chave_t)
            if not peca_pe or not lat_esq or not lat_dir:
                continue

            y_meio_pe = peca_pe.posicao_relativa["pos_y"] + meia_esp
            z_ini_pe = peca_pe.posicao_relativa["pos_z"]
            alt_pe = peca_pe.dimensoes_3d["z"]
            cotas_z_pe = [z_ini_pe + 18.0, z_ini_pe + alt_pe - 18.0]

            for cz in cotas_z_pe:
                for lat in (lat_esq, lat_dir):
                    lx, ly = self.converter_global_para_2d_peca(lat, 0.0, y_meio_pe, cz)
                    lat.adicionar_furo(lx, ly, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")

    # =========================================================================
    # 2. VARREDURA RECURSIVA DA ÁRVORE ESPACIAL
    # =========================================================================
    def _furar_arvore_recursiva(self, no: NoEspacial) -> None:
        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        diam_estrutural = float(self.perfil.obter("parametros_usinagem.broca_parafuso_estrutural"))
        diam_guia = float(self.perfil.obter("parametros_usinagem.broca_marcacao_guia"))
        prof_guia = float(self.perfil.obter("parametros_usinagem.profundidade_marcacao_guia"))
        recuo_f = float(self.perfil.obter("parametros_usinagem.recuo_furo_estrutural_frontal"))
        recuo_t = float(self.perfil.obter("parametros_usinagem.recuo_furo_estrutural_traseiro"))

        meia_esp = esp_mdf / 2.0

        # A) Divisória Vertical
        if no.tipo_divisao == "VERTICAL" and no.peca_divisora:
            div = no.peca_divisora
            x_centro_div = div.posicao_relativa["pos_x"] + meia_esp
            y_ini_div = div.posicao_relativa["pos_y"]
            prof_div = div.dimensoes_3d["y"]
            cotas_y_div = [y_ini_div + recuo_f, y_ini_div + (prof_div / 2.0), y_ini_div + prof_div - recuo_t]

            for vizinho_horizontal in (no.vizinhos.get("base"), no.vizinhos.get("topo")):
                if not vizinho_horizontal:
                    continue
                y_min_v = vizinho_horizontal.posicao_relativa["pos_y"]
                y_max_v = y_min_v + vizinho_horizontal.dimensoes_3d["y"]

                for cy in cotas_y_div:
                    if (y_min_v + 10.0) <= cy <= (y_max_v - 10.0):
                        vx, vy = self.converter_global_para_2d_peca(vizinho_horizontal, x_centro_div, cy, 0.0)
                        vizinho_horizontal.adicionar_furo(vx, vy, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")

        # B) Prateleira Fixa ou Livre
        elif no.tipo_divisao == "HORIZONTAL" and no.peca_divisora:
            prat = no.peca_divisora
            eh_fixa = (prat.categoria_industrial == "prateleira_fixa")
            diam_aplicado = diam_estrutural if eh_fixa else diam_guia
            prof_aplicada = esp_mdf if eh_fixa else prof_guia
            face_aplicada = "FACE_EXTERNA" if eh_fixa else "FACE_INTERNA"
            tipo_furo = "ESTRUTURAL" if eh_fixa else "GUIA"

            z_furo_global = prat.posicao_relativa["pos_z"] + (meia_esp if eh_fixa else 0.0)
            y_ini_p = prat.posicao_relativa["pos_y"]
            prof_p = prat.dimensoes_3d["y"]
            cotas_y_prat = [y_ini_p + recuo_f, y_ini_p + prof_p - recuo_t]

            for lado in ("esquerda", "direita"):
                painel_apoio = no.vizinhos.get(lado)
                if not painel_apoio:
                    continue
                for cy in cotas_y_prat:
                    px_2d, py_2d = self.converter_global_para_2d_peca(painel_apoio, 0.0, cy, z_furo_global)
                    painel_apoio.adicionar_furo(px_2d, py_2d, diam_aplicado, prof_aplicada, face_aplicada, tipo_furo)

        # C) Gaveteiro ou Porta-Tempero
        if hasattr(no, "metadados_gaveteiro"):
            self._furar_gaveteiro_ou_tempero(no, getattr(no, "metadados_gaveteiro"))

        # D) Portas de Giro
        if hasattr(no, "metadados_portas"):
            self._furar_portas(getattr(no, "metadados_portas"))

        for filho in no.filhos:
            self._furar_arvore_recursiva(filho)

    # =========================================================================
    # 3. FURAÇÃO DE GAVETEIROS E PORTA-TEMPERO
    # =========================================================================
    def _furar_gaveteiro_ou_tempero(self, no: NoEspacial, lista_itens: list) -> None:
        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        diam_estrutural = float(self.perfil.obter("parametros_usinagem.broca_parafuso_estrutural"))
        diam_guia = float(self.perfil.obter("parametros_usinagem.broca_marcacao_guia"))
        prof_guia = float(self.perfil.obter("parametros_usinagem.profundidade_marcacao_guia"))
        recuo_gav = float(self.perfil.obter("parametros_usinagem.recuo_furo_gaveta"))
        recuo_canal_gav = float(self.perfil.obter("regras_gaveta.recuo_canal_fundo_gaveta"))
        larg_canal = float(self.perfil.obter("parametros_usinagem.largura_canal_fundo"))

        meia_esp = esp_mdf / 2.0

        for item in lista_itens:
            z_trilho = item["z_furo_corredica_global"]
            y_ini = item["y_inicio_trilho"]
            comp_trilho = item["comprimento_trilho"]

            # 3A. Furos guia (3mm) dos trilhos nas Laterais/Divisórias do armário
            cotas_y_trilho = [y_ini + 37.0, y_ini + (comp_trilho / 2.0), y_ini + comp_trilho - 37.0]
            for lado in ("esquerda", "direita"):
                painel_vizinho = no.vizinhos.get(lado)
                if not painel_vizinho:
                    continue
                for cy in cotas_y_trilho:
                    vx, vy = self.converter_global_para_2d_peca(painel_vizinho, 0.0, cy, z_trilho)
                    painel_vizinho.adicionar_furo(vx, vy, diam_guia, prof_guia, "FACE_INTERNA", "GUIA")

            # Se for o carro do Porta-Tempero, fura a estrutura dele e pula a furação de gaveta comum
            if item.get("somente_trilho_lateral"):
                continue

            # 3B. Furos estruturais (4.5mm) nas Laterais de Gaveta prendendo Contra-Frente e Traseira
            for lat_gav in (item["lat_esq"], item["lat_dir"]):
                alt_lat = lat_gav.dim_y_2d
                comp_lat = lat_gav.dim_x_2d

                z_furo_inf_local = round(recuo_canal_gav + larg_canal + 15.0, 2)
                z_furo_sup_local = round(alt_lat - recuo_gav, 2)

                for y_2d in (z_furo_inf_local, z_furo_sup_local):
                    lat_gav.adicionar_furo(meia_esp, y_2d, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")
                    lat_gav.adicionar_furo(comp_lat - meia_esp, y_2d, diam_estrutural, esp_mdf, "FACE_EXTERNA", "ESTRUTURAL")

    # =========================================================================
    # 4. FURAÇÃO DE CANECOS DE DOBRADIÇA (35mm) E CALÇOS NAS LATERAIS
    # =========================================================================
    def _furar_portas(self, lista_portas: list) -> None:
        diam_caneco = float(self.perfil.obter("parametros_usinagem.broca_caneco_dobradica"))
        prof_caneco = float(self.perfil.obter("parametros_usinagem.profundidade_caneco_dobradica"))
        dist_borda_caneco = float(self.perfil.obter("parametros_usinagem.distancia_centro_caneco_borda"))
        recuo_topo_base = float(self.perfil.obter("parametros_usinagem.recuo_dobradica_topo_base"))
        diam_guia = float(self.perfil.obter("parametros_usinagem.broca_marcacao_guia"))
        prof_guia = float(self.perfil.obter("parametros_usinagem.profundidade_marcacao_guia"))

        for item in lista_portas:
            porta: Peca = item["peca_porta"]

            # CASO A: PORTA BASCULANTE (Canecos na borda superior horizontal + Pistão a Gás)
            if item.get("eh_basculante"):
                larg_porta = porta.dim_x_2d
                alt_porta = porta.dim_y_2d
                y_caneco_topo = round(alt_porta - dist_borda_caneco, 2)
                cotas_x_basc = [recuo_topo_base, round(larg_porta - recuo_topo_base, 2)]

                for cx_local in cotas_x_basc:
                    porta.adicionar_furo(cx_local, y_caneco_topo, diam_caneco, prof_caneco, "FACE_INTERNA", "CANECO")

                # Furos guia (3mm) dos pistões a gás nas laterais do vão
                for painel_lat in (item.get("peca_apoio_esq"), item.get("peca_apoio_dir")):
                    if not painel_lat:
                        continue
                    z_pistao = round(porta.posicao_relativa["pos_z"] + alt_porta - 80.0, 2)
                    y_pistao = round(painel_lat.posicao_relativa["pos_y"] + 55.0, 2)
                    z_min_p = painel_lat.posicao_relativa["pos_z"]
                    z_max_p = z_min_p + painel_lat.dimensoes_3d["z"]
                    if z_min_p <= z_pistao <= z_max_p:
                        px, py = self.converter_global_para_2d_peca(painel_lat, 0.0, y_pistao, z_pistao)
                        painel_lat.adicionar_furo(px, py, diam_guia, prof_guia, "FACE_INTERNA", "GUIA")
                continue

            # CASO B: PORTA DE GIRO VERTICAL
            painel_apoio: Peca = item.get("peca_apoio_lateral")
            alt_porta = porta.dim_y_2d
            qtd_dobradicas = self.perfil.calcular_qtd_dobradicas(alt_porta)

            if qtd_dobradicas <= 2:
                cotas_y_porta = [recuo_topo_base, alt_porta - recuo_topo_base]
            else:
                espaco_entre = (alt_porta - (2.0 * recuo_topo_base)) / float(qtd_dobradicas - 1)
                cotas_y_porta = [round(recuo_topo_base + i * espaco_entre, 2) for i in range(qtd_dobradicas)]

            for cy_local in cotas_y_porta:
                porta.adicionar_furo(
                    x=dist_borda_caneco,
                    y=cy_local,
                    diametro=diam_caneco,
                    profundidade=prof_caneco,
                    face="FACE_INTERNA",
                    tipo_furo="CANECO"
                )

                if painel_apoio:
                    z_global_dobradica = porta.posicao_relativa["pos_z"] + cy_local
                    y_global_calco = painel_apoio.posicao_relativa["pos_y"] + 37.0
                    z_min_p = painel_apoio.posicao_relativa["pos_z"]
                    z_max_p = z_min_p + painel_apoio.dimensoes_3d["z"]
                    if z_min_p <= z_global_dobradica <= z_max_p:
                        px, py = self.converter_global_para_2d_peca(painel_apoio, 0.0, y_global_calco, z_global_dobradica)
                        painel_apoio.adicionar_furo(px, py, diam_guia, prof_guia, "FACE_INTERNA", "GUIA")