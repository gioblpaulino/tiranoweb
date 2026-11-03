# =============================================================================
# ARQUIVO: tiranocad_core/construtores/tamponamentos.py
# RESPONSABILIDADE: Construir Tamponamentos Agregados (Individual ou Lote),
# Fechamentos/Afastadores de Parede, Vista em "L" com divisão automática por
# limite de chapa, Fita padrão em 1 lado (Frente) e Redimensionamento por Peça.
# =============================================================================

import math
from typing import Any, Dict, List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import Peca


class ConstrutorTamponamento:
    """
    Especialista na geração de Tamponamentos Agregados, Fechamentos de Parede
    e Vistas em 'L' com suporte a envelopamento de múltiplos módulos.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    @staticmethod
    def _aplicar_override_dimensional_tamp(peca: Peca, overrides_map: Dict[str, Any]) -> None:
        """
        Permite redimensionar ou deslocar individualmente qualquer peça do
        tamponamento/fechamento através do Menu Flutuante 3D.
        """
        ov = overrides_map.get(peca.nome_comercial)
        if not ov:
            return

        dx = float(ov.get("dx", peca.dimensoes_3d["x"]))
        dy = float(ov.get("dy", peca.dimensoes_3d["y"]))
        dz = float(ov.get("dz", peca.dimensoes_3d["z"]))

        px = float(peca.posicao_relativa["pos_x"]) + float(ov.get("offset_x", 0.0))
        py = float(peca.posicao_relativa["pos_y"]) + float(ov.get("offset_y", 0.0))
        pz = float(peca.posicao_relativa["pos_z"]) + float(ov.get("offset_z", 0.0))

        peca.dimensoes_3d = {"x": round(dx, 2), "y": round(dy, 2), "z": round(dz, 2)}
        peca.posicao_relativa = {"pos_x": round(px, 2), "pos_y": round(py, 2), "pos_z": round(pz, 2)}
        peca.espessura, peca.dim_x_2d, peca.dim_y_2d, peca.orientacao_3d = peca._planificar_dimensoes(dx, dy, dz)

    def construir_tamponamentos_agregados(
        self,
        id_modulo: str,
        largura_mod: float,
        altura_mod: float,
        profundidade_mod: float,
        config_tamp: Dict[str, Any]
    ) -> List[Peca]:
        """
        Gera as peças de tamponamento e fechamento de parede agregadas ao módulo.
        Por padrão, aplica fita de borda APENAS no lado frontal visível (deixando
        os demais topos em MDF Cru).
        """
        if not config_tamp or not config_tamp.get("ativo", False):
            return []

        esp_tamp = float(config_tamp.get("espessura_mm", 18.0))
        avanco_frontal = float(config_tamp.get("avanco_frontal_mm", 18.0))
        subida_topo = float(config_tamp.get("subida_topo_mm", 70.0))
        descida_base = float(config_tamp.get("descida_base_mm", 0.0))
        larg_aba_l = float(config_tamp.get("largura_aba_l_mm", 60.0))

        tem_lat_esq = bool(config_tamp.get("lateral_esquerda", False))
        tem_lat_dir = bool(config_tamp.get("lateral_direita", False))
        tem_vista_l = bool(config_tamp.get("vista_superior_l", False))
        tem_topo_cheio = bool(config_tamp.get("topo_passante", False))

        # Fechamentos / Afastadores de Parede (acompanham a altura do tamponamento lateral)
        tem_fech_esq = bool(config_tamp.get("fechamento_esquerda", False))
        tem_fech_dir = bool(config_tamp.get("fechamento_direita", False))
        larg_fech = float(config_tamp.get("largura_fechamento_mm", 50.0))
        esp_fech = float(config_tamp.get("espessura_fechamento_mm", esp_tamp))

        # Comprimento de conjunto (quando envelopa múltiplos módulos selecionados)
        largura_conjunto = float(config_tamp.get("largura_conjunto_mm") or largura_mod)
        ultimo_tem_lat_dir = bool(config_tamp.get("conjunto_tem_lat_dir", tem_lat_dir))

        overrides_pecas_tamp = config_tamp.get("overrides_pecas_tamp") or {}

        # Limite útil da chapa do Perfil para seccionar vistas muito compridas
        max_comp_chapa = float(self.perfil.obter("restricoes_chapa.comprimento_max_mdf"))
        refilo = float(self.perfil.obter("restricoes_chapa.refilo_seguranca"))
        limite_util_chapa = max_comp_chapa - (2.0 * refilo)

        mat_tamp = str(
            config_tamp.get("material") or self.perfil.obter("materiais_padrao.material_frentes")
        )
        tem_veio = not any(c in mat_tamp.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "GRAFITE", "TX"])

        prof_total_tamp = round(profundidade_mod + avanco_frontal, 2)
        alt_total_lat = round(altura_mod + subida_topo + descida_base, 2)
        y_inicio_tamp = round(-avanco_frontal, 2)
        z_inicio_lat = round(-descida_base, 2)

        pecas: List[Peca] = []

        # =====================================================================
        # 1. TAMPONAMENTO LATERAL ESQUERDO (Fita apenas na Frente: esquerda=True)
        # =====================================================================
        if tem_lat_esq:
            tamp_esq = Peca(
                categoria_industrial="painel_tamponamento",
                nome_comercial="Tamponamento Lateral (Esq)",
                dim_3d=(esp_tamp, prof_total_tamp, alt_total_lat),
                pos_3d=(-esp_tamp, y_inicio_tamp, z_inicio_lat),
                material=mat_tamp,
                id_pai=id_modulo,
                tem_veio=tem_veio,
                espelhar_cam_x=False
            )
            tamp_esq.fitas.esquerda = True  # Apenas o lado frontal recebe fita por padrão!
            self._aplicar_override_dimensional_tamp(tamp_esq, overrides_pecas_tamp)
            pecas.append(tamp_esq)

        # =====================================================================
        # 2. TAMPONAMENTO LATERAL DIREITO (Fita apenas na Frente: esquerda=True)
        # =====================================================================
        if tem_lat_dir:
            tamp_dir = Peca(
                categoria_industrial="painel_tamponamento",
                nome_comercial="Tamponamento Lateral (Dir)",
                dim_3d=(esp_tamp, prof_total_tamp, alt_total_lat),
                pos_3d=(largura_mod, y_inicio_tamp, z_inicio_lat),
                material=mat_tamp,
                id_pai=id_modulo,
                tem_veio=tem_veio,
                espelhar_cam_x=True
            )
            tamp_dir.fitas.esquerda = True  # Apenas o lado frontal recebe fita por padrão!
            self._aplicar_override_dimensional_tamp(tamp_dir, overrides_pecas_tamp)
            pecas.append(tamp_dir)

        # =====================================================================
        # 3. FECHAMENTOS / AFASTADORES DE PAREDE (Mesma altura dos Tamponamentos)
        # =====================================================================
        if tem_fech_esq and larg_fech > 0:
            x_fech_esq = (-esp_tamp - larg_fech) if tem_lat_esq else -larg_fech
            fech_esq = Peca(
                categoria_industrial="painel_tamponamento",
                nome_comercial="Fechamento Parede (Esq)",
                dim_3d=(larg_fech, esp_fech, alt_total_lat),
                pos_3d=(round(x_fech_esq, 2), y_inicio_tamp, z_inicio_lat),
                material=mat_tamp,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            fech_esq.fitas.direita = True  # Fita apenas na borda vertical de encontro
            self._aplicar_override_dimensional_tamp(fech_esq, overrides_pecas_tamp)
            pecas.append(fech_esq)

        if tem_fech_dir and larg_fech > 0:
            x_fech_dir = (largura_mod + esp_tamp) if tem_lat_dir else largura_mod
            fech_dir = Peca(
                categoria_industrial="painel_tamponamento",
                nome_comercial="Fechamento Parede (Dir)",
                dim_3d=(larg_fech, esp_fech, alt_total_lat),
                pos_3d=(round(x_fech_dir, 2), y_inicio_tamp, z_inicio_lat),
                material=mat_tamp,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            fech_dir.fitas.esquerda = True  # Fita apenas na borda vertical de encontro
            self._aplicar_override_dimensional_tamp(fech_dir, overrides_pecas_tamp)
            pecas.append(fech_dir)

        # =====================================================================
        # 4. VISTA SUPERIOR EM "L" (Individual ou Entre Laterais de Múltiplos Módulos)
        # =====================================================================
        if tem_vista_l and subida_topo >= 25.0:
            x_ini_vista = 0.0 if tem_lat_esq else -esp_tamp
            x_fim_vista = largura_conjunto if ultimo_tem_lat_dir else (largura_conjunto + esp_tamp)
            larg_total_vista = round(x_fim_vista - x_ini_vista, 2)

            # Se ultrapassar o tamanho útil da chapa (ex: 2710mm), divide em tramos iguais!
            qtd_segmentos = max(1, math.ceil(larg_total_vista / limite_util_chapa))
            larg_segmento = round(larg_total_vista / float(qtd_segmentos), 2)

            for idx_seg in range(qtd_segmentos):
                sufixo_seg = f" {idx_seg + 1}" if qtd_segmentos > 1 else ""
                x_seg = round(x_ini_vista + (idx_seg * larg_segmento), 2)

                vista_frontal = Peca(
                    categoria_industrial="painel_tamponamento",
                    nome_comercial=f"Vista Superior Frontal (Perfil L){sufixo_seg}",
                    dim_3d=(larg_segmento, esp_tamp, subida_topo),
                    pos_3d=(x_seg, y_inicio_tamp, altura_mod),
                    material=mat_tamp,
                    id_pai=id_modulo,
                    tem_veio=tem_veio
                )
                vista_frontal.fitas.base = True  # Fita apenas em 1 lado (borda frontal inferior)!
                self._aplicar_override_dimensional_tamp(vista_frontal, overrides_pecas_tamp)
                pecas.append(vista_frontal)

                aba_deitada_l = Peca(
                    categoria_industrial="painel_tamponamento",
                    nome_comercial=f"Travessa Base da Vista em L{sufixo_seg}",
                    dim_3d=(larg_segmento, larg_aba_l, esp_tamp),
                    pos_3d=(x_seg, round(y_inicio_tamp + esp_tamp, 2), altura_mod),
                    material=mat_tamp,
                    id_pai=id_modulo,
                    tem_veio=tem_veio
                )
                aba_deitada_l.fitas.base = True
                self._aplicar_override_dimensional_tamp(aba_deitada_l, overrides_pecas_tamp)
                pecas.append(aba_deitada_l)

        # =====================================================================
        # 5. TAMPONAMENTO SUPERIOR INTEIRIÇO (OPCIONAL)
        # =====================================================================
        if tem_topo_cheio and not tem_vista_l:
            x_ini_t = 0.0 if tem_lat_esq else -esp_tamp
            x_fim_t = largura_conjunto if ultimo_tem_lat_dir else (largura_conjunto + esp_tamp)
            larg_total_topo = round(x_fim_t - x_ini_t, 2)

            qtd_seg_t = max(1, math.ceil(larg_total_topo / limite_util_chapa))
            larg_seg_t = round(larg_total_topo / float(qtd_seg_t), 2)

            for idx_seg in range(qtd_seg_t):
                sufixo_seg = f" {idx_seg + 1}" if qtd_seg_t > 1 else ""
                x_seg = round(x_ini_t + (idx_seg * larg_seg_t), 2)
                tamp_sup = Peca(
                    categoria_industrial="painel_tamponamento",
                    nome_comercial=f"Tamponamento Superior{sufixo_seg}",
                    dim_3d=(larg_seg_t, prof_total_tamp, esp_tamp),
                    pos_3d=(x_seg, y_inicio_tamp, altura_mod),
                    material=mat_tamp,
                    id_pai=id_modulo,
                    tem_veio=tem_veio
                )
                tamp_sup.fitas.base = True  # Fita apenas na borda frontal!
                self._aplicar_override_dimensional_tamp(tamp_sup, overrides_pecas_tamp)
                pecas.append(tamp_sup)

        return pecas