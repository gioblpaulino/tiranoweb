# =============================================================================
# ARQUIVO: tiranocad_core/construtores/porta_tempero.py
# RESPONSABILIDADE: Construir o Porta-Tempero / Porta-Óleo extraível lendo 100%
# das medidas e nomenclaturas do Perfil JSON, com estrutura colada na Frente.
# =============================================================================

from typing import List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorPortaTempero:
    """
    Construtor paramétrico de Porta-Tempero extraível lateral.
    Zero magic numbers: todas as alturas, folgas e nomes vêm do Perfil JSON.
    """

    TRILHOS_COMERCIAIS_MM = [500.0, 450.0, 400.0, 350.0, 300.0, 250.0]

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_porta_tempero(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial
    ) -> List[Peca]:
        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        folga_corredica = float(self.perfil.obter("regras_gaveta.folga_corredica_cada_lado"))
        folga_traseira = float(self.perfil.obter("regras_gaveta.folga_profundidade_traseira"))
        elevacao_base_z = float(self.perfil.obter("regras_gaveta.elevacao_base_caixote_z"))

        # Parâmetros exclusivos do Porta-Tempero vindos do Perfil JSON
        recuo_estrutura_y = float(self.perfil.obter("regras_porta_tempero.recuo_frontal_estrutura"))
        folga_topo_z = float(self.perfil.obter("regras_porta_tempero.folga_topo_estrutura"))
        alt_guarda_lat = float(self.perfil.obter("regras_porta_tempero.altura_guarda_lateral"))
        fator_nivel_meio = float(self.perfil.obter("regras_porta_tempero.cota_z_prateleira_intermediaria_fator"))
        off_corr_inf_z = float(self.perfil.obter("regras_porta_tempero.offset_corredica_inferior_z"))
        off_corr_sup_topo = float(self.perfil.obter("regras_porta_tempero.offset_corredica_superior_topo_z"))

        modo_frente = str(self.perfil.obter("folgas_frentes.tipo_montagem_frente")).strip().upper()
        gap_sup = float(self.perfil.obter("folgas_frentes.gap_superior"))
        gap_inf = float(self.perfil.obter("folgas_frentes.gap_inferior"))
        gap_esq = float(self.perfil.obter("folgas_frentes.gap_lateral_esquerda"))
        gap_dir = float(self.perfil.obter("folgas_frentes.gap_lateral_direita"))
        gap_entre = float(self.perfil.obter("folgas_frentes.gap_entre_frentes"))
        afast_frontal = float(self.perfil.obter("folgas_frentes.afastamento_frontal_caixa"))

        tem_veio_frente = not any(c in mat_frente.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        prof_max_permitida = vao_alvo.profundidade - recuo_estrutura_y - folga_traseira
        prof_quadro = next((t for t in self.TRILHOS_COMERCIAIS_MM if t <= prof_max_permitida), 0.0)
        if prof_quadro <= 0.0:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade do '{vao_alvo.nome_vao}' ({vao_alvo.profundidade}mm) insuficiente para Porta-Tempero."
            )

        pecas_geradas: List[Peca] = []

        # 1. FRENTE EXTERNA DO PORTA-TEMPERO
        if modo_frente == "EMBUTIDA":
            larg_frente = round(vao_alvo.largura - gap_esq - gap_dir, 2)
            alt_frente = round(vao_alvo.altura - gap_inf - gap_sup, 2)
            x_frente = round(vao_alvo.x + gap_esq, 2)
            y_frente = round(vao_alvo.y, 2)
            z_frente = round(vao_alvo.z + gap_inf, 2)
        else:
            viz_esq = vao_alvo.vizinhos.get("esquerda")
            viz_dir = vao_alvo.vizinhos.get("direita")
            eh_div_esq = viz_esq is not None and "divisoria" in viz_esq.categoria_industrial
            eh_div_dir = viz_dir is not None and "divisoria" in viz_dir.categoria_industrial

            cob_esq = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_esq else (esp_caixa - gap_esq)
            cob_dir = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_dir else (esp_caixa - gap_dir)
            cob_inf = esp_caixa - gap_inf
            cob_sup = esp_caixa - gap_sup

            larg_frente = round(vao_alvo.largura + cob_esq + cob_dir, 2)
            alt_frente = round(vao_alvo.altura + cob_inf + cob_sup, 2)
            x_frente = round(vao_alvo.x - cob_esq, 2)
            y_frente = round(vao_alvo.y - esp_frente - afast_frontal, 2)
            z_frente = round(vao_alvo.z - cob_inf, 2)

        frente_pt = Peca(
            categoria_industrial="frente_porta_tempero",
            nome_comercial=self.perfil.obter_nome_peca("frente_porta_tempero"),
            dim_3d=(larg_frente, esp_frente, alt_frente),
            pos_3d=(x_frente, y_frente, z_frente),
            material=mat_frente,
            id_pai=id_modulo,
            tem_veio=tem_veio_frente
        )
        frente_pt.fitas.topo = frente_pt.fitas.base = frente_pt.fitas.esquerda = frente_pt.fitas.direita = True
        pecas_geradas.append(frente_pt)

        # 2. COLUNAS VERTICAIS FRONTAL E TRASEIRA (Encostadas na Frente em Y = vao_alvo.y!)
        larg_util_interna = round(vao_alvo.largura - (2.0 * folga_corredica), 2)
        alt_quadro = round(vao_alvo.altura - elevacao_base_z - folga_topo_z, 2)
        x_quadro = round(vao_alvo.x + folga_corredica, 2)
        y_ini = round(vao_alvo.y + recuo_estrutura_y, 2)
        z_ini = round(vao_alvo.z + elevacao_base_z, 2)

        col_frontal = Peca(
            categoria_industrial="contra_frente_gaveta",
            nome_comercial=self.perfil.obter_nome_peca("coluna_frontal_porta_tempero"),
            dim_3d=(larg_util_interna, esp_caixa, alt_quadro),
            pos_3d=(x_quadro, y_ini, z_ini),
            material=mat_caixa,
            id_pai=id_modulo
        )
        col_frontal.fitas.topo = col_frontal.fitas.esquerda = col_frontal.fitas.direita = True

        col_traseira = Peca(
            categoria_industrial="traseira_gaveta",
            nome_comercial=self.perfil.obter_nome_peca("coluna_traseira_porta_tempero"),
            dim_3d=(larg_util_interna, esp_caixa, alt_quadro),
            pos_3d=(x_quadro, round(y_ini + prof_quadro - esp_caixa, 2), z_ini),
            material=mat_caixa,
            id_pai=id_modulo
        )
        col_traseira.fitas.topo = col_traseira.fitas.esquerda = col_traseira.fitas.direita = True
        pecas_geradas.extend([col_frontal, col_traseira])

        # 3. DOIS NÍVEIS DE BANDEJAS + GUARDAS LATERAIS (Com medidas e nomes do Perfil JSON)
        comp_bandeja_y = round(prof_quadro - (2.0 * esp_caixa), 2)
        larg_base_interna = round(larg_util_interna - (2.0 * esp_caixa), 2)
        y_bandeja = round(y_ini + esp_caixa, 2)

        cotas_z_niveis = [z_ini, round(z_ini + (alt_quadro * fator_nivel_meio), 2)]
        nome_base_nivel = self.perfil.obter_nome_peca("base_nivel_porta_tempero")
        nome_guarda_esq = self.perfil.obter_nome_peca("guarda_lateral_porta_tempero_esq")
        nome_guarda_dir = self.perfil.obter_nome_peca("guarda_lateral_porta_tempero_dir")

        # Lê o vãozinho livre entre a base do nível e a guarda lateral (ex: 15mm)
        vao_livre_guarda_z = float(self.perfil.obter("regras_porta_tempero.vao_livre_abaixo_guarda_z"))

        lista_guardas_esq: List[Peca] = []
        lista_guardas_dir: List[Peca] = []
        cotas_z_eixo_corredica: List[float] = []

        for idx, z_nivel in enumerate(cotas_z_niveis):
            num_n = idx + 1
            base_nivel = Peca(
                categoria_industrial="prateleira_interna_tempero",
                nome_comercial=f"{nome_base_nivel} {num_n}",
                dim_3d=(larg_base_interna + esp_caixa * 2.0, comp_bandeja_y, esp_caixa),
                pos_3d=(round(x_quadro, 2), y_bandeja, z_nivel),
                material=mat_caixa,
                id_pai=id_modulo
            )

            base_nivel.fitas.esquerda = base_nivel.fitas.direita = True
            
            # A guarda sobe acima da base_nivel (esp_caixa) + o vãozinho livre configurado!
            z_guarda = round(z_nivel + esp_caixa + vao_livre_guarda_z, 2)

            # O eixo da corrediça telescópica acompanha exatamente o MEIO da altura da guarda!
            z_centro_trilho = round(z_guarda + (alt_guarda_lat / 2.0), 2)
            cotas_z_eixo_corredica.append(z_centro_trilho)

            guarda_esq = Peca(
                categoria_industrial="lateral_gaveta_esquerda",
                nome_comercial=f"{nome_guarda_esq} {num_n}",
                dim_3d=(esp_caixa, comp_bandeja_y, alt_guarda_lat),
                pos_3d=(x_quadro, y_bandeja, z_guarda),
                material=mat_caixa,
                id_pai=id_modulo,
                espelhar_cam_x=False
            )
            guarda_esq.fitas.topo = True
            if vao_livre_guarda_z > 0:
                guarda_esq.fitas.base = True  # Se tem vão livre embaixo, fita a base da guarda também!

            guarda_dir = Peca(
                categoria_industrial="lateral_gaveta_direita",
                nome_comercial=f"{nome_guarda_dir} {num_n}",
                dim_3d=(esp_caixa, comp_bandeja_y, alt_guarda_lat),
                pos_3d=(round(x_quadro + larg_util_interna - esp_caixa, 2), y_bandeja, z_guarda),
                material=mat_caixa,
                id_pai=id_modulo,
                espelhar_cam_x=True
            )
            guarda_dir.fitas.topo = True
            if vao_livre_guarda_z > 0:
                guarda_dir.fitas.base = True

            lista_guardas_esq.append(guarda_esq)
            lista_guardas_dir.append(guarda_dir)
            pecas_geradas.extend([base_nivel, guarda_esq, guarda_dir])

        vao_alvo.ocupacao_interna = "PORTA_TEMPERO"
        vao_alvo.pecas_internas.extend(pecas_geradas)
        setattr(vao_alvo, "metadados_gaveteiro", [
            {
                "indice_gaveta": 1,
                "z_furo_corredica_global": cotas_z_eixo_corredica[0],
                "y_inicio_trilho": y_ini,
                "comprimento_trilho": prof_quadro,
                "lat_esq": lista_guardas_esq[0],
                "lat_dir": lista_guardas_dir[0],
                "ctrf": col_frontal,
                "traseira": col_traseira,
                "frente": frente_pt
            },
            {
                "indice_gaveta": 2,
                "z_furo_corredica_global": cotas_z_eixo_corredica[1],
                "y_inicio_trilho": y_ini,
                "comprimento_trilho": prof_quadro,
                "lat_esq": lista_guardas_esq[1],
                "lat_dir": lista_guardas_dir[1],
                "ctrf": col_frontal,
                "traseira": col_traseira,
                "frente": frente_pt
            }
        ])

        return pecas_geradas