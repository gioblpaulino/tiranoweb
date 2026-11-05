# =============================================================================
# ARQUIVO: tiranocad_core/orquestradores/orquestrador_ambiente.py
# RESPONSABILIDADE: Gerenciar o posicionamento global dos módulos nas paredes,
# Auto-Snap inteligente (desviando de Portas de Passagem), Transformações em
# Lote e Auditoria de Interferências Arquitetônicas (Janelas, Portas, Água/Gás).
# =============================================================================

import math
from typing import Any, Dict, List, Optional
from tiranocad_core.modelos.ambiente import ConstrutorParedes, ParedeAmbiente


class OrquestradorAmbiente:
    """
    Motor de ancoragem magnética, transformação 3D e validação arquitetônica
    entre os módulos de marcenaria e os elementos da obra (paredes/esquadrias/pontos).
    """

    def __init__(self):
        self.construtor_paredes = ConstrutorParedes()
        self.construtor_paredes.gerar_preset_ambiente("L", 3600.0, 2600.0)

    def calcular_proximo_x_autosnap(
        self,
        id_parede: str,
        elevacao_z: float,
        modulos_ativos: Dict[str, Dict[str, Any]],
        ignorar_id: Optional[str] = None,
        largura_novo_modulo: float = 0.0
    ) -> float:
        """
        Calcula a próxima coordenada X livre na parede para encostar o módulo (Auto-Snap).
        Se for um módulo de piso (Z < 200mm) e houver uma PORTA de passagem no caminho,
        salta automaticamente para depois da porta!
        """
        maior_x_ocupado = 0.0
        eh_aereo = elevacao_z >= 1000.0

        for m_id, mod in modulos_ativos.items():
            if ignorar_id and m_id == ignorar_id:
                continue
            # Ignora bancadas e rodapés no cálculo de fila de armários
            if mod.get("familia") in ("MODULO_BANCADA_PEDRA", "MODULO_RODAPE"):
                continue

            pos = mod.get("posicionamento_ambiente")
            if not pos or pos.get("id_parede") != id_parede:
                continue

            mod_eh_aereo = float(pos.get("elevacao_z", 0.0)) >= 1000.0
            if mod_eh_aereo == eh_aereo:
                fim_x = float(pos.get("distancia_x_parede", 0.0)) + float(mod["dimensoes_ocupadas"]["largura_x"])
                if fim_x > maior_x_ocupado:
                    maior_x_ocupado = fim_x

        x_candidato = round(maior_x_ocupado, 2)

        # Inteligência Arquitetônica: Se o módulo não for aéreo, verifica se vai parar na frente de uma PORTA
        parede = self.construtor_paredes.buscar_parede(id_parede)
        if parede and not eh_aereo:
            larg_teste = largura_novo_modulo if largura_novo_modulo > 0 else 600.0
            for el in sorted(parede.elementos, key=lambda e: e.distancia_x):
                if el.tipo == "PORTA":
                    p_ini = el.distancia_x
                    p_fim = el.distancia_x + el.largura_x
                    # Se o intervalo [x_candidato, x_candidato + larg_teste] cruza a porta, pula para depois da porta!
                    if (x_candidato < p_fim - 5.0) and ((x_candidato + larg_teste) > p_ini + 5.0):
                        x_candidato = round(p_fim, 2)

        return x_candidato

    def ancorar_modulo_na_parede(
        self,
        modulo_dict: Dict[str, Any],
        modulos_ativos: Dict[str, Dict[str, Any]],
        id_parede: Optional[str] = None,
        distancia_x_parede: Optional[float] = None,
        elevacao_z: Optional[float] = None,
        afastamento_parede: float = 0.0,
        rotacao_offset_graus: float = 0.0,
        usar_autosnap: bool = True
    ) -> Dict[str, Any]:
        """Ancora um módulo em uma parede convertendo coordenadas locais em globais 3D."""
        familia = modulo_dict.get("familia", "MODULO_INFERIOR")
        if elevacao_z is None:
            elevacao_z = 1450.0 if familia == "MODULO_AEREO" else 0.0
        else:
            elevacao_z = float(elevacao_z)

        parede: Optional[ParedeAmbiente] = None
        if id_parede and id_parede != "LIVRE":
            parede = self.construtor_paredes.buscar_parede(id_parede)
        elif id_parede is None and self.construtor_paredes.paredes:
            parede = self.construtor_paredes.paredes[0]

        larg_mod = float(modulo_dict["dimensoes_ocupadas"]["largura_x"])

        if not parede:
            dist_x = float(distancia_x_parede) if distancia_x_parede is not None else 0.0
            pos_info = {
                "id_parede": "LIVRE",
                "nome_parede": "Livre (Sem Parede)",
                "distancia_x_parede": round(dist_x, 2),
                "elevacao_z": round(elevacao_z, 2),
                "afastamento_parede": round(float(afastamento_parede), 2),
                "rotacao_offset_graus": round(float(rotacao_offset_graus), 2),
                "pos_global_x": round(dist_x, 2),
                "pos_global_y": round(float(afastamento_parede), 2),
                "pos_global_z": round(elevacao_z, 2),
                "rotacao_graus": round(float(rotacao_offset_graus), 2),
                "sobra_parede_mm": 0.0,
                "ultrapassou_parede": False
            }
            modulo_dict["posicionamento_ambiente"] = pos_info
            return pos_info

        if usar_autosnap or distancia_x_parede is None:
            dist_x = self.calcular_proximo_x_autosnap(
                id_parede=parede.id_parede,
                elevacao_z=elevacao_z,
                modulos_ativos=modulos_ativos,
                ignorar_id=modulo_dict["id_modulo"],
                largura_novo_modulo=larg_mod
            )
        else:
            dist_x = float(distancia_x_parede)

        ux, uy = parede.vetor_direcao
        nx, ny = parede.vetor_normal_interno

        pos_global_x = parede.x1 + (ux * dist_x) + (nx * float(afastamento_parede))
        pos_global_y = parede.y1 + (uy * dist_x) + (ny * float(afastamento_parede))
        rot_final = parede.angulo_graus + float(rotacao_offset_graus)
        sobra_parede = round(parede.comprimento - (dist_x + larg_mod), 2)

        pos_info = {
            "id_parede": parede.id_parede,
            "nome_parede": parede.nome,
            "distancia_x_parede": round(dist_x, 2),
            "elevacao_z": round(elevacao_z, 2),
            "afastamento_parede": round(float(afastamento_parede), 2),
            "rotacao_offset_graus": round(float(rotacao_offset_graus), 2),
            "pos_global_x": round(pos_global_x, 2),
            "pos_global_y": round(pos_global_y, 2),
            "pos_global_z": round(elevacao_z, 2),
            "rotacao_graus": round(rot_final, 2),
            "sobra_parede_mm": sobra_parede,
            "ultrapassou_parede": sobra_parede < 0.0
        }

        modulo_dict["posicionamento_ambiente"] = pos_info
        return pos_info

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
    ) -> List[Dict[str, Any]]:
        """Aplica translações e rotações simultaneamente a múltiplos módulos."""
        modificados = []

        for m_id in ids_selecionados:
            if m_id not in modulos_ativos:
                continue

            mod = modulos_ativos[m_id]
            pos_atual = mod.get("posicionamento_ambiente", {})

            id_par = nova_id_parede if nova_id_parede is not None else pos_atual.get("id_parede")
            trocou_parede = (nova_id_parede is not None and nova_id_parede != pos_atual.get("id_parede"))

            novo_x = float(pos_atual.get("distancia_x_parede", 0.0)) + float(delta_x)
            novo_y = float(y_absoluto) if y_absoluto is not None else (
                float(pos_atual.get("afastamento_parede", 0.0)) + float(delta_y)
            )
            novo_z = max(0.0, float(z_absoluto) if z_absoluto is not None else (
                float(pos_atual.get("elevacao_z", 0.0)) + float(delta_z)
            ))
            nova_rot = float(rotacao_absoluta) if rotacao_absoluta is not None else (
                float(pos_atual.get("rotacao_offset_graus", 0.0)) + float(delta_rotacao)
            )
            nova_rot = nova_rot % 360.0

            self.ancorar_modulo_na_parede(
                modulo_dict=mod,
                modulos_ativos=modulos_ativos,
                id_parede=id_par,
                distancia_x_parede=None if (aplicar_autosnap or trocou_parede) else novo_x,
                elevacao_z=novo_z,
                afastamento_parede=novo_y,
                rotacao_offset_graus=nova_rot,
                usar_autosnap=aplicar_autosnap or trocou_parede
            )
            modificados.append(mod)

        return modificados

    def recalcular_todos_modulos(self, modulos_ativos: Dict[str, Dict[str, Any]]) -> None:
        """Recalcula a posição global de todos os módulos quando as paredes mudam."""
        for m_id in sorted(modulos_ativos.keys()):
            mod = modulos_ativos[m_id]
            pos_ant = mod.get("posicionamento_ambiente", {})
            self.ancorar_modulo_na_parede(
                modulo_dict=mod,
                modulos_ativos=modulos_ativos,
                id_parede=pos_ant.get("id_parede"),
                distancia_x_parede=pos_ant.get("distancia_x_parede"),
                elevacao_z=pos_ant.get("elevacao_z"),
                afastamento_parede=pos_ant.get("afastamento_parede", 0.0),
                rotacao_offset_graus=pos_ant.get("rotacao_offset_graus", 0.0),
                usar_autosnap=False
            )

    def auditar_interferencias_obra(self, modulos_ativos: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Audita todo o ambiente verificando interferências entre a marcenaria e a obra:
        1. Módulos bloqueando Portas de Passagem.
        2. Módulos invadindo o vão de Janelas.
        3. Balcões com Fundo Costa fechado posicionados na frente de Pontos de Água/Gás.
        """
        alertas: List[str] = []

        for mod in modulos_ativos.values():
            pos = mod.get("posicionamento_ambiente") or {}
            id_par = pos.get("id_parede")
            if not id_par or id_par == "LIVRE":
                continue

            parede = self.construtor_paredes.buscar_parede(id_par)
            if not parede or parede.id_parede != id_par:
                continue

            mx1 = float(pos.get("distancia_x_parede", 0.0))
            mx2 = mx1 + float(mod["dimensoes_ocupadas"]["largura_x"])
            mz1 = float(pos.get("elevacao_z", 0.0))
            mz2 = mz1 + float(mod["dimensoes_ocupadas"]["altura_y"])
            fam = mod.get("familia", "")

            for el in parede.elementos:
                ex1 = el.distancia_x
                ex2 = ex1 + el.largura_x
                ez1 = el.elevacao_z
                ez2 = ez1 + el.altura_z

                sobrepoe_x = (mx1 < ex2 - 5.0) and (mx2 > ex1 + 5.0)
                sobrepoe_z = (mz1 < ez2 - 5.0) and (mz2 > ez1 + 5.0)

                if sobrepoe_x and sobrepoe_z:
                    if el.tipo == "PORTA":
                        alertas.append(
                            f"🚨 COLISÃO: Item #{mod['id_modulo']} está bloqueando a '{el.nome}' na Parede {id_par}!"
                        )
                    elif el.tipo == "JANELA" and fam != "MODULO_BANCADA_PEDRA":
                        alertas.append(
                            f"⚠️ JANELA: Item #{mod['id_modulo']} invade a '{el.nome}' (Peitoril Z={ez1:.0f}mm) na Parede {id_par}!"
                        )
                    elif el.tipo in ("PONTO_AGUA", "PONTO_GAS") and fam == "MODULO_INFERIOR":
                        tem_fundo_fechado = any(
                            p.get("categoria_industrial") == "fundo_costa"
                            for p in mod.get("lista_de_pecas", [])
                        )
                        if tem_fundo_fechado:
                            icone = "🚰 HIDRÁULICA" if el.tipo == "PONTO_AGUA" else "🔥 GÁS"
                            alertas.append(
                                f"{icone}: O '{el.nome}' (X={ex1:.0f}mm) está atrás do Balcão #{mod['id_modulo']}, que está COM FUNDO fechado!"
                            )

        return alertas