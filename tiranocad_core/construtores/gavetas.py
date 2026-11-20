# =============================================================================
# ARQUIVO: tiranocad_core/construtores/gavetas.py
# RESPONSABILIDADE: Construir Gaveteiros Externos, Gaveteiros Internos e
# Sapateiras Corrediças 100% Data-Driven pelo Perfil JSON.
# =============================================================================

from typing import Any, Dict, List, Optional
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorGavetas:
    """
    Especialista na fabricação paramétrica de gavetas externas, internas e sapateiras.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    @staticmethod
    def _resolver_alturas_customizadas(
        quantidade: int,
        altura_total_disponivel: float,
        alturas_custom: Optional[List[Optional[float]]] = None,
        altura_minima_item: float = 70.0
    ) -> List[float]:
        """
        Distribui a altura disponível entre N gavetas.
        Itens com valor > 0 ficam travados na medida informada;
        itens com 0 ou None ('Auto') dividem igualmente o espaço restante.
        """
        if not alturas_custom:
            return [round(altura_total_disponivel / float(quantidade), 2)] * quantidade

        # Normaliza o tamanho da lista para bater com a quantidade de gavetas
        lista_norm: List[float] = []
        for i in range(quantidade):
            val = alturas_custom[i] if i < len(alturas_custom) else 0.0
            lista_norm.append(float(val) if val and float(val) > 0.0 else 0.0)

        soma_fixas = sum(h for h in lista_norm if h > 0.0)
        qtd_autos = sum(1 for h in lista_norm if h <= 0.0)

        if qtd_autos == 0:
            if abs(soma_fixas - altura_total_disponivel) > 2.0:
                raise ErroGeometriaCAD(
                    f"🚨 [ALTURAS DE GAVETA] A soma das alturas fixas ({soma_fixas:.1f}mm) "
                    f"não bate com o espaço disponível ({altura_total_disponivel:.1f}mm). "
                    f"Deixe pelo menos 1 gaveta em 0 (Auto) para absorver a diferença!"
                )
            return [round(h, 2) for h in lista_norm]

        restante = altura_total_disponivel - soma_fixas
        altura_cada_auto = round(restante / float(qtd_autos), 2)

        if altura_cada_auto < altura_minima_item:
            raise ErroGeometriaCAD(
                f"🚨 [ALTURAS DE GAVETA] Sobrou apenas {altura_cada_auto:.1f}mm para cada gaveta Auto "
                f"(mínimo permitido: {altura_minima_item:.0f}mm). Reduza as alturas fixas ou a quantidade."
            )

        return [round(h, 2) if h > 0.0 else altura_cada_auto for h in lista_norm]
    
    def construir_gaveteiro(
     self,
     id_modulo: str,
     vao_alvo: NoEspacial,
     quantidade_gavetas: int,
     alturas_custom: Optional[List[Optional[float]]] = None
 ) -> List[Peca]:
        """Constrói bateria de gavetas com frentes externas (Sobrepostas ou Embutidas)."""
        if quantidade_gavetas <= 0:
            return []

        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        esp_fundo = float(self.perfil.obter("materiais_padrao.espessura_fundo_mm"))

        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))
        mat_fundo = str(self.perfil.obter("materiais_padrao.material_fundo"))

        modo_frente = str(self.perfil.obter("folgas_frentes.tipo_montagem_frente")).strip().upper()
        gap_sup = float(self.perfil.obter("folgas_frentes.gap_superior"))
        gap_inf = float(self.perfil.obter("folgas_frentes.gap_inferior"))
        gap_esq = float(self.perfil.obter("folgas_frentes.gap_lateral_esquerda"))
        gap_dir = float(self.perfil.obter("folgas_frentes.gap_lateral_direita"))
        gap_entre = float(self.perfil.obter("folgas_frentes.gap_entre_frentes"))
        afast_frontal = float(self.perfil.obter("folgas_frentes.afastamento_frontal_caixa"))

        trilhos_comerciais = [float(t) for t in self.perfil.obter("regras_gaveta.trilhos_comerciais_mm")]
        folga_corredica = float(self.perfil.obter("regras_gaveta.folga_corredica_cada_lado"))
        recuo_caixote = float(self.perfil.obter("regras_gaveta.recuo_frontal_caixote"))
        folga_prof_traseira = float(self.perfil.obter("regras_gaveta.folga_profundidade_traseira"))
        folga_alt_caixote = float(self.perfil.obter("regras_gaveta.folga_altura_caixote"))
        rebaixo_ctrf_tras = float(self.perfil.obter("regras_gaveta.rebaixo_contra_frente_traseira"))
        elevacao_base_z = float(self.perfil.obter("regras_gaveta.elevacao_base_caixote_z"))
        offset_corredica_z = float(self.perfil.obter("regras_gaveta.offset_eixo_corredica_z"))
        recuo_canal_gav = float(self.perfil.obter("regras_gaveta.recuo_canal_fundo_gaveta"))

        larg_canal = float(self.perfil.obter("parametros_usinagem.largura_canal_fundo"))
        prof_canal = float(self.perfil.obter("parametros_usinagem.profundidade_canal_fundo"))
        margem_canal_gav = float(self.perfil.obter("parametros_usinagem.margem_furo_acima_canal_gaveta"))
        folga_encaixe_fundo = float(self.perfil.obter("geometria_caixaria.folga_encaixe_fundo"))

        tem_veio_caixa = self.perfil.material_possui_veio(mat_caixa)
        tem_veio_frente = self.perfil.material_possui_veio(mat_frente)

        prof_max_permitida = vao_alvo.profundidade - recuo_caixote - folga_prof_traseira
        prof_caixote = next((t for t in sorted(trilhos_comerciais, reverse=True) if t <= prof_max_permitida), 0.0)
        if prof_caixote <= 0.0:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade do '{vao_alvo.nome_vao}' ({vao_alvo.profundidade}mm) não comporta corrediça comercial."
            )

        viz_esq = vao_alvo.vizinhos.get("esquerda")
        viz_dir = vao_alvo.vizinhos.get("direita")
        eh_div_esq = viz_esq is not None and "divisoria" in viz_esq.categoria_industrial
        eh_div_dir = viz_dir is not None and "divisoria" in viz_dir.categoria_industrial

        if modo_frente == "EMBUTIDA":
            cob_esq, cob_dir, cob_inf, cob_sup = -gap_esq, -gap_dir, -gap_inf, -gap_sup
            y_frente_pos = round(vao_alvo.y, 2)
        else:
            cob_esq = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_esq else (esp_caixa - gap_esq)
            cob_dir = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_dir else (esp_caixa - gap_dir)
            cob_inf = esp_caixa - gap_inf
            cob_sup = esp_caixa - gap_sup
            y_frente_pos = round(vao_alvo.y - esp_frente - afast_frontal, 2)

        largura_frente = round(vao_alvo.largura + cob_esq + cob_dir, 2)
        altura_total_cobertura = vao_alvo.altura + cob_inf + cob_sup
        soma_gaps_internos = (quantidade_gavetas - 1) * gap_entre
        altura_liquida_frentes = round(altura_total_cobertura - soma_gaps_internos, 2)

        alturas_frentes = self._resolver_alturas_customizadas(
            quantidade_gavetas, altura_liquida_frentes, alturas_custom
        )
        soma_frentes = sum(alturas_frentes)
        alturas_nichos = [round(vao_alvo.altura * (hf / soma_frentes), 2) for hf in alturas_frentes]

        altura_nicho_unitario = vao_alvo.altura / float(quantidade_gavetas)
        altura_lateral_gav = round(altura_nicho_unitario - folga_alt_caixote, 2)
        altura_traseira_ctrf = round(altura_lateral_gav - rebaixo_ctrf_tras, 2)

        if altura_traseira_ctrf <= (recuo_canal_gav + larg_canal + margem_canal_gav):
            raise ErroGeometriaCAD(
                f"🚨 As {quantidade_gavetas} gavetas ficaram baixas demais ({altura_lateral_gav}mm) para o vão ({vao_alvo.altura}mm)."
            )

        largura_ctrf_traseira = round(vao_alvo.largura - (2.0 * folga_corredica) - (2.0 * esp_caixa), 2)
        penetracao_fundo = prof_canal - folga_encaixe_fundo
        larg_fundo_gav = round(largura_ctrf_traseira + (2.0 * penetracao_fundo), 2)
        prof_fundo_gav = round(prof_caixote - (2.0 * esp_caixa) + (2.0 * penetracao_fundo), 2)

        pecas_gaveteiro: List[Peca] = []
        metadados_corredicas: List[Dict[str, Any]] = []

        z_cursor_nicho = vao_alvo.z
        z_cursor_frente = vao_alvo.z - cob_inf

        for i in range(quantidade_gavetas):
            num_gav = i + 1
            altura_frente = alturas_frentes[i]
            altura_nicho_unitario = alturas_nichos[i]

            altura_lateral_gav = round(altura_nicho_unitario - folga_alt_caixote, 2)
            altura_traseira_ctrf = round(altura_lateral_gav - rebaixo_ctrf_tras, 2)

            if altura_traseira_ctrf <= (recuo_canal_gav + larg_canal + margem_canal_gav):
                raise ErroGeometriaCAD(
                    f"🚨 A gaveta {num_gav} ficou baixa demais ({altura_lateral_gav}mm) para o rasgo de fundo."
                )

            z_base_nicho = z_cursor_nicho
            z_base_caixote = round(z_base_nicho + elevacao_base_z, 2)
            y_inicio_caixote = round(vao_alvo.y + recuo_caixote, 2)

            z_frente = round(z_cursor_frente, 2)
            x_frente = round(vao_alvo.x - cob_esq, 2)

            # Avança os cursores para a próxima gaveta acima
            z_cursor_nicho += altura_nicho_unitario
            z_cursor_frente += altura_frente + gap_entre

            frente_gav = Peca(
                categoria_industrial="frente_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('frente_gaveta')} {num_gav}",
                dim_3d=(largura_frente, esp_frente, altura_frente),
                pos_3d=(x_frente, y_frente_pos, z_frente),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente
            )
            frente_gav.fitas.base = frente_gav.fitas.direita = frente_gav.fitas.topo = frente_gav.fitas.esquerda = True
            pecas_gaveteiro.append(frente_gav)

            x_lat_esq_gav = round(vao_alvo.x + folga_corredica, 2)
            lat_esq_gav = Peca(
                categoria_industrial="lateral_gaveta_esquerda",
                nome_comercial=f"{self.perfil.obter_nome_peca('lateral_gaveta_esquerda')} {num_gav}",
                dim_3d=(esp_caixa, prof_caixote, altura_lateral_gav),
                pos_3d=(x_lat_esq_gav, y_inicio_caixote, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=False
            )
            lat_esq_gav.fitas.topo = True
            lat_esq_gav.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, prof_caixote, prof_canal, "H", "CANAL_FUNDO")
            pecas_gaveteiro.append(lat_esq_gav)

            x_lat_dir_gav = round(vao_alvo.x + vao_alvo.largura - folga_corredica - esp_caixa, 2)
            lat_dir_gav = Peca(
                categoria_industrial="lateral_gaveta_direita",
                nome_comercial=f"{self.perfil.obter_nome_peca('lateral_gaveta_direita')} {num_gav}",
                dim_3d=(esp_caixa, prof_caixote, altura_lateral_gav),
                pos_3d=(x_lat_dir_gav, y_inicio_caixote, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=True
            )
            lat_dir_gav.fitas.topo = True
            lat_dir_gav.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, prof_caixote, prof_canal, "H", "CANAL_FUNDO")
            pecas_gaveteiro.append(lat_dir_gav)

            x_interno_gav = round(x_lat_esq_gav + esp_caixa, 2)
            ctrf_gav = Peca(
                categoria_industrial="contra_frente_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('contra_frente_gaveta')} {num_gav}",
                dim_3d=(largura_ctrf_traseira, esp_caixa, altura_traseira_ctrf),
                pos_3d=(x_interno_gav, y_inicio_caixote, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            ctrf_gav.fitas.topo = True
            ctrf_gav.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, largura_ctrf_traseira, prof_canal, "H", "CANAL_FUNDO")
            pecas_gaveteiro.append(ctrf_gav)

            y_traseira_gav = round(y_inicio_caixote + prof_caixote - esp_caixa, 2)
            tras_gav = Peca(
                categoria_industrial="traseira_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('traseira_gaveta')} {num_gav}",
                dim_3d=(largura_ctrf_traseira, esp_caixa, altura_traseira_ctrf),
                pos_3d=(x_interno_gav, y_traseira_gav, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            tras_gav.fitas.topo = True
            tras_gav.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, largura_ctrf_traseira, prof_canal, "H", "CANAL_FUNDO")
            pecas_gaveteiro.append(tras_gav)

            fundo_gav = Peca(
                categoria_industrial="fundo_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('fundo_gaveta')} {num_gav}",
                dim_3d=(larg_fundo_gav, prof_fundo_gav, esp_fundo),
                pos_3d=(
                    round(x_interno_gav - penetracao_fundo, 2),
                    round(y_inicio_caixote + esp_caixa - penetracao_fundo, 2),
                    round(z_base_caixote + recuo_canal_gav, 2)
                ),
                material=mat_fundo,
                id_pai=id_modulo
            )
            pecas_gaveteiro.append(fundo_gav)

            metadados_corredicas.append({
                "indice_gaveta": num_gav,
                "z_furo_corredica_global": round(z_base_nicho + offset_corredica_z, 2),
                "y_inicio_trilho": y_inicio_caixote,
                "comprimento_trilho": prof_caixote,
                "lat_esq": lat_esq_gav,
                "lat_dir": lat_dir_gav,
                "ctrf": ctrf_gav,
                "traseira": tras_gav,
                "frente": frente_gav
            })

        vao_alvo.ocupacao_interna = "GAVETEIRO"
        vao_alvo.pecas_internas.extend(pecas_gaveteiro)
        setattr(vao_alvo, "metadados_gaveteiro", metadados_corredicas)
        return pecas_gaveteiro

    def construir_gaveteiro_interno(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        quantidade_gavetas: int,
        alturas_custom: Optional[List[Optional[float]]] = None
    ) -> List[Peca]:
        """Constrói Gavetas Internas recuadas com espaçadores laterais para dobradiças."""
        if quantidade_gavetas <= 0:
            return []

        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        esp_fundo = float(self.perfil.obter("materiais_padrao.espessura_fundo_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_fundo = str(self.perfil.obter("materiais_padrao.material_fundo"))

        trilhos_comerciais = [float(t) for t in self.perfil.obter("regras_gaveta.trilhos_comerciais_mm")]
        folga_corredica = float(self.perfil.obter("regras_gaveta.folga_corredica_cada_lado"))
        folga_prof_traseira = float(self.perfil.obter("regras_gaveta.folga_profundidade_traseira"))
        rebaixo_ctrf_tras = float(self.perfil.obter("regras_gaveta.rebaixo_contra_frente_traseira"))
        elevacao_base_z = float(self.perfil.obter("regras_gaveta.elevacao_base_caixote_z"))
        offset_corredica_z = float(self.perfil.obter("regras_gaveta.offset_eixo_corredica_z"))
        recuo_canal_gav = float(self.perfil.obter("regras_gaveta.recuo_canal_fundo_gaveta"))

        recuo_frontal_int = float(self.perfil.obter("regras_gaveta.recuo_frontal_gaveta_interna"))
        esp_engrosso = float(self.perfil.obter("regras_gaveta.espessura_engrosso_gaveta_interna"))
        vao_puxador = float(self.perfil.obter("regras_gaveta.vao_puxador_gaveta_interna"))
        folga_lat_frente_int = float(self.perfil.obter("regras_gaveta.folga_lateral_frente_interna"))
        dif_alt_lat_int = float(self.perfil.obter("regras_gaveta.diferenca_altura_lateral_interna"))
        elev_frente_int_z = float(self.perfil.obter("regras_gaveta.elevacao_frente_interna_z"))

        larg_canal = float(self.perfil.obter("parametros_usinagem.largura_canal_fundo"))
        prof_canal = float(self.perfil.obter("parametros_usinagem.profundidade_canal_fundo"))
        margem_canal_gav = float(self.perfil.obter("parametros_usinagem.margem_furo_acima_canal_gaveta"))
        folga_encaixe_fundo = float(self.perfil.obter("geometria_caixaria.folga_encaixe_fundo"))

        tem_veio_caixa = self.perfil.material_possui_veio(mat_caixa)

        prof_max = vao_alvo.profundidade - recuo_frontal_int - esp_frente - folga_prof_traseira
        prof_caixote = next((t for t in sorted(trilhos_comerciais, reverse=True) if t <= prof_max), 0.0)
        if prof_caixote <= 0.0:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade do '{vao_alvo.nome_vao}' ({vao_alvo.profundidade}mm) insuficiente para Gaveta Interna."
            )

        pecas_geradas: List[Peca] = []
        metadados_corredicas: List[Dict[str, Any]] = []

        y_ini_caixote = round(vao_alvo.y + recuo_frontal_int + esp_frente, 2)
        for eh_dir, cat_eng, x_eng in (
            (False, "engrosso_gaveta_interna_esq", vao_alvo.x),
            (True, "engrosso_gaveta_interna_dir", vao_alvo.x + vao_alvo.largura - esp_engrosso)
        ):
            engrosso = Peca(
                categoria_industrial=cat_eng,
                nome_comercial=self.perfil.obter_nome_peca(cat_eng),
                dim_3d=(esp_engrosso, prof_caixote, vao_alvo.altura),
                pos_3d=(x_eng, y_ini_caixote, vao_alvo.z),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=eh_dir
            )
            engrosso.fitas.esquerda = True
            pecas_geradas.append(engrosso)

        larg_util_entre_engrossos = round(vao_alvo.largura - (2.0 * esp_engrosso), 2)
        x_util_inicio = round(vao_alvo.x + esp_engrosso, 2)

        largura_frente_int = round(larg_util_entre_engrossos - (2.0 * folga_lat_frente_int), 2)
        altura_nicho = vao_alvo.altura / float(quantidade_gavetas)
        altura_frente_int = round(altura_nicho - vao_puxador, 2)
        altura_lateral_gav = round(altura_frente_int - dif_alt_lat_int, 2)
        altura_traseira_ctrf = round(altura_lateral_gav - rebaixo_ctrf_tras, 2)

        if altura_traseira_ctrf <= (recuo_canal_gav + larg_canal + margem_canal_gav):
            raise ErroGeometriaCAD(
                f"🚨 As {quantidade_gavetas} gavetas internas ficaram baixas demais para o vão ({vao_alvo.altura}mm)."
            )

        largura_ctrf_traseira = round(larg_util_entre_engrossos - (2.0 * folga_corredica) - (2.0 * esp_caixa), 2)
        penetracao = prof_canal - folga_encaixe_fundo
        larg_fundo_gav = round(largura_ctrf_traseira + (2.0 * penetracao), 2)
        prof_fundo_gav = round(prof_caixote - (2.0 * esp_caixa) + (2.0 * penetracao), 2)

        alturas_nichos = self._resolver_alturas_customizadas(
         quantidade_gavetas, vao_alvo.altura, alturas_custom
        )
        z_cursor_nicho = vao_alvo.z
     
        for i in range(quantidade_gavetas):
            altura_nicho = alturas_nichos[i]
            altura_frente_int = round(altura_nicho - vao_puxador, 2)
            altura_lateral_gav = round(altura_frente_int - dif_alt_lat_int, 2)
            altura_traseira_ctrf = round(altura_lateral_gav - rebaixo_ctrf_tras, 2)

            if altura_traseira_ctrf <= (recuo_canal_gav + larg_canal + margem_canal_gav):
                raise ErroGeometriaCAD(
                    f"🚨 A gaveta interna {num_gav} ficou baixa demais para o rasgo de fundo."
                )

            z_base_nicho = z_cursor_nicho
            z_base_caixote = round(z_base_nicho + elevacao_base_z, 2)
            z_cursor_nicho += altura_nicho
            num_gav = i + 1
            z_base_nicho = vao_alvo.z + (i * altura_nicho)
            z_base_caixote = round(z_base_nicho + elevacao_base_z, 2)

            frente_int = Peca(
                categoria_industrial="frente_gaveta_interna",
                nome_comercial=f"{self.perfil.obter_nome_peca('frente_gaveta_interna')} {num_gav}",
                dim_3d=(largura_frente_int, esp_frente, altura_frente_int),
                pos_3d=(
                    round(x_util_inicio + folga_lat_frente_int, 2),
                    round(vao_alvo.y + recuo_frontal_int, 2),
                    round(z_base_nicho + elev_frente_int_z, 2)
                ),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            frente_int.fitas.base = frente_int.fitas.direita = frente_int.fitas.topo = frente_int.fitas.esquerda = True
            pecas_geradas.append(frente_int)

            x_lat_esq = round(x_util_inicio + folga_corredica, 2)
            x_lat_dir = round(x_util_inicio + larg_util_entre_engrossos - folga_corredica - esp_caixa, 2)
            x_interno = round(x_lat_esq + esp_caixa, 2)

            lat_esq = Peca(
                categoria_industrial="lateral_gaveta_esquerda",
                nome_comercial=f"{self.perfil.obter_nome_peca('lateral_gaveta_esquerda')} Int. {num_gav}",
                dim_3d=(esp_caixa, prof_caixote, altura_lateral_gav),
                pos_3d=(x_lat_esq, y_ini_caixote, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=False
            )
            lat_esq.fitas.topo = True
            lat_esq.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, prof_caixote, prof_canal, "H", "CANAL_FUNDO")

            lat_dir = Peca(
                categoria_industrial="lateral_gaveta_direita",
                nome_comercial=f"{self.perfil.obter_nome_peca('lateral_gaveta_direita')} Int. {num_gav}",
                dim_3d=(esp_caixa, prof_caixote, altura_lateral_gav),
                pos_3d=(x_lat_dir, y_ini_caixote, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=True
            )
            lat_dir.fitas.topo = True
            lat_dir.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, prof_caixote, prof_canal, "H", "CANAL_FUNDO")

            ctrf = Peca(
                categoria_industrial="contra_frente_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('contra_frente_gaveta')} Int. {num_gav}",
                dim_3d=(largura_ctrf_traseira, esp_caixa, altura_traseira_ctrf),
                pos_3d=(x_interno, y_ini_caixote, z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            ctrf.fitas.topo = True
            ctrf.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, largura_ctrf_traseira, prof_canal, "H", "CANAL_FUNDO")

            tras = Peca(
                categoria_industrial="traseira_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('traseira_gaveta')} Int. {num_gav}",
                dim_3d=(largura_ctrf_traseira, esp_caixa, altura_traseira_ctrf),
                pos_3d=(x_interno, round(y_ini_caixote + prof_caixote - esp_caixa, 2), z_base_caixote),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            tras.fitas.topo = True
            tras.adicionar_rasgo(0.0, recuo_canal_gav, larg_canal, largura_ctrf_traseira, prof_canal, "H", "CANAL_FUNDO")

            fundo = Peca(
                categoria_industrial="fundo_gaveta",
                nome_comercial=f"{self.perfil.obter_nome_peca('fundo_gaveta')} Int. {num_gav}",
                dim_3d=(larg_fundo_gav, prof_fundo_gav, esp_fundo),
                pos_3d=(round(x_interno - penetracao, 2), round(y_ini_caixote + esp_caixa - penetracao, 2), round(z_base_caixote + recuo_canal_gav, 2)),
                material=mat_fundo,
                id_pai=id_modulo
            )

            pecas_geradas.extend([lat_esq, lat_dir, ctrf, tras, fundo])
            metadados_corredicas.append({
                "indice_gaveta": num_gav,
                "z_furo_corredica_global": round(z_base_nicho + offset_corredica_z, 2),
                "y_inicio_trilho": y_ini_caixote,
                "comprimento_trilho": prof_caixote,
                "lat_esq": lat_esq,
                "lat_dir": lat_dir,
                "ctrf": ctrf,
                "traseira": tras,
                "frente": frente_int
            })

        vao_alvo.ocupacao_interna = "GAVETEIRO_INTERNO"
        vao_alvo.pecas_internas.extend(pecas_geradas)
        setattr(vao_alvo, "metadados_gaveteiro", metadados_corredicas)
        return pecas_geradas

    def construir_sapateira(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        quantidade_sapateiras: int
    ) -> List[Peca]:
        """Constrói Bandejas Sapateiras Extraíveis com medidas 100% do Perfil JSON."""
        if quantidade_sapateiras <= 0:
            return []

        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_fundo = float(self.perfil.obter("materiais_padrao.espessura_fundo_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_fundo = str(self.perfil.obter("materiais_padrao.material_fundo"))

        trilhos_comerciais = [float(t) for t in self.perfil.obter("regras_gaveta.trilhos_comerciais_mm")]
        folga_corredica = float(self.perfil.obter("regras_gaveta.folga_corredica_cada_lado"))
        folga_traseira = float(self.perfil.obter("regras_gaveta.folga_profundidade_traseira"))
        rebaixo_ctrf_tras = float(self.perfil.obter("regras_gaveta.rebaixo_contra_frente_traseira"))
        recuo_sap = float(self.perfil.obter("regras_gaveta.recuo_frontal_sapateira"))
        alt_lat_sap = float(self.perfil.obter("regras_gaveta.altura_lateral_sapateira"))
        elev_base_sap_z = float(self.perfil.obter("regras_gaveta.elevacao_base_sapateira_z"))
        recuo_canal = float(self.perfil.obter("regras_gaveta.recuo_canal_fundo_gaveta"))
        offset_corredica_z = float(self.perfil.obter("regras_gaveta.offset_eixo_corredica_z"))

        larg_canal = float(self.perfil.obter("parametros_usinagem.largura_canal_fundo"))
        prof_canal = float(self.perfil.obter("parametros_usinagem.profundidade_canal_fundo"))
        folga_fundo = float(self.perfil.obter("geometria_caixaria.folga_encaixe_fundo"))

        tem_veio_caixa = self.perfil.material_possui_veio(mat_caixa)

        prof_max = vao_alvo.profundidade - recuo_sap - folga_traseira
        prof_bandeja = next((t for t in sorted(trilhos_comerciais, reverse=True) if t <= prof_max), 0.0)
        if prof_bandeja <= 0.0:
            raise ErroGeometriaCAD(f"🚨 Profundidade insuficiente no '{vao_alvo.nome_vao}' para Sapateira.")

        altura_nicho = vao_alvo.altura / float(quantidade_sapateiras)
        larg_interna = round(vao_alvo.largura - (2.0 * folga_corredica) - (2.0 * esp_caixa), 2)
        penetracao = prof_canal - folga_fundo

        pecas_geradas: List[Peca] = []
        metadados_corredicas: List[Dict[str, Any]] = []

        for i in range(quantidade_sapateiras):
            num_s = i + 1
            z_base = round(vao_alvo.z + (i * altura_nicho) + elev_base_sap_z, 2)
            y_ini = round(vao_alvo.y + recuo_sap, 2)
            x_esq = round(vao_alvo.x + folga_corredica, 2)
            x_dir = round(vao_alvo.x + vao_alvo.largura - folga_corredica - esp_caixa, 2)
            x_meio = round(x_esq + esp_caixa, 2)

            lat_esq = Peca(
                categoria_industrial="lateral_sapateira_esquerda",
                nome_comercial=f"{self.perfil.obter_nome_peca('lateral_sapateira_esquerda')} {num_s}",
                dim_3d=(esp_caixa, prof_bandeja, alt_lat_sap),
                pos_3d=(x_esq, y_ini, z_base),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=False
            )
            lat_esq.fitas.topo = lat_esq.fitas.esquerda = True
            lat_esq.adicionar_rasgo(0.0, recuo_canal, larg_canal, prof_bandeja, prof_canal, "H", "CANAL_FUNDO")

            lat_dir = Peca(
                categoria_industrial="lateral_sapateira_direita",
                nome_comercial=f"{self.perfil.obter_nome_peca('lateral_sapateira_direita')} {num_s}",
                dim_3d=(esp_caixa, prof_bandeja, alt_lat_sap),
                pos_3d=(x_dir, y_ini, z_base),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=True
            )
            lat_dir.fitas.topo = lat_dir.fitas.esquerda = True
            lat_dir.adicionar_rasgo(0.0, recuo_canal, larg_canal, prof_bandeja, prof_canal, "H", "CANAL_FUNDO")

            frente_s = Peca(
                categoria_industrial="frente_sapateira",
                nome_comercial=f"{self.perfil.obter_nome_peca('frente_sapateira')} {num_s}",
                dim_3d=(larg_interna, esp_caixa, round(alt_lat_sap - rebaixo_ctrf_tras, 2)),
                pos_3d=(x_meio, y_ini, z_base),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            frente_s.fitas.topo = True
            frente_s.adicionar_rasgo(0.0, recuo_canal, larg_canal, larg_interna, prof_canal, "H", "CANAL_FUNDO")

            tras_s = Peca(
                categoria_industrial="traseira_sapateira",
                nome_comercial=f"{self.perfil.obter_nome_peca('traseira_sapateira')} {num_s}",
                dim_3d=(larg_interna, esp_caixa, round(alt_lat_sap - rebaixo_ctrf_tras, 2)),
                pos_3d=(x_meio, round(y_ini + prof_bandeja - esp_caixa, 2), z_base),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            tras_s.fitas.topo = True
            tras_s.adicionar_rasgo(0.0, recuo_canal, larg_canal, larg_interna, prof_canal, "H", "CANAL_FUNDO")

            fundo_s = Peca(
                categoria_industrial="fundo_sapateira",
                nome_comercial=f"{self.perfil.obter_nome_peca('fundo_sapateira')} {num_s}",
                dim_3d=(round(larg_interna + 2.0 * penetracao, 2), round(prof_bandeja - 2.0 * esp_caixa + 2.0 * penetracao, 2), esp_fundo),
                pos_3d=(round(x_meio - penetracao, 2), round(y_ini + esp_caixa - penetracao, 2), round(z_base + recuo_canal, 2)),
                material=mat_fundo,
                id_pai=id_modulo
            )

            pecas_geradas.extend([lat_esq, lat_dir, frente_s, tras_s, fundo_s])
            metadados_corredicas.append({
                "indice_gaveta": num_s,
                "z_furo_corredica_global": round(z_base + offset_corredica_z, 2),
                "y_inicio_trilho": y_ini,
                "comprimento_trilho": prof_bandeja,
                "lat_esq": lat_esq,
                "lat_dir": lat_dir,
                "ctrf": frente_s,
                "traseira": tras_s,
                "frente": frente_s
            })

        vao_alvo.ocupacao_interna = "SAPATEIRA"
        vao_alvo.pecas_internas.extend(pecas_geradas)
        setattr(vao_alvo, "metadados_gaveteiro", metadados_corredicas)
        return pecas_geradas