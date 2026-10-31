# =============================================================================
# ARQUIVO: tiranocad_core/construtores/avulsos.py
# RESPONSABILIDADE: Fabricar Peças e Subconjuntos Avulsos (Gaveta Solta com
# Corpo Completo, Par de Portas para Alvenaria com Canecos 35mm, Porta Única,
# Frente de Gaveta Solta e Peças Estruturais Unitárias) guiados pelo Perfil.
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
    Reaproveita os construtores especialistas e as regras do Perfil JSON.
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
        """
        Fabrica o subconjunto ou peça avulsa solicitada.
        """
        subtipo = subtipo_avulso.strip().upper()
        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        tem_veio_caixa = not any(c in mat_caixa.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])
        tem_veio_frente = not any(c in mat_frente.upper() for c in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        # Cria um Vão Espacial Virtual (sem paredes externas) para reutilizar a inteligência de Gavetas e Portas
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

        # 1. GAVETA COMPLETA AVULSA (Frente + Corpo + Fundo + Furos de Fixação)
        if subtipo == "GAVETA_COMPLETA":
            c_gavetas = ConstrutorGavetas(self.perfil)
            qtd_gav = max(1, int(quantidade))
            pecas = c_gavetas.construir_gaveteiro(id_modulo, vao_virtual, qtd_gav)
            o_usinagens.aplicar_todas_usinagens({}, vao_virtual)
            return pecas

        # 2. PORTAS AVULSAS COM CANECOS DE 35mm (Par Duplo, Simples Esquerda ou Direita)
        if subtipo in ("PAR_PORTAS", "PORTA_ESQUERDA", "PORTA_DIREITA"):
            c_frentes = ConstrutorFrentes(self.perfil)
            abertura = "DUPLA" if subtipo == "PAR_PORTAS" else (
                "ESQUERDA" if subtipo == "PORTA_ESQUERDA" else "DIREITA"
            )
            pecas = c_frentes.construir_portas_giro(id_modulo, vao_virtual, abertura)
            o_usinagens.aplicar_todas_usinagens({}, vao_virtual)
            return pecas

        # 3. FRENTE DE GAVETA SOLTA (Fita nos 4 lados)
        if subtipo == "FRENTE_GAVETA_SOLTA":
            frente = Peca(
                categoria_industrial="frente_gaveta",
                nome_comercial="Frente de Gaveta Avulsa",
                dim_3d=(largura_x, esp_frente, altura_y),
                pos_3d=(0.0, 0.0, 0.0),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente
            )
            frente.fitas.base = frente.fitas.direita = frente.fitas.topo = frente.fitas.esquerda = True
            return [frente]

        # 4. PRATELEIRA OU BASE AVULSA (Horizontal com fita frontal)
        if subtipo == "PRATELEIRA_AVULSA":
            prat = Peca(
                categoria_industrial="prateleira_livre",
                nome_comercial="Prateleira / Base Avulsa",
                dim_3d=(largura_x, profundidade_z, esp_caixa),
                pos_3d=(0.0, 0.0, 0.0),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            prat.fitas.base = True
            return [prat]

        # 5. LATERAL OU DIVISÓRIA AVULSA (Vertical YZ com fita frontal)
        lat = Peca(
            categoria_industrial="lateral_esquerda",
            nome_comercial="Painel / Lateral Avulsa",
            dim_3d=(esp_caixa, profundidade_z, altura_y),
            pos_3d=(0.0, 0.0, 0.0),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio_caixa
        )
        lat.fitas.esquerda = True
        return [lat]