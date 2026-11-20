# =============================================================================
# ARQUIVO: tiranocad_core/construtores/internos.py
# RESPONSABILIDADE: Inserir Divisórias Verticais, Divisórias Horizontais
# Estruturais e Prateleiras Internas 100% Data-Driven pelo Perfil JSON.
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
        prof_min_div = float(self.perfil.obter("limites_engenharia.profundidade_min_divisoria_mm"))

        tem_veio = self.perfil.material_possui_veio(mat_caixa)

        cota_x_local = ((vao_alvo.largura - esp_mdf) / 2.0) if posicao_x_relativa is None else float(posicao_x_relativa)
        prof_divisoria = round(vao_alvo.profundidade - recuo_frontal - recuo_traseiro, 2)
        alt_divisoria = vao_alvo.altura

        if prof_divisoria <= prof_min_div:
            raise ErroGeometriaCAD(
                f"🚨 Profundidade resultante da divisória ({prof_divisoria}mm) é menor que o mínimo ({prof_min_div:.0f}mm)."
            )

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
        if not vao_alvo.eh_folha:
            raise ErroGeometriaCAD(f"🚨 O vão '{vao_alvo.nome_vao}' já foi subdividido.")

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_prateleira"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_prateleira"))
        max_vao_sem_apoio = float(self.perfil.obter("restricoes_chapa.largura_max_vao_livre_sem_apoio"))
        prof_min_prat = float(self.perfil.obter("limites_engenharia.profundidade_min_prateleira_mm"))

        tem_veio = self.perfil.material_possui_veio(mat_caixa)
        recuo_f_aplicado = 0.0 if fixa else recuo_frontal
        cota_z_local = ((vao_alvo.altura - esp_mdf) / 2.0) if posicao_z_relativa is None else float(posicao_z_relativa)

        larg_prateleira = vao_alvo.largura
        prof_prateleira = max(prof_min_prat, round(vao_alvo.profundidade - recuo_f_aplicado - recuo_traseiro, 2))
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
        fixas: bool = False,
        recuo_frontal_override: Optional[float] = None
    ) -> List[Peca]:
        if quantidade <= 0:
            return []

        esp_mdf = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        recuo_frontal = float(self.perfil.obter("geometria_caixaria.recuo_frontal_prateleira"))
        recuo_traseiro = float(self.perfil.obter("geometria_caixaria.recuo_traseiro_prateleira"))
        max_vao_sem_apoio = float(self.perfil.obter("restricoes_chapa.largura_max_vao_livre_sem_apoio"))
        prof_min_prat = float(self.perfil.obter("limites_engenharia.profundidade_min_prateleira_mm"))
        alt_min_nicho = float(self.perfil.obter("limites_engenharia.altura_min_nicho_prateleira_mm"))

        altura_total_disp = vao_alvo.altura - (quantidade * esp_mdf)
        if altura_total_disp <= (quantidade + 1) * alt_min_nicho:
            raise ErroGeometriaCAD(
                f"🚨 Altura do '{vao_alvo.nome_vao}' ({vao_alvo.altura}mm) não comporta {quantidade} prateleira(s)."
            )

        tem_veio = self.perfil.material_possui_veio(mat_caixa)
        recuo_f = float(recuo_frontal_override) if recuo_frontal_override is not None else (0.0 if fixas else recuo_frontal)
        larg_prat = vao_alvo.largura
        prof_prat = max(prof_min_prat, round(vao_alvo.profundidade - recuo_f - recuo_traseiro, 2))
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