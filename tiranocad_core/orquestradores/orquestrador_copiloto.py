# =============================================================================
# ARQUIVO: tiranocad_core/orquestradores/orquestrador_copiloto.py
# RESPONSABILIDADE: Traduzir comandos em português para operações da árvore
# NoEspacial, suportando Divisões Verticais, Divisões Horizontais (Torre Quente),
# Gavetas Externas, Gavetas Internas, Sapateiras, Porta-Tempero e Basculantes.
# =============================================================================

import re
from typing import Any, Dict, List


class OrquestradorCopiloto:
    """
    Tradutor semântico de engenharia para o TiranoCAD.
    Converte pedidos em texto livre para comandos únicos e validados na árvore NoEspacial.
    """

    def interpretar_comando(self, texto_usuario: str) -> Dict[str, Any]:
        texto = texto_usuario.strip().lower()
        operacoes: List[Dict[str, Any]] = []
        dimensoes: Dict[str, float] = {}
        resumo_acoes: List[str] = []

        # 1. Deteção opcional de medidas globais na frase (Ex: "1200x700x550")
        padrao_medidas = re.search(r"(\d{3,4})\s*[xX*]\s*(\d{3,4})(?:\s*[xX*]\s*(\d{3,4}))?", texto)
        if padrao_medidas:
            dimensoes["largura_x"] = float(padrao_medidas.group(1))
            dimensoes["altura_y"] = float(padrao_medidas.group(2))
            if padrao_medidas.group(3):
                dimensoes["profundidade_z"] = float(padrao_medidas.group(3))
            resumo_acoes.append(f"Dimensões ajustadas ({dimensoes})")

        # 2. CENÁRIO A: TORRE QUENTE / DIVISÃO HORIZONTAL (Embaixo / Meio / Cima)
        eh_torre_quente = any(t in texto for t in ["torre quente", "nicho", "embaixo", "em cima"])
        if eh_torre_quente:
            self._construir_plano_horizontal(texto, operacoes, resumo_acoes)
            return {
                "dimensoes_detectadas": dimensoes,
                "operacoes_internas": self._remover_operacoes_duplicadas(operacoes),
                "mensagem_copiloto": "🤖 Copiloto executou: " + " | ".join(resumo_acoes) + "."
            }

        # 3. CENÁRIO B: DIVISÃO VERTICAL (Ao meio ou com cota de Porta-Tempero)
        dividiu_vertical = any(
            termo in texto for termo in ["divid", "meio", "dois vãos", "2 vãos", "divisória", "divisoria"]
        ) or ("esquerda" in texto and "direita" in texto)

        if dividiu_vertical:
            cota_div = None
            match_cota_temp = re.search(r"tempero\s*(?:de\s*)?(\d{2,3})\s*(?:mm)?", texto)
            if match_cota_temp:
                cota_div = float(match_cota_temp.group(1))

            op_div: Dict[str, Any] = {"tipo": "DIVISORIA_VERTICAL", "id_vao": "raiz"}
            if cota_div:
                op_div["posicao_x"] = cota_div
                resumo_acoes.append(f"Divisória Vertical posicionada em X={cota_div:.0f}mm")
            else:
                resumo_acoes.append("Vão principal dividido ao meio por Divisória Vertical")
            operacoes.append(op_div)

            trechos = re.split(r"\b(?:e\b|,|;)", texto)
            for trecho in trechos:
                id_alvo = "raiz"
                if re.search(r"\b(?:na|da|no|do)\s+esquerd[ao]", trecho):
                    id_alvo = "raiz.0"
                elif re.search(r"\b(?:na|da|no|do)\s+direit[ao]", trecho):
                    id_alvo = "raiz.1"
                elif "esquerda" in trecho and "porta" not in trecho:
                    id_alvo = "raiz.0"
                elif "direita" in trecho and "porta" not in trecho:
                    id_alvo = "raiz.1"

                self._extrair_componentes_do_trecho(trecho, id_alvo, operacoes, resumo_acoes)
        else:
            self._extrair_componentes_do_trecho(texto, "raiz", operacoes, resumo_acoes)

        operacoes_limpas = self._remover_operacoes_duplicadas(operacoes)
        mensagem = (
            "🤖 Copiloto executou: " + " | ".join(resumo_acoes) + "."
            if resumo_acoes else "Estrutura base da caixaria mantida."
        )

        return {
            "dimensoes_detectadas": dimensoes,
            "operacoes_internas": operacoes_limpas,
            "mensagem_copiloto": mensagem
        }

    def _construir_plano_horizontal(
        self,
        texto: str,
        operacoes: List[Dict[str, Any]],
        resumo_acoes: List[str]
    ) -> None:
        """Monta a árvore de divisões horizontais para Torres Quentes ou Armários Mistos."""
        alt_base = 720.0
        operacoes.append({"tipo": "DIVISORIA_HORIZONTAL", "id_vao": "raiz", "posicao_z": alt_base})
        resumo_acoes.append(f"Vão Inferior estruturado com {alt_base:.0f}mm")

        tem_nicho_meio = any(t in texto for t in ["nicho", "meio", "forno", "micro"])
        id_vao_topo = "raiz.1"

        if tem_nicho_meio:
            match_alt_nicho = re.search(r"nicho\s*(?:de\s*)?(\d{3})\s*(?:mm)?", texto)
            alt_nicho = float(match_alt_nicho.group(1)) if match_alt_nicho else 450.0
            operacoes.append({"tipo": "DIVISORIA_HORIZONTAL", "id_vao": "raiz.1", "posicao_z": alt_nicho})
            resumo_acoes.append(f"Nicho Central aberto com {alt_nicho:.0f}mm")
            id_vao_topo = "raiz.1.1"

        trechos = re.split(r"\b(?:e\b|,|;)", texto)
        for trecho in trechos:
            if any(p in trecho for p in ["embaixo", "inferior", "base"]):
                self._extrair_componentes_do_trecho(trecho, "raiz.0", operacoes, resumo_acoes)
            elif any(p in trecho for p in ["em cima", "superior", "topo"]):
                self._extrair_componentes_do_trecho(trecho, id_vao_topo, operacoes, resumo_acoes)
            elif "gaveta" in trecho or "sapateira" in trecho:
                self._extrair_componentes_do_trecho(trecho, "raiz.0", operacoes, resumo_acoes)
            elif "porta" in trecho or "prateleira" in trecho:
                self._extrair_componentes_do_trecho(trecho, id_vao_topo, operacoes, resumo_acoes)

    def _extrair_componentes_do_trecho(
        self,
        trecho: str,
        id_vao_alvo: str,
        operacoes: List[Dict[str, Any]],
        resumo_acoes: List[str]
    ) -> None:
        nome_legivel = {
            "raiz": "Vão Principal",
            "raiz.0": "Vão Esquerdo/Inferior",
            "raiz.1": "Vão Direito/Superior",
            "raiz.1.0": "Nicho Central",
            "raiz.1.1": "Vão Superior"
        }.get(id_vao_alvo, f"Vão {id_vao_alvo}")

        # A) Porta-Tempero / Porta-Óleo
        if any(t in trecho for t in ["tempero", "oleo", "óleo"]):
            operacoes.append({"tipo": "PORTA_TEMPERO", "id_vao": id_vao_alvo})
            resumo_acoes.append(f"Porta-Tempero extraível no {nome_legivel}")
            return

        # B) Gavetas (Internas vs Externas — Bloco Único Unificado!)
        match_gav = re.search(r"(\d+)\s*gaveta", trecho)
        if "interna" in trecho and ("gaveta" in trecho or "gaveteiro" in trecho):
            qtd_g = int(match_gav.group(1)) if match_gav else 3
            operacoes.append({"tipo": "GAVETEIRO_INTERNO", "quantidade": qtd_g, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"{qtd_g} gaveta(s) interna(s) c/ espaçador no {nome_legivel}")
        elif match_gav:
            qtd_gav = int(match_gav.group(1))
            operacoes.append({"tipo": "GAVETEIRO", "quantidade": qtd_gav, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"{qtd_gav} gavetas no {nome_legivel}")
        elif "gaveteiro" in trecho:
            operacoes.append({"tipo": "GAVETEIRO", "quantidade": 4, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"4 gavetas no {nome_legivel}")

        # C) Sapateiras Corrediças
        if "sapateira" in trecho:
            match_sap = re.search(r"(\d+)\s*sapateira", trecho)
            qtd_s = int(match_sap.group(1)) if match_sap else 2
            operacoes.append({"tipo": "SAPATEIRA", "quantidade": qtd_s, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"{qtd_s} sapateira(s) corrediça(s) no {nome_legivel}")

        # D) Prateleiras
        match_prat = re.search(r"(\d+)\s*prateleira", trecho)
        if match_prat:
            qtd_prat = int(match_prat.group(1))
            eh_fixa = "fixa" in trecho
            operacoes.append({"tipo": "PRATELEIRAS", "quantidade": qtd_prat, "fixas": eh_fixa, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"{qtd_prat} prateleira(s) no {nome_legivel}")
        elif "prateleira" in trecho:
            eh_fixa = "fixa" in trecho
            operacoes.append({"tipo": "PRATELEIRAS", "quantidade": 1, "fixas": eh_fixa, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"1 prateleira no {nome_legivel}")

        # E) Portas (Basculantes vs Giro — Bloco Único Unificado!)
        if "basculante" in trecho:
            match_basc = re.search(r"(\d+)\s*(?:porta\s*)?basculante", trecho)
            qtd_b = int(match_basc.group(1)) if match_basc else 1
            operacoes.append({"tipo": "PORTAS_BASCULANTES", "quantidade": qtd_b, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"{qtd_b} porta(s) basculante(s) no {nome_legivel}")
        elif "porta" in trecho:
            trecho_sem_local = re.sub(r"\b(?:na|da|no|do)\s+(?:esquerd[ao]|direit[ao])", "", trecho)
            if any(u in trecho_sem_local for u in ["1 porta", "uma porta", "porta simples", "porta direita", "porta esquerda"]):
                abertura = "DIREITA" if "direita" in trecho_sem_local else "ESQUERDA"
            else:
                abertura = "DUPLA"

            operacoes.append({"tipo": "PORTAS_GIRO", "abertura": abertura, "id_vao": id_vao_alvo})
            resumo_acoes.append(f"Porta ({abertura}) no {nome_legivel}")

    @staticmethod
    def _remover_operacoes_duplicadas(operacoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Garante que nunca sejam enviadas duas operações de ocupação conflitantes
        para o mesmo id_vao por erro de digitação na frase.
        """
        resultado: List[Dict[str, Any]] = []
        chaves_vistas = set()

        for op in operacoes:
            chave = (op.get("tipo"), op.get("id_vao"), op.get("alvo_semantica"))
            if chave not in chaves_vistas:
                chaves_vistas.add(chave)
                resultado.append(op)
        return resultado