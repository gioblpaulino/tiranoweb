# =============================================================================
# ARQUIVO: tiranocad_core/construtores/internos.py
# RESPONSABILIDADE: Inserir Divisórias Verticais e Prateleiras (Fixas ou Livres)
# dentro de qualquer Nó Espacial, subdividindo o vão automaticamente e
# auditando limites estruturais (como risco de empenamento por vão livre).
# =============================================================================

from typing import List, Optional, Tuple
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorInternos:
    """
    Especialista na divisão interna de vãos (Divisórias e Prateleiras).
    Opera de forma 100% recursiva sobre qualquer nó folha da árvore NoEspacial.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def inserir_divisoria_vertical(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        posicao_x_relativa: Optional[float] = None
    ) -> Tuple[Peca, List[NoEspacial]]:
        """
        Insere uma Divisória Vertical dentro do 'vao_alvo' e fatia o espaço
        em dois novos sub-vãos (Esquerdo e Direito).
        """
        if not vao_alvo.eh_folha or vao_alvo.ocupacao_interna is not None:
            raise ErroGeometriaCAD(
                f"🚨 O vão '{vao_alvo.nome_vao}' já está ocupado ou subdividido e não pode receber divisória."
            )

        # 1. Leitura dos parâmetros técnicos do Perfil JSON
        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_divisoria"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_divisoria"))

        tem_veio = not any(cor in mat_caixa.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        # 2. Cálculo da posição X (se None, centraliza perfeitamente no vão)
        if posicao_x_relativa is None:
            cota_x_local = (vao_alvo.largura - esp_mdf) / 2.0
        else:
            cota_x_local = float(posicao_x_relativa)

        prof_divisoria = vao_alvo.profundidade - recuo_frontal - recuo_traseiro
        alt_divisoria = vao_alvo.altura

        if prof_divisoria <= 50.0:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade resultante da divisória ({prof_divisoria}mm) é inválida no '{vao_alvo.nome_vao}'."
            )

        # 3. Criação da Peça 3D/2D
        pos_3d_x = vao_alvo.x + cota_x_local
        pos_3d_y = vao_alvo.y + recuo_frontal
        pos_3d_z = vao_alvo.z

        divisoria = Peca(
            categoria_industrial="divisoria_vertical",
            nome_comercial=self.perfil.obter_nome_peca("divisoria_vertical"),
            dim_3d=(esp_mdf, prof_divisoria, alt_divisoria),
            pos_3d=(pos_3d_x, pos_3d_y, pos_3d_z),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio,
            espelhar_cam_x=False
        )
        # No plano YZ planificado (dim_x = profundidade, dim_y = altura), a frente é a borda Esquerda (X=0)
        divisoria.fitas.esquerda = True

        # 4. Fatia o Nó Espacial e atualiza os vizinhos automaticamente
        sub_vaos = vao_alvo.dividir_verticalmente(divisoria, cota_x_local)
        return divisoria, sub_vaos

    def inserir_prateleira(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        fixa: bool = False,
        posicao_z_relativa: Optional[float] = None
    ) -> Tuple[Peca, List[NoEspacial]]:
        """
        Insere uma Prateleira (Fixa ou Livre) dentro do 'vao_alvo' e fatia o espaço
        em dois novos sub-vãos (Inferior e Superior).
        """
        if not vao_alvo.eh_folha or vao_alvo.ocupacao_interna is not None:
            raise ErroGeometriaCAD(
                f"🚨 O vão '{vao_alvo.nome_vao}' já está ocupado e não pode receber prateleira."
            )

        # 1. Leitura dos parâmetros do Perfil JSON
        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_prateleira"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_prateleira"))
        max_vao_sem_apoio = float(self.perfil.obter("restricoes_chapa.largura_max_vao_livre_sem_apoio"))

        tem_veio = not any(cor in mat_caixa.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        # Se for Prateleira Fixa, ela costuma ser faceada na frente (sem recuo frontal)
        recuo_f_aplicado = 0.0 if fixa else recuo_frontal

        if posicao_z_relativa is None:
            cota_z_local = (vao_alvo.altura - esp_mdf) / 2.0
        else:
            cota_z_local = float(posicao_z_relativa)

        larg_prateleira = vao_alvo.largura
        prof_prateleira = vao_alvo.profundidade - recuo_f_aplicado - recuo_traseiro

        categoria = "prateleira_fixa" if fixa else "prateleira_livre"
        pos_3d_x = vao_alvo.x
        pos_3d_y = vao_alvo.y + recuo_f_aplicado
        pos_3d_z = vao_alvo.z + cota_z_local

        prateleira = Peca(
            categoria_industrial=categoria,
            nome_comercial=self.perfil.obter_nome_peca(categoria),
            dim_3d=(larg_prateleira, prof_prateleira, esp_mdf),
            pos_3d=(pos_3d_x, pos_3d_y, pos_3d_z),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio,
            espelhar_cam_x=False
        )
        # Na peça deitada (dim_x = largura, dim_y = profundidade), a frente é a Base (Y=0)
        prateleira.fitas.base = True

        # 2. Auditoria de Engenharia: Alerta de Empenamento (Flecha)
        if larg_prateleira > max_vao_sem_apoio:
            prateleira.avisos_auditoria.append(
                f"⚠️ Risco de Empenamento: A '{prateleira.nome_comercial}' no '{vao_alvo.nome_vao}' "
                f"possui {larg_prateleira:.0f}mm de vão livre (limite recomendado para {esp_mdf:.0f}mm é "
                f"{max_vao_sem_apoio:.0f}mm). Considere adicionar uma divisória ou engrossar a peça."
            )

        # 3. Fatia o Nó Espacial em Vão Inferior e Vão Superior
        sub_vaos = vao_alvo.dividir_horizontalmente(prateleira, cota_z_local)
        return prateleira, sub_vaos

    def distribuir_prateleiras_iguais(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        quantidade: int,
        fixas: bool = False
    ) -> List[Peca]:
        """
        Subdivide um vão com N prateleiras igualmente espaçadas na vertical.
        Usa recursividade sobre a árvore NoEspacial para manter todos os vãos rastreados!
        """
        if quantidade <= 0:
            return []

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        altura_total_disponivel = vao_alvo.altura - (quantidade * esp_mdf)

        if altura_total_disponivel <= (quantidade + 1) * 50.0:
            raise ErroGeometriaCAD(
                f"🚨 Altura do '{vao_alvo.nome_vao}' ({vao_alvo.altura}mm) não comporta {quantidade} prateleiras."
            )

        altura_cada_nicho = altura_total_disponivel / float(quantidade + 1)
        pecas_criadas: List[Peca] = []
        vao_cursor = vao_alvo

        for _ in range(quantidade):
            prat, sub_vaos = self.inserir_prateleira(
                id_modulo=id_modulo,
                vao_alvo=vao_cursor,
                fixa=fixas,
                posicao_z_relativa=altura_cada_nicho
            )
            pecas_criadas.append(prat)
            # Continua fatiando o sub-vão superior restante
            vao_cursor = sub_vaos[1]

        return pecas_criadas