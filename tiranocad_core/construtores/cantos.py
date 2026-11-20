# =============================================================================
# ARQUIVO: tiranocad_core/construtores/cantos.py
# RESPONSABILIDADE: Construir Módulos de Canto Reto (Inferior, Aéreo e Torre)
# com Porta Cega Interna ou Externa, Batente/Montante de apoio para dobradiça,
# Prateleiras inteiriças e 1 ou 2 Portas de Giro no vão útil.
# =============================================================================

from typing import Any, Dict, List, Tuple
from tiranocad_core.gerenciador_perfis import GerenciadorPerfis
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca
from tiranocad_core.modelos.no_espacial import NoEspacial
from tiranocad_core.construtores.caixaria import ConstrutorCaixaria
from tiranocad_core.construtores.internos import ConstrutorInternos
from tiranocad_core.orquestradores.orquestrador_usinagens import OrquestradorUsinagens


class ConstrutorCantos:
    """
    Especialista na fabricação paramétrica de Módulos de Canto Reto.
    100% Data-Driven pelo Perfil JSON.
    """

    def __init__(self, perfil: GerenciadorPerfis):
        self.perfil = perfil

    def construir_canto_reto(
        self,
        id_modulo: str,
        largura_x: float,
        altura_y: float,
        profundidade_z: float,
        opcoes: Dict[str, Any],
        com_fundo: bool = True
    ) -> Tuple[List[Peca], NoEspacial]:
        # 1. Lê parâmetros customizados pela UI (com fallback 100% no Perfil JSON)
        subfamilia = str(opcoes.get("subfamilia_canto", "MODULO_INFERIOR")).strip().upper()
        lado_cego = str(opcoes.get("lado_cego", "ESQUERDA")).strip().upper()  # ESQUERDA ou DIREITA
        tipo_cega = str(
            opcoes.get("tipo_porta_cega", self.perfil.obter("regras_canto_reto.tipo_porta_cega_padrao"))
        ).strip().upper()  # INTERNA ou EXTERNA

        larg_area_cega = float(
            opcoes.get("largura_area_cega_mm", self.perfil.obter("regras_canto_reto.largura_area_cega_padrao_mm"))
        )
        larg_batente = float(
            opcoes.get("largura_batente_mm", self.perfil.obter("regras_canto_reto.largura_batente_padrao_mm"))
        )
        avanco_batente = float(
            opcoes.get("avanco_frontal_batente_mm", self.perfil.obter("regras_canto_reto.avanco_frontal_batente_mm"))
        )
        desloc_x_afastador = float(
            opcoes.get("deslocamento_x_afastador_mm", self.perfil.obter("regras_canto_reto.deslocamento_x_afastador_mm"))
        )
        qtd_portas = max(1, min(2, int(opcoes.get("qtd_portas_canto", 1))))
        qtd_prateleiras = max(0, min(6, int(opcoes.get("qtd_prateleiras_canto", 1))))

        esp_caixa = float(self.perfil.obter("materiais_padrao.espessura_estrutural_mm"))
        esp_frente = float(self.perfil.obter("materiais_padrao.espessura_frente_mm"))
        mat_caixa = str(self.perfil.obter("materiais_padrao.material_caixaria"))
        mat_frente = str(self.perfil.obter("materiais_padrao.material_frentes"))

        gap_sup = float(self.perfil.obter("folgas_frentes.gap_superior"))
        gap_inf = float(self.perfil.obter("folgas_frentes.gap_inferior"))
        gap_esq = float(self.perfil.obter("folgas_frentes.gap_lateral_esquerda"))
        gap_dir = float(self.perfil.obter("folgas_frentes.gap_lateral_direita"))
        gap_entre = float(self.perfil.obter("folgas_frentes.gap_entre_frentes"))
        afast_frontal = float(self.perfil.obter("folgas_frentes.afastamento_frontal_caixa"))
        larg_min_porta = float(self.perfil.obter("limites_engenharia.largura_min_porta_dupla_mm"))

        tem_veio_caixa = self.perfil.material_possui_veio(mat_caixa)
        tem_veio_frente = self.perfil.material_possui_veio(mat_frente)

        # Validação geométrica do vão livre da porta
        larg_vao_porta = round(largura_x - larg_area_cega - esp_caixa, 2)
        if larg_vao_porta < 200.0:
            raise ErroGeometriaCAD(
                f"🚨 [CANTO RETO] A largura total ({largura_x:.0f}mm) é insuficiente para "
                f"Área Cega de {larg_area_cega:.0f}mm (sobrou apenas {larg_vao_porta:.0f}mm para a porta)."
            )

        # 2. Constrói a Caixaria Base usando o ConstrutorCaixaria oficial (Inferior, Aéreo ou Torre)
        c_caixaria = ConstrutorCaixaria(self.perfil)
        pecas, vao_raiz, mapa_estrutural = c_caixaria.construir(
            id_modulo=id_modulo,
            familia=subfamilia,
            largura_x=largura_x,
            altura_y=altura_y,
            profundidade_z=profundidade_z,
            com_fundo=com_fundo
        )

        # 3. Prateleira(s) Inteiriça(s) passando de ponta a ponta no vão interno
        if qtd_prateleiras > 0:
            c_internos = ConstrutorInternos(self.perfil)
            prats = c_internos.distribuir_prateleiras_iguais(
                id_modulo=id_modulo,
                vao_alvo=vao_raiz,
                quantidade=qtd_prateleiras,
                fixas=False,
                recuo_frontal_override=larg_batente
            )
            pecas.extend(prats)

        eh_cego_esq = (lado_cego == "ESQUERDA")
        alt_porta = round(altura_y - gap_inf - gap_sup, 2)
        y_porta = round(-esp_frente - afast_frontal, 2)
        z_porta = round(gap_inf, 2)

        nome_batente = self.perfil.obter_nome_peca("batente_canto")
        nome_afastador = self.perfil.obter_nome_peca("afastador_canto")

        # 4. MONTANTE(S) INTERNO(S) DE APOIO + AFASTADOR FRONTAL SEPARADO
        if tipo_cega == "INTERNA":
            # Regra Cega Interna: 1 único montante interno faceando o fim da porta cega
            # (Profundidade = larg_batente - esp_frente, ex: 70 - 15 = 55mm; + 15mm da porta cega na frente)
            prof_montante = max(35.0, round(larg_batente - esp_frente, 2))
            x_montante = round(larg_area_cega - esp_caixa, 2) if eh_cego_esq else round(largura_x - larg_area_cega, 2)

            montante_dobradica = Peca(
                categoria_industrial="batente_canto",
                nome_comercial=nome_batente,
                dim_3d=(esp_caixa, prof_montante, vao_raiz.altura),
                pos_3d=(x_montante, esp_frente, vao_raiz.z),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=not eh_cego_esq
            )
            montante_dobradica.fitas.esquerda = True
            pecas.append(montante_dobradica)

            # Porta Cega Interna embutida (Y = 0 até esp_frente)
            larg_cega = round(larg_area_cega - esp_caixa, 2)
            x_cega = round(esp_caixa, 2) if eh_cego_esq else round(x_montante, 2)
            porta_cega = Peca(
                categoria_industrial="porta_cega_canto",
                nome_comercial=self.perfil.obter_nome_peca("porta_cega_canto"),
                dim_3d=(larg_cega, esp_frente, vao_raiz.altura),
                pos_3d=(x_cega, 0.0, vao_raiz.z),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente
            )
            porta_cega.fitas.base = porta_cega.fitas.topo = porta_cega.fitas.esquerda = porta_cega.fitas.direita = True
            pecas.append(porta_cega)

            # Afastador Frontal separado (para fora do módulo, Y < 0)
            if avanco_batente > 0:
                afastador = Peca(
                    categoria_industrial="afastador_canto",
                    nome_comercial=nome_afastador,
                    dim_3d=(esp_caixa, avanco_batente, alt_porta),
                    pos_3d=(round(x_montante + desloc_x_afastador, 2), round(-avanco_batente, 2), z_porta),
                    material=mat_frente,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_frente
                )
                afastador.fitas.esquerda = afastador.fitas.topo = afastador.fitas.base = True
                pecas.append(afastador)

            # Limites X das portas de abrir
            if eh_cego_esq:
                x_ini_portas = round(larg_area_cega + gap_entre, 2)
                x_fim_portas = round(largura_x - gap_dir, 2)
            else:
                x_ini_portas = round(gap_esq, 2)
                x_fim_portas = round(x_montante - gap_entre, 2)

        else:
            # Regra Cega Externa: Montante DUPLO interno (15mm + 15mm)
            # 1 peça atrás da porta cega + 1 peça aparente no vão onde vai o calço da dobradiça!
            if eh_cego_esq:
                x_mont_cega = round(larg_area_cega - esp_caixa, 2)
                x_mont_dobradica = round(larg_area_cega, 2)
            else:
                x_mont_cega = round(largura_x - larg_area_cega, 2)
                x_mont_dobradica = round(largura_x - larg_area_cega - esp_caixa, 2)

            montante_cega = Peca(
                categoria_industrial="batente_canto",
                nome_comercial=f"{nome_batente} (Apoio Cega)",
                dim_3d=(esp_caixa, larg_batente, vao_raiz.altura),
                pos_3d=(x_mont_cega, 0.0, vao_raiz.z),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa
            )
            montante_cega.fitas.esquerda = True

            montante_dobradica = Peca(
                categoria_industrial="batente_canto",
                nome_comercial=f"{nome_batente} (Apoio Dobradiça)",
                dim_3d=(esp_caixa, larg_batente, vao_raiz.altura),
                pos_3d=(x_mont_dobradica, 0.0, vao_raiz.z),
                material=mat_caixa,
                id_pai=id_modulo,
                tem_veio=tem_veio_caixa,
                espelhar_cam_x=not eh_cego_esq
            )
            montante_dobradica.fitas.esquerda = True
            pecas.extend([montante_cega, montante_dobradica])

            # Porta Cega Externa sobreposta (alinhada em Y com as portas)
            larg_cega = round(larg_area_cega - (gap_esq if eh_cego_esq else gap_dir), 2)
            x_cega = round(gap_esq, 2) if eh_cego_esq else round(x_mont_cega, 2)
            porta_cega = Peca(
                categoria_industrial="porta_cega_canto",
                nome_comercial=self.perfil.obter_nome_peca("porta_cega_canto"),
                dim_3d=(larg_cega, esp_frente, alt_porta),
                pos_3d=(x_cega, y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente
            )
            porta_cega.fitas.base = porta_cega.fitas.topo = porta_cega.fitas.esquerda = porta_cega.fitas.direita = True
            pecas.append(porta_cega)

            # Afastador Frontal separado (avançando para fora na linha do montante aparente)
            if avanco_batente > 0:
                afastador = Peca(
                    categoria_industrial="afastador_canto",
                    nome_comercial=nome_afastador,
                    dim_3d=(esp_caixa, avanco_batente, alt_porta),
                    pos_3d=(
                        round(x_mont_dobradica + desloc_x_afastador, 2),
                        round(y_porta - avanco_batente, 2),
                        z_porta
                    ),
                    material=mat_frente,
                    id_pai=id_modulo,
                    tem_veio=tem_veio_frente
                )
                afastador.fitas.esquerda = afastador.fitas.topo = afastador.fitas.base = True
                pecas.append(afastador)

            # Limites X das portas de abrir
            if eh_cego_esq:
                x_ini_portas = round(x_mont_dobradica + esp_caixa + gap_entre, 2)
                x_fim_portas = round(largura_x - gap_dir, 2)
            else:
                x_ini_portas = round(gap_esq, 2)
                x_fim_portas = round(x_mont_dobradica - gap_entre, 2)

        # 6. PORTA(S) DE GIRO NO VÃO LIVRE ÚTIL (1 ou 2 folhas)
        apoio_esq = montante_dobradica if eh_cego_esq else mapa_estrutural["lateral_esquerda"]
        apoio_dir = mapa_estrutural["lateral_direita"] if eh_cego_esq else montante_dobradica
        larg_total_portas = round(x_fim_portas - x_ini_portas, 2)
        metadados_portas: List[Dict[str, Any]] = []

        if qtd_portas == 1:
            eh_dir = not eh_cego_esq
            cat_p = "porta_giro_direita" if eh_dir else "porta_giro_esquerda"
            porta = Peca(
                categoria_industrial=cat_p,
                nome_comercial=f"{self.perfil.obter_nome_peca(cat_p)} 1",
                dim_3d=(larg_total_portas, esp_frente, alt_porta),
                pos_3d=(x_ini_portas, y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=eh_dir
            )
            porta.fitas.base = porta.fitas.topo = porta.fitas.esquerda = porta.fitas.direita = True
            pecas.append(porta)
            metadados_portas.append({
                "peca_porta": porta,
                "lado_fixacao": "direita" if eh_dir else "esquerda",
                "peca_apoio_lateral": montante_dobradica
            })
        else:
            larg_folha = round((larg_total_portas - gap_entre) / 2.0, 2)
            if larg_folha <= larg_min_porta:
                raise ErroGeometriaCAD(
                    f"🚨 Vão útil do canto ({larg_total_portas:.0f}mm) é estreito demais para 2 portas."
                )

            p_esq = Peca(
                categoria_industrial="porta_giro_esquerda",
                nome_comercial=f"{self.perfil.obter_nome_peca('porta_giro_esquerda')} 1",
                dim_3d=(larg_folha, esp_frente, alt_porta),
                pos_3d=(x_ini_portas, y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=False
            )
            p_esq.fitas.base = p_esq.fitas.topo = p_esq.fitas.esquerda = p_esq.fitas.direita = True

            p_dir = Peca(
                categoria_industrial="porta_giro_direita",
                nome_comercial=f"{self.perfil.obter_nome_peca('porta_giro_direita')} 2",
                dim_3d=(larg_folha, esp_frente, alt_porta),
                pos_3d=(round(x_ini_portas + larg_folha + gap_entre, 2), y_porta, z_porta),
                material=mat_frente,
                id_pai=id_modulo,
                tem_veio=tem_veio_frente,
                espelhar_cam_x=True
            )
            p_dir.fitas.base = p_dir.fitas.topo = p_dir.fitas.esquerda = p_dir.fitas.direita = True

            pecas.extend([p_esq, p_dir])
            metadados_portas.extend([
                {"peca_porta": p_esq, "lado_fixacao": "esquerda", "peca_apoio_lateral": apoio_esq},
                {"peca_porta": p_dir, "lado_fixacao": "direita", "peca_apoio_lateral": apoio_dir}
            ])

        # 7. Aplica todas as usinagens automáticas (caixaria, prateleiras, canecos Ø35mm e calços)
        o_usinagens = OrquestradorUsinagens(self.perfil)
        o_usinagens.aplicar_todas_usinagens(mapa_estrutural, vao_raiz)

        return pecas, vao_raiz