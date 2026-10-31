# =============================================================================
# ARQUIVO: tiranocad_core/construtores/frentes.py
# RESPONSABILIDADE: Construir Portas de Giro (Esquerda, Direita, Dupla) e
# Portas Basculantes Horizontais (Simples ou Dupla) sobre qualquer Nó Espacial.
# =============================================================================

from typing import Dict, List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorFrentes:
    """Especialista na geração de portas de giro e portas basculantes."""

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_portas_giro(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        tipo_abertura: str = "DUPLA"
    ) -> List[Peca]:
        tipo_abertura = tipo_abertura.strip().upper()
        if tipo_abertura not in ("ESQUERDA", "DIREITA", "DUPLA"):
            raise ErroGeometriaCAD(f"🚨 Tipo de abertura inválido: '{tipo_abertura}'.")

        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        modo_frente = str(self.perfil.obter("folgas_frentes.tipo_montagem_frente")).strip().upper()
        gap_sup = float(self.perfil.obter("folgas_frentes.gap_superior"))
        gap_inf = float(self.perfil.obter("folgas_frentes.gap_inferior"))
        gap_esq = float(self.perfil.obter("folgas_frentes.gap_lateral_esquerda"))
        gap_dir = float(self.perfil.obter("folgas_frentes.gap_lateral_direita"))
        gap_entre = float(self.perfil.obter("folgas_frentes.gap_entre_frentes"))
        afast_frontal = float(self.perfil.obter("folgas_frentes.afastamento_frontal_caixa"))

        tem_veio_frente = not any(
            cor in mat_frente.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"]
        )

        if modo_frente == "EMBUTIDA":
            largura_total_cobertura = round(vao_alvo.largura - gap_esq - gap_dir, 2)
            altura_porta = round(vao_alvo.altura - gap_inf - gap_sup, 2)
            x_origem_cobertura = round(vao_alvo.x + gap_esq, 2)
            y_porta = round(vao_alvo.y, 2)
            z_porta = round(vao_alvo.z + gap_inf, 2)
        else:
            viz_esq = vao_alvo.vizinhos.get("esquerda")
            viz_dir = vao_alvo.vizinhos.get("direita")
            eh_div_esq = viz_esq is not None and "divisoria" in viz_esq.categoria_industrial
            eh_div_dir = viz_dir is not None and "divisoria" in viz_dir.categoria_industrial

            cob_esq = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_esq else (esp_caixa - gap_esq)
            cob_dir = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_dir else (esp_caixa - gap_dir)
            cob_inf = esp_caixa - gap_inf
            cob_sup = esp_caixa - gap_sup

            largura_total_cobertura = round(vao_alvo.largura + cob_esq + cob_dir, 2)
            altura_porta = round(vao_alvo.altura + cob_inf + cob_sup, 2)
            x_origem_cobertura = round(vao_alvo.x - cob_esq, 2)
            y_porta = round(vao_alvo.y - esp_frente - afast_frontal, 2)
            z_porta = round(vao_alvo.z - cob_inf, 2)

        portas_geradas: List[Peca] = []
        metadados_portas: List[Dict] = []

        if tipo_abertura in ("ESQUERDA", "DIREITA"):
            eh_direita = (tipo_abertura == "DIREITA")
            categoria = "porta_giro_direita" if eh_direita else "porta_giro_esquerda"
            lado_dobradica = "direita" if eh_direita else "esquerda"

            porta = Peca(
                categoria_industrial=categoria,
                nome_comercial=f"{self.perfil.obter_nome_peca(categoria)} 1",
                dim_3d=(largura_total_cobertura, esp_frente, altura_porta),
                pos_3d=(x_origem_cobertura, y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=eh_direita
            )
            self._aplicar_fita_4_lados(porta)
            portas_geradas.append(porta)
            metadados_portas.append({
                "peca_porta": porta,
                "lado_fixacao": lado_dobradica,
                "peca_apoio_lateral": vao_alvo.vizinhos.get(lado_dobradica)
            })
        else:
            largura_cada_porta = round((largura_total_cobertura - gap_entre) / 2.0, 2)
            if largura_cada_porta <= 80.0:
                raise ErroGeometriaCAD(f"🚨 Vão estreito demais ({vao_alvo.largura}mm) para porta dupla.")

            porta_esq = Peca(
                categoria_industrial="porta_giro_esquerda",
                nome_comercial=f"{self.perfil.obter_nome_peca('porta_giro_esquerda')} 1",
                dim_3d=(largura_cada_porta, esp_frente, altura_porta),
                pos_3d=(x_origem_cobertura, y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=False
            )
            self._aplicar_fita_4_lados(porta_esq)
            portas_geradas.append(porta_esq)
            metadados_portas.append({
                "peca_porta": porta_esq,
                "lado_fixacao": "esquerda",
                "peca_apoio_lateral": vao_alvo.vizinhos.get("esquerda")
            })

            x_porta_dir = round(x_origem_cobertura + largura_cada_porta + gap_entre, 2)
            porta_dir = Peca(
                categoria_industrial="porta_giro_direita",
                nome_comercial=f"{self.perfil.obter_nome_peca('porta_giro_direita')} 2",
                dim_3d=(largura_cada_porta, esp_frente, altura_porta),
                pos_3d=(x_porta_dir, y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=True
            )
            self._aplicar_fita_4_lados(porta_dir)
            portas_geradas.append(porta_dir)
            metadados_portas.append({
                "peca_porta": porta_dir,
                "lado_fixacao": "direita",
                "peca_apoio_lateral": vao_alvo.vizinhos.get("direita")
            })

        setattr(vao_alvo, "metadados_portas", metadados_portas)
        return portas_geradas

    def construir_portas_basculantes(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        quantidade_basculantes: int = 1
    ) -> List[Peca]:
        """Constrói 1 ou 2 Portas Basculantes horizontais (abertura para cima)."""
        qtd = max(1, min(2, int(quantidade_basculantes)))

        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        modo_frente = str(self.perfil.obter("folgas_frentes.tipo_montagem_frente")).strip().upper()
        gap_sup = float(self.perfil.obter("folgas_frentes.gap_superior"))
        gap_inf = float(self.perfil.obter("folgas_frentes.gap_inferior"))
        gap_esq = float(self.perfil.obter("folgas_frentes.gap_lateral_esquerda"))
        gap_dir = float(self.perfil.obter("folgas_frentes.gap_lateral_direita"))
        gap_entre = float(self.perfil.obter("folgas_frentes.gap_entre_frentes"))
        afast_frontal = float(self.perfil.obter("folgas_frentes.afastamento_frontal_caixa"))

        tem_veio_frente = not any(c in mat_frente.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        if modo_frente == "EMBUTIDA":
            larg_porta = round(vao_alvo.largura - gap_esq - gap_dir, 2)
            alt_total_cob = round(vao_alvo.altura - gap_inf - gap_sup, 2)
            x_porta = round(vao_alvo.x + gap_esq, 2)
            y_porta = round(vao_alvo.y, 2)
            z_inicio = round(vao_alvo.z + gap_inf, 2)
        else:
            viz_esq = vao_alvo.vizinhos.get("esquerda")
            viz_dir = vao_alvo.vizinhos.get("direita")
            eh_div_esq = viz_esq is not None and "divisoria" in viz_esq.categoria_industrial
            eh_div_dir = viz_dir is not None and "divisoria" in viz_dir.categoria_industrial

            cob_esq = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_esq else (esp_caixa - gap_esq)
            cob_dir = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_dir else (esp_caixa - gap_dir)
            cob_inf = esp_caixa - gap_inf
            cob_sup = esp_caixa - gap_sup

            larg_porta = round(vao_alvo.largura + cob_esq + cob_dir, 2)
            alt_total_cob = round(vao_alvo.altura + cob_inf + cob_sup, 2)
            x_porta = round(vao_alvo.x - cob_esq, 2)
            y_porta = round(vao_alvo.y - esp_frente - afast_frontal, 2)
            z_inicio = round(vao_alvo.z - cob_inf, 2)

        alt_cada_basc = round((alt_total_cob - ((qtd - 1) * gap_entre)) / float(qtd), 2)

        portas_geradas: List[Peca] = []
        metadados_portas: List[Dict] = []

        for i in range(qtd):
            z_basc = round(z_inicio + i * (alt_cada_basc + gap_entre), 2)
            porta = Peca(
                categoria_industrial="porta_basculante",
                nome_comercial=f"{self.perfil.obter_nome_peca('porta_basculante')} {i + 1}",
                dim_3d=(larg_porta, esp_frente, alt_cada_basc),
                pos_3d=(x_porta, y_porta, z_basc),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=False
            )
            self._aplicar_fita_4_lados(porta)
            portas_geradas.append(porta)

            metadados_portas.append({
                "peca_porta": porta,
                "eh_basculante": True,
                "peca_apoio_topo": vao_alvo.vizinhos.get("topo"),
                "peca_apoio_esq": vao_alvo.vizinhos.get("esquerda"),
                "peca_apoio_dir": vao_alvo.vizinhos.get("direita")
            })

        setattr(vao_alvo, "metadados_portas", metadados_portas)
        return portas_geradas

    @staticmethod
    def _aplicar_fita_4_lados(peca: Peca) -> None:
        peca.fitas.base = True
        peca.fitas.direita = True
        peca.fitas.topo = True
        peca.fitas.esquerda = True