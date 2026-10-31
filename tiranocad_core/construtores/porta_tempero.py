# =============================================================================
# ARQUIVO: tiranocad_core/construtores/porta_tempero.py
# RESPONSABILIDADE: Construir o Carro Extraível Porta-Tempero / Porta-Óleo
# fiel ao modelo construtivo do Ruby (Corpo estrutural extraível em MDF com
# Base, Traseira, Prateleira Intermediária, Guardas Laterais e Frente Externa).
# =============================================================================

from typing import Any, Dict, List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorPortaTempero:
    """
    Especialista na fabricação do Carro Extraível Porta-Tempero.
    Gera a estrutura integrada guiada pelas folgas de corrediça e frentes do Perfil.
    """

    TRILHOS_COMERCIAIS_MM = [550.0, 500.0, 450.0, 400.0, 350.0, 300.0, 250.0]

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_porta_tempero(self, id_modulo: str, vao_alvo: NoEspacial) -> List[Peca]:
        """
        Constrói o Porta-Tempero dentro do 'vao_alvo' e registra os metadados
        dos trilhos de corrediça para o OrquestradorUsinagens furar as laterais.
        """
        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))

        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        modo_frente = str(self.perfil.obter("folgas_frentes.tipo_montagem_frente")).strip().upper()
        gap_sup = float(self.perfil.obter("folgas_frentes.gap_superior"))
        gap_inf = float(self.perfil.obter("folgas_frentes.gap_inferior"))
        gap_esq = float(self.perfil.obter("folgas_frentes.gap_lateral_esquerda"))
        gap_dir = float(self.perfil.obter("folgas_frentes.gap_lateral_direita"))
        gap_entre = float(self.perfil.obter("folgas_frentes.gap_entre_frentes"))
        afast_frontal = float(self.perfil.obter("folgas_frentes.afastamento_frontal_caixa"))

        folga_corredica = float(self.perfil.obter("regras_gaveta.folga_corredica_cada_lado"))
        recuo_trilho = float(self.perfil.obter("regras_gaveta.recuo_trilho_frontal"))
        folga_traseira = float(self.perfil.obter("regras_gaveta.folga_profundidade_traseira"))
        elevacao_base_z = float(self.perfil.obter("regras_gaveta.elevacao_base_caixote_z"))
        offset_corredica_z = float(self.perfil.obter("regras_gaveta.offset_eixo_corredica_z"))

        tem_veio_caixa = not any(c in mat_caixa.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])
        tem_veio_frente = not any(c in mat_frente.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        # 1. Escolha do trilho comercial
        prof_max = vao_alvo.profundidade - recuo_trilho - folga_traseira
        prof_carro = next((t for t in self.TRILHOS_COMERCIAIS_MM if t <= prof_max), 0.0)
        if prof_carro <= 0.0:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade do '{vao_alvo.nome_vao}' ({vao_alvo.profundidade}mm) não comporta Porta-Tempero."
            )

        # 2. Cálculo de Cobertura da Frente Externa (respeitando Divisória Compartilhada)
        viz_esq = vao_alvo.vizinhos.get("esquerda")
        viz_dir = vao_alvo.vizinhos.get("direita")
        eh_div_esq = viz_esq is not None and "divisoria" in viz_esq.categoria_industrial
        eh_div_dir = viz_dir is not None and "divisoria" in viz_dir.categoria_industrial

        if modo_frente == "EMBUTIDA":
            cob_esq, cob_dir, cob_inf, cob_sup = -gap_esq, -gap_dir, -gap_inf, -gap_sup
            y_frente = round(vao_alvo.y, 2)
        else:
            cob_esq = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_esq else (esp_caixa - gap_esq)
            cob_dir = ((esp_caixa / 2.0) - (gap_entre / 2.0)) if eh_div_dir else (esp_caixa - gap_dir)
            cob_inf = esp_caixa - gap_inf
            cob_sup = esp_caixa - gap_sup
            y_frente = round(vao_alvo.y - esp_frente - afast_frontal, 2)

        larg_frente = round(vao_alvo.largura + cob_esq + cob_dir, 2)
        alt_frente = round(vao_alvo.altura + cob_inf + cob_sup, 2)

        pecas: List[Peca] = []

        # ---------------------------------------------------------------------
        # PEÇA 1: FRENTE EXTERNA DO PORTA-TEMPERO
        # ---------------------------------------------------------------------
        frente = Peca(
            categoria_industrial="frente_porta_tempero",
            nome_comercial="Frente Porta-Tempero",
            dim_3d=(larg_frente, esp_frente, alt_frente),
            pos_3d=(vao_alvo.x - cob_esq, y_frente, vao_alvo.z - cob_inf),
            material=mat_frente,
            id_pai=id_modulo,
            tem_veio=tem_veio_frente
        )
        frente.fitas.base = frente.fitas.direita = frente.fitas.topo = frente.fitas.esquerda = True
        pecas.append(frente)

        # ---------------------------------------------------------------------
        # GEOMETRIA DO CORPO INTERNO EXTRAÍVEL (Quadro Vertical + 2 Níveis)
        # ---------------------------------------------------------------------
        larg_carro_externa = round(vao_alvo.largura - (2.0 * folga_corredica), 2)
        larg_interna_prateleiras = round(larg_carro_externa - (2.0 * esp_caixa), 2)
        alt_carro = round(vao_alvo.altura - (2.0 * elevacao_base_z), 2)
        alt_guarda_lateral = 95.0

        x_carro = round(vao_alvo.x + folga_corredica, 2)
        y_carro = round(vao_alvo.y + recuo_trilho, 2)
        z_carro = round(vao_alvo.z + elevacao_base_z, 2)

        # PEÇA 2: Contra-Frente Estrutural Vertical (Une o carro à Frente Externa)
        ctrf_tempero = Peca(
            categoria_industrial="contra_frente_tempero",
            nome_comercial="Contra-Frente Porta-Tempero",
            dim_3d=(larg_carro_externa, esp_caixa, alt_carro),
            pos_3d=(x_carro, y_carro, z_carro),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio_caixa
        )
        ctrf_tempero.fitas.topo = ctrf_tempero.fitas.esquerda = ctrf_tempero.fitas.direita = True
        pecas.append(ctrf_tempero)

        # PEÇA 3: Traseira Estrutural Vertical do Porta-Tempero
        tras_tempero = Peca(
            categoria_industrial="traseira_porta_tempero",
            nome_comercial="Traseira Porta-Tempero",
            dim_3d=(larg_carro_externa, esp_caixa, alt_carro),
            pos_3d=(x_carro, y_carro + prof_carro - esp_caixa, z_carro),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio_caixa
        )
        tras_tempero.fitas.topo = tras_tempero.fitas.esquerda = tras_tempero.fitas.direita = True
        pecas.append(tras_tempero)

        # PEÇAS 4 e 5: Bases/Bandejas Horizontais (Inferior e Intermediária) entre Contra-Frente e Traseira
        prof_bandeja = round(prof_carro - (2.0 * esp_caixa), 2)
        cotas_z_niveis = [z_carro, round(z_carro + (alt_carro * 0.48), 2)]

        for idx_nivel, z_niv in enumerate(cotas_z_niveis, 1):
            base_niv = Peca(
                categoria_industrial="base_porta_tempero",
                nome_comercial=f"Base Nível Porta-Tempero {idx_nivel}",
                dim_3d=(larg_interna_prateleiras, prof_bandeja, esp_caixa),
                pos_3d=(x_carro + esp_caixa, y_carro + esp_caixa, z_niv),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            pecas.append(base_niv)

            # Guardas Laterais Esquerda e Direita de cada nível (onde correm os trilhos e seguram as garrafas)
            for eh_dir, x_lat, sufixo in (
                (False, x_carro, "Esq"),
                (True, x_carro + larg_carro_externa - esp_caixa, "Dir")
            ):
                lat_guarda = Peca(
                    categoria_industrial=f"lateral_gaveta_{'direita' if eh_dir else 'esquerda'}",
                    nome_comercial=f"Lateral Porta-Tempero ({sufixo}) {idx_nivel}",
                    dim_3d=(esp_caixa, prof_bandeja, alt_guarda_lateral),
                    pos_3d=(x_lat, y_carro + esp_caixa, z_niv),
                    material=mat_caixa,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_caixa,
                    espelhar_cam_x=eh_dir
                )
                lat_guarda.fitas.topo = True
                pecas.append(lat_guarda)

        vao_alvo.ocupacao_interna = "PORTA_TEMPERO"
        vao_alvo.pecas_internas.extend(pecas)

        # Registra metadados para furar os 2 pares de corrediças telescópicas (embaixo e no meio)
        metadados_trilhos: List[Dict[str, Any]] = []
        for idx_nivel, z_niv in enumerate(cotas_z_niveis, 1):
            metadados_trilhos.append({
                "indice_gaveta": idx_nivel,
                "z_furo_corredica_global": round(z_niv + offset_corredica_z, 2),
                "y_inicio_trilho": y_carro,
                "comprimento_trilho": prof_carro,
                "somente_trilho_lateral": True
            })
        setattr(vao_alvo, "metadados_gaveteiro", metadados_trilhos)

        return pecas