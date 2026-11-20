# =============================================================================
# ARQUIVO: tiranocad_core/construtores/avulsos.py
# RESPONSABILIDADE: Fabricar Peças e Subconjuntos Avulsos 100% Data-Driven.
# =============================================================================

from typing import List
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import Peca
from tiranocad_core.modelos.no_espacial import NoEspacial
from tiranocad_core.construtores.gavetas import ConstrutorGavetas
from tiranocad_core.construtores.frentes import ConstrutorFrentes
from tiranocad_core.orquestradores.orquestrador_usinagens import OrquestradorUsinagens


class ConstrutorAvulsos:
    """
    Especialista na fabricação de componentes avulsos fora de módulos padrão.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_item_avulso(
        self,
        id_modulo: str,
        subtipo_avulso: str,
        largura_x: float,
        altura_y: float,
        profundidade_z: float,
        quantidade: int = 1
    ) -> List[Peca]:
        subtipo = subtipo_avulso.strip().upper()
        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        tem_veio_caixa = self.perfil.material_possui_veio(mat_caixa)
        tem_veio_frente = self.perfil.material_possui_veio(mat_frente)

        vao_virtual = NoEspacial(
            x=0.0,
            y=0.0,
            z=0.0,
            largura=largura_x,
            profundidade=profundidade_z,
            altura=altura_y,
            nome_vao="Vão Virtual Avulso",
            id_vao="raiz"
        )

        o_usinagens = OrquestradorUsinagens(self.perfil)

        # 1. GAVETA COMPLETA AVULSA
        if subtipo == "GAVETA_COMPLETA":
            c_gavetas = ConstrutorGavetas(self.perfil)
            qtd_gav = max(1, int(quantidade))
            pecas = c_gavetas.construir_gaveteiro(id_modulo, vao_virtual, qtd_gav)
            o_usinagens.aplicar_todas_usinagens({}, vao_virtual)
            return pecas

        # 2. PORTAS AVULSAS COM CANECOS DE 35mm
        if subtipo in ("PAR_PORTAS", "PORTA_ESQUERDA", "PORTA_DIREITA"):
            c_frentes = ConstrutorFrentes(self.perfil)
            abertura = "DUPLA" if subtipo == "PAR_PORTAS" else (
                "ESQUERDA" if subtipo == "PORTA_ESQUERDA" else "DIREITA"
            )
            pecas = c_frentes.construir_portas_giro(id_modulo, vao_virtual, abertura)
            o_usinagens.aplicar_todas_usinagens({}, vao_virtual)
            return pecas

        # 3. FRENTE DE GAVETA SOLTA
        if subtipo == "FRENTE_GAVETA_SOLTA":
            frente = Peca(
                categoria_industrial="frente_gaveta",
                nome_comercial=self.perfil.obter_nome_peca("frente_gaveta_avulsa"),
                dim_3d=(largura_x, esp_frente, altura_y),
                pos_3d=(0.0, 0.0, 0.0),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente
            )
            frente.fitas.base = frente.fitas.direita = frente.fitas.topo = frente.fitas.esquerda = True
            return [frente]

        # 4. PRATELEIRA OU BASE AVULSA
        if subtipo == "PRATELEIRA_AVULSA":
            prat = Peca(
                categoria_industrial="prateleira_livre",
                nome_comercial=self.perfil.obter_nome_peca("prateleira_avulsa"),
                dim_3d=(largura_x, profundidade_z, esp_caixa),
                pos_3d=(0.0, 0.0, 0.0),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            prat.fitas.base = True
            return [prat]

        # 5. LATERAL OU DIVISÓRIA AVULSA
        lat = Peca(
            categoria_industrial="lateral_esquerda",
            nome_comercial=self.perfil.obter_nome_peca("lateral_avulsa"),
            dim_3d=(esp_caixa, profundidade_z, altura_y),
            pos_3d=(0.0, 0.0, 0.0),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio_caixa
        )
        lat.fitas.esquerda = True
        return [lat]