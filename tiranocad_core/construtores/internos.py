# =============================================================================
# ARQUIVO: tiranocad_core/construtores/internos.py
# RESPONSABILIDADE: Inserir Divisórias Verticais, Divisórias Horizontais
# Estruturais (que fatiaram o NoEspacial) e Prateleiras Internas (que ocupam o
# vão sem destruir o nó folha, permitindo Portas de Giro/Basculantes no vão!).
# =============================================================================

from typing import List, Optional, Tuple
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial


class ConstrutorInternos:
    """
    Especialista na divisão interna de vãos (Divisórias e Prateleiras).
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def inserir_divisoria_vertical(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        posicao_x_relativa: Optional[float] = None
    ) -> Tuple[Peca, List[NoEspacial]]:
        if not vao_alvo.eh_folha:
            raise ErroGeometriaCAD(
                f"🚨 O vão '{vao_alvo.nome_vao}' já possui subdivisões estruturais."
            )

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_divisoria"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_divisoria"))

        tem_veio = not any(cor in mat_caixa.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])

        cota_x_local = ((vao_alvo.largura - esp_mdf) / 2.0) if posicao_x_relativa is None else float(posicao_x_relativa)
        prof_divisoria = round(vao_alvo.profundidade - recuo_frontal - recuo_traseiro, 2)
        alt_divisoria = vao_alvo.altura

        if prof_divisoria <= 50.0:
            raise ErroGeometriaCAD(f"🚨 Profundidade resultante da divisória ({prof_divisoria}mm) é inválida.")

        divisoria = Peca(
            categoria_industrial="divisoria_vertical",
            nome_comercial=self.perfil.obter_nome_peca("divisoria_vertical"),
            dim_3d=(esp_mdf, prof_divisoria, alt_divisoria),
            pos_3d=(vao_alvo.x + cota_x_local, vao_alvo.y + recuo_frontal, vao_alvo.z),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio
        )
        divisoria.fitas.esquerda = True

        sub_vaos = vao_alvo.dividir_verticalmente(divisoria, cota_x_local)
        return divisoria, sub_vaos

    def inserir_prateleira(
        self,
        id_modulo: str,
        vao_alvo: NoEspacial,
        fixa: bool = True,
        posicao_z_relativa: Optional[float] = None
    ) -> Tuple[Peca, List[NoEspacial]]:
        """
        Usado para DIVISORIA_HORIZONTAL estrutural (ex: separar os andares de uma
        Torre Quente), fatiando o NoEspacial em sub-vão Inferior (.0) e Superior (.1).
        """
        if not vao_alvo.eh_folha:
            raise ErroGeometriaCAD(f"🚨 O vão '{vao_alvo.nome_vao}' já foi subdividido.")

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_prateleira"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_prateleira"))
        max_vao_sem_apoio = float(self.perfil.obter("restricoes_chapa.largura_max_vao_livre_sem_apoio"))

        tem_veio = not any(cor in mat_caixa.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])
        recuo_f_aplicado = 0.0 if fixa else recuo_frontal
        cota_z_local = ((vao_alvo.altura - esp_mdf) / 2.0) if posicao_z_relativa is None else float(posicao_z_relativa)

        larg_prateleira = vao_alvo.largura
        prof_prateleira = max(60.0, round(vao_alvo.profundidade - recuo_f_aplicado - recuo_traseiro, 2))
        categoria = "prateleira_fixa" if fixa else "prateleira_livre"

        prateleira = Peca(
            categoria_industrial=categoria,
            nome_comercial=self.perfil.obter_nome_peca(categoria),
            dim_3d=(larg_prateleira, prof_prateleira, esp_mdf),
            pos_3d=(vao_alvo.x, vao_alvo.y + recuo_f_aplicado, vao_alvo.z + cota_z_local),
            material=mat_caixa,
            id_pai=id_modulo,
            tem_veio=tem_veio
        )
        prateleira.fitas.base = True

        if larg_prateleira > max_vao_sem_apoio:
            prateleira.avisos_auditoria.append(
                f"⚠️ Risco de Empenamento: '{prateleira.nome_comercial}' com {larg_prateleira:.0f}mm de vão livre."
            )

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
        Distribui N prateleiras igualmente espaçadas dentro do 'vao_alvo' SEM
        quebrar o nó folha do NoEspacial, permitindo que o mesmo vão receba
        Portas de Giro ou Basculantes cobrindo o vão inteiro!
        """
        if quantidade <= 0:
            return []

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_prateleira"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_prateleira"))
        max_vao_sem_apoio = float(self.perfil.obter("restricoes_chapa.largura_max_vao_livre_sem_apoio"))

        altura_total_disp = vao_alvo.altura - (quantidade * esp_mdf)
        if altura_total_disp <= (quantidade + 1) * 40.0:
            raise ErroGeometriaCAD(
                f"🚨 Altura do '{vao_alvo.nome_vao}' ({vao_alvo.altura}mm) não comporta {quantidade} prateleira(s)."
            )

        tem_veio = not any(cor in mat_caixa.upper() for cor in ["BRANCO", "CRU", "PRETO", "CINZA", "TX"])
        recuo_f = 0.0 if fixas else recuo_frontal
        larg_prat = vao_alvo.largura
        prof_prat = max(60.0, round(vao_alvo.profundidade - recuo_f - recuo_traseiro, 2))
        categoria = "prateleira_fixa" if fixas else "prateleira_livre"

        altura_nicho = altura_total_disp / float(quantidade + 1)
        pecas_criadas: List[Peca] = []
        lista_prats_vao = getattr(vao_alvo, "metadados_prateleiras", [])

        for i in range(quantidade):
            z_local = (i + 1) * altura_nicho + (i * esp_mdf)
            z_global = round(vao_alvo.z + z_local, 2)

            prat = Peca(
                categoria_industrial=categoria,
                nome_comercial=self.perfil.obter_nome_peca(categoria),
                dim_3d=(larg_prat, prof_prat, esp_mdf),
                pos_3d=(vao_alvo.x, round(vao_alvo.y + recuo_f, 2), z_global),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio
            )
            prat.fitas.base = True

            if larg_prat > max_vao_sem_apoio:
                prat.avisos_auditoria.append(
                    f"⚠️ Risco de Empenamento: '{prat.nome_comercial}' com {larg_prat:.0f}mm de vão livre."
                )

            pecas_criadas.append(prat)
            lista_prats_vao.append(prat)

        vao_alvo.pecas_internas.extend(pecas_criadas)
        setattr(vao_alvo, "metadados_prateleiras", lista_prats_vao)
        return pecas_criadas