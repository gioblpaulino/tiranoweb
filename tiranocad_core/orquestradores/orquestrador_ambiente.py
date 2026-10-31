# =============================================================================
# ARQUIVO: tiranocad_core/orquestradores/orquestrador_ambiente.py
# RESPONSABILIDADE: Coordenar as Paredes do ConstrutorAmbiente, calcular o
# Auto-Snap lateral e executar movimentações/rotações direcionais (individuais
# ou em lote) respeitando as coordenadas da parede ou globais do ambiente.
# =============================================================================

from typing import Any, Dict, List, Optional
from tiranocad_core.modelos.ambiente import ConstrutorAmbiente, Parede


class OrquestradorAmbiente:
    """
    Gerencia a planta baixa de paredes e posiciona/movimenta os módulos no espaço 3D.
    """

    ALTURA_PADRAO_AEREO_MM = 1450.0

    def __init__(self):
        self.construtor_paredes = ConstrutorAmbiente(pe_direito_padrao=2700.0, espessura_padrao=150.0)
        self.construtor_paredes.gerar_preset_ambiente("L", larg_a=3600.0, larg_b=2600.0)

    def obter_primeira_parede(self) -> Optional[Parede]:
        return self.construtor_paredes.paredes[0] if self.construtor_paredes.paredes else None

    def calcular_proximo_x_autosnap(
        self,
        id_parede: str,
        elevacao_z: float,
        modulos_ativos: Dict[str, Dict[str, Any]],
        ignorar_id_modulo: Optional[str] = None
    ) -> float:
        """
        Descobre onde termina o último módulo ancorado na mesma parede e na mesma
        faixa de altura (Piso vs. Aéreo), retornando a cota X exata para Auto-Snap.
        """
        maior_x_ocupado = 0.0
        eh_faixa_alta = (elevacao_z >= 900.0)

        for m_id, mod in modulos_ativos.items():
            if ignorar_id_modulo and m_id == ignorar_id_modulo:
                continue

            pos_amb = mod.get("posicionamento_ambiente", {})
            if pos_amb.get("id_parede") != id_parede:
                continue

            z_mod = float(pos_amb.get("elevacao_z", 0.0))
            mod_eh_alto = (z_mod >= 900.0)

            if eh_faixa_alta == mod_eh_alto:
                x_ini = float(pos_amb.get("distancia_x_parede", 0.0))
                larg_m = float(mod["dimensoes_ocupadas"]["largura_x"])
                fim_m = x_ini + larg_m
                if fim_m > maior_x_ocupado:
                    maior_x_ocupado = fim_m

        return round(maior_x_ocupado, 2)

    def ancorar_modulo_na_parede(
        self,
        modulo_dict: Dict[str, Any],
        modulos_ativos: Dict[str, Dict[str, Any]],
        id_parede: Optional[str] = None,
        distancia_x_parede: Optional[float] = None,
        elevacao_z: Optional[float] = None,
        afastamento_parede: Optional[float] = None,
        rotacao_offset_graus: Optional[float] = None,
        usar_autosnap: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula e injeta o dicionário 'posicionamento_ambiente' dentro do módulo,
        convertendo coordenadas relativas da parede em coordenadas 3D globais.
        """
        pos_atual = modulo_dict.get("posicionamento_ambiente", {})

        parede = self.construtor_paredes.obter_parede(id_parede) if id_parede else None
        if not parede:
            parede = self.obter_primeira_parede()

        familia = str(modulo_dict.get("familia", "MODULO_INFERIOR")).upper()

        # Define elevação Z (1450mm automático para Aéreos quando não informado ou zerado na criação)
        if elevacao_z is None:
            z_final = self.ALTURA_PADRAO_AEREO_MM if familia == "MODULO_AEREO" else 0.0
        else:
            z_final = float(elevacao_z)

        afast_final = float(
            afastamento_parede if afastamento_parede is not None else pos_atual.get("afastamento_parede", 0.0)
        )
        rot_offset_final = float(
            rotacao_offset_graus if rotacao_offset_graus is not None else pos_atual.get("rotacao_offset_graus", 0.0)
        )

        if not parede:
            x_dist = float(distancia_x_parede or 0.0)
            modulo_dict["posicionamento_ambiente"] = {
                "id_parede": None,
                "nome_parede": "Livre (Sem Parede)",
                "distancia_x_parede": round(x_dist, 2),
                "elevacao_z": round(z_final, 2),
                "afastamento_parede": round(afast_final, 2),
                "rotacao_offset_graus": round(rot_offset_final, 2),
                "x_ambiente": round(x_dist, 2),
                "y_ambiente": round(afast_final, 2),
                "z_ambiente": round(z_final, 2),
                "rotacao_graus": round(rot_offset_final, 2),
                "sobra_parede_mm": 0.0
            }
            return modulo_dict["posicionamento_ambiente"]

        if usar_autosnap or distancia_x_parede is None:
            x_dist = self.calcular_proximo_x_autosnap(
                id_parede=parede.id_parede,
                elevacao_z=z_final,
                modulos_ativos=modulos_ativos,
                ignorar_id_modulo=modulo_dict["id_modulo"]
            )
        else:
            x_dist = float(distancia_x_parede)

        transf = parede.calcular_transformacao_modulo(
            distancia_ao_longo_mm=x_dist,
            elevacao_z_mm=z_final,
            afastamento_parede_mm=afast_final
        )

        rot_total = (transf["rotacao_graus"] + rot_offset_final) % 360.0
        larg_mod = float(modulo_dict["dimensoes_ocupadas"]["largura_x"])
        sobra_parede = round(parede.comprimento - (x_dist + larg_mod), 2)

        modulo_dict["posicionamento_ambiente"] = {
            "id_parede": parede.id_parede,
            "nome_parede": parede.nome,
            "distancia_x_parede": round(x_dist, 2),
            "elevacao_z": round(z_final, 2),
            "afastamento_parede": round(afast_final, 2),
            "rotacao_offset_graus": round(rot_offset_final, 2),
            "x_ambiente": transf["x_ambiente"],
            "y_ambiente": transf["y_ambiente"],
            "z_ambiente": transf["z_ambiente"],
            "rotacao_graus": round(rot_total, 2),
            "sobra_parede_mm": sobra_parede
        }
        return modulo_dict["posicionamento_ambiente"]

    def transformar_lote_modulos(
        self,
        ids_selecionados: List[str],
        modulos_ativos: Dict[str, Dict[str, Any]],
        delta_x: float = 0.0,
        delta_y: float = 0.0,
        delta_z: float = 0.0,
        delta_rotacao: float = 0.0,
        z_absoluto: Optional[float] = None,
        y_absoluto: Optional[float] = None,
        rotacao_absoluta: Optional[float] = None,
        nova_id_parede: Optional[str] = None,
        aplicar_autosnap: bool = False
    ) -> List[str]:
        """
        Aplica deslocamentos direcionais (X, Y, Z) e rotações em 1 ou múltiplos
        módulos selecionados simultaneamente.
        """
        modificados: List[str] = []

        for m_id in ids_selecionados:
            if m_id not in modulos_ativos:
                continue

            mod = modulos_ativos[m_id]
            pos = mod.get("posicionamento_ambiente", {})

            id_par_alvo = nova_id_parede if nova_id_parede else pos.get("id_parede")
            trocou_parede = (nova_id_parede is not None and nova_id_parede != pos.get("id_parede"))

            novo_x = float(pos.get("distancia_x_parede", 0.0)) + float(delta_x)
            novo_y = float(y_absoluto) if y_absoluto is not None else (float(pos.get("afastamento_parede", 0.0)) + float(delta_y))
            novo_z = float(z_absoluto) if z_absoluto is not None else max(0.0, float(pos.get("elevacao_z", 0.0)) + float(delta_z))

            if rotacao_absoluta is not None:
                novo_rot = float(rotacao_absoluta)
            else:
                novo_rot = (float(pos.get("rotacao_offset_graus", 0.0)) + float(delta_rotacao)) % 360.0

            self.ancorar_modulo_na_parede(
                modulo_dict=mod,
                modulos_ativos=modulos_ativos,
                id_parede=id_par_alvo,
                distancia_x_parede=None if (aplicar_autosnap or trocou_parede) else novo_x,
                elevacao_z=novo_z,
                afastamento_parede=novo_y,
                rotacao_offset_graus=novo_rot,
                usar_autosnap=(aplicar_autosnap or trocou_parede)
            )
            modificados.append(m_id)

        return modificados

    def recalcular_todos_modulos(self, modulos_ativos: Dict[str, Dict[str, Any]]) -> None:
        for mod in modulos_ativos.values():
            pos = mod.get("posicionamento_ambiente", {})
            self.ancorar_modulo_na_parede(
                modulo_dict=mod,
                modulos_ativos=modulos_ativos,
                id_parede=pos.get("id_parede"),
                distancia_x_parede=pos.get("distancia_x_parede", 0.0),
                elevacao_z=pos.get("elevacao_z", 0.0),
                afastamento_parede=pos.get("afastamento_parede", 0.0),
                rotacao_offset_graus=pos.get("rotacao_offset_graus", 0.0),
                usar_autosnap=False
            )