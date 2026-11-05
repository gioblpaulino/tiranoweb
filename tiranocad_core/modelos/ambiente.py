# =============================================================================
# ARQUIVO: tiranocad_core/modelos/ambiente.py
# RESPONSABILIDADE: Modelar as Paredes 2D/3D do Ambiente, Esquadrias (Janelas,
# Portas de Passagem) e Pontos de Instalação (Água/Esgoto, Gás e Tomadas).
# =============================================================================

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple
from tiranocad_core.modelos.entidades import ErroGeometriaCAD


class ElementoParede:
    """
    Representa um elemento arquitetônico ou ponto de instalação na parede:
    - 'JANELA': Esquadria com largura, altura e elevação (peitoril).
    - 'PORTA': Porta de passagem (elevação Z = 0).
    - 'PONTO_AGUA': Ponto hidráulico de água/esgoto (ex: pia/lava-louças).
    - 'PONTO_GAS': Ponto de gás encanado (ex: cooktop/forno).
    - 'PONTO_TOMADA': Ponto elétrico / tomada de força 110V/220V.
    """

    def __init__(
        self,
        tipo: str,
        distancia_x: float,
        elevacao_z: float,
        largura_x: float,
        altura_z: float,
        nome: Optional[str] = None,
        id_elemento: Optional[str] = None
    ):
        self.id_elemento = id_elemento or f"EL_{str(uuid.uuid4())[:6].upper()}"
        self.tipo = tipo.strip().upper()
        self.distancia_x = round(float(distancia_x), 2)
        self.elevacao_z = round(float(elevacao_z), 2)
        self.largura_x = round(float(largura_x), 2)
        self.altura_z = round(float(altura_z), 2)
        self.nome = nome or self.tipo

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id_elemento": self.id_elemento,
            "tipo": self.tipo,
            "nome": self.nome,
            "distancia_x": self.distancia_x,
            "elevacao_z": self.elevacao_z,
            "largura_x": self.largura_x,
            "altura_z": self.altura_z
        }


class ParedeAmbiente:
    """Representa um segmento de parede física no espaço 2D/3D."""

    def __init__(
        self,
        id_parede: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        pe_direito: float = 2700.0,
        espessura: float = 150.0,
        nome: Optional[str] = None
    ):
        self.id_parede = id_parede
        self.x1 = round(float(x1), 2)
        self.y1 = round(float(y1), 2)
        self.x2 = round(float(x2), 2)
        self.y2 = round(float(y2), 2)
        self.pe_direito = round(float(pe_direito), 2)
        self.espessura = round(float(espessura), 2)

        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        self.comprimento = round(math.hypot(dx, dy), 2)

        if self.comprimento < 100.0:
            raise ErroGeometriaCAD(
                f"🚨 Parede '{id_parede}' muito curta ({self.comprimento}mm). Mínimo permitido: 100mm."
            )

        self.angulo_rad = math.atan2(dy, dx)
        self.angulo_graus = round(math.degrees(self.angulo_rad), 2)
        self.nome = nome or f"Parede {id_parede} ({self.comprimento:.0f}mm)"
        self.elementos: List[ElementoParede] = []

    @property
    def vetor_direcao(self) -> Tuple[float, float]:
        return (math.cos(self.angulo_rad), math.sin(self.angulo_rad))

    @property
    def vetor_normal_interno(self) -> Tuple[float, float]:
        return (-math.sin(self.angulo_rad), math.cos(self.angulo_rad))

    def adicionar_elemento(
        self,
        tipo: str,
        distancia_x: float,
        elevacao_z: float,
        largura_x: float,
        altura_z: float,
        nome: Optional[str] = None,
        id_elemento: Optional[str] = None
    ) -> ElementoParede:
        el = ElementoParede(
            tipo=tipo,
            distancia_x=max(0.0, min(self.comprimento - largura_x, distancia_x)),
            elevacao_z=max(0.0, min(self.pe_direito - altura_z, elevacao_z)),
            largura_x=largura_x,
            altura_z=altura_z,
            nome=nome,
            id_elemento=id_elemento
        )
        self.elementos.append(el)
        return el

    def to_dict(self) -> Dict[str, Any]:
        ux, uy = self.vetor_direcao
        nx, ny = self.vetor_normal_interno
        return {
            "id_parede": self.id_parede,
            "nome": self.nome,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "comprimento": self.comprimento,
            "pe_direito": self.pe_direito,
            "espessura": self.espessura,
            "angulo_graus": self.angulo_graus,
            "vetor_direcao": {"ux": round(ux, 6), "uy": round(uy, 6)},
            "vetor_normal_interno": {"nx": round(nx, 6), "ny": round(ny, 6)},
            "elementos": [el.to_dict() for el in self.elementos]
        }


class ConstrutorParedes:
    """Construtor de polilinhas de paredes (Estilo Promob 2D)."""

    def __init__(self):
        self.paredes: List[ParedeAmbiente] = []
        self.pe_direito_padrao: float = 2700.0
        self.espessura_padrao: float = 150.0

    def limpar_paredes(self) -> None:
        self.paredes.clear()

    def _proximo_id_parede(self) -> str:
        letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        idx = len(self.paredes)
        return letras[idx] if idx < len(letras) else f"P{idx + 1}"

    def iniciar_parede_origem(
        self,
        comprimento: float,
        angulo_graus: float = 0.0,
        x_ini: float = 0.0,
        y_ini: float = 0.0,
        pe_direito: Optional[float] = None,
        espessura: Optional[float] = None
    ) -> ParedeAmbiente:
        rad = math.radians(angulo_graus)
        x_fim = x_ini + comprimento * math.cos(rad)
        y_fim = y_ini + comprimento * math.sin(rad)

        id_p = self._proximo_id_parede()
        nova = ParedeAmbiente(
            id_parede=id_p,
            x1=x_ini,
            y1=y_ini,
            x2=x_fim,
            y2=y_fim,
            pe_direito=pe_direito or self.pe_direito_padrao,
            espessura=espessura or self.espessura_padrao
        )
        self.paredes.append(nova)
        return nova

    def adicionar_segmento_continuo(
        self,
        comprimento: float,
        angulo_graus: float,
        pe_direito: Optional[float] = None,
        espessura: Optional[float] = None
    ) -> ParedeAmbiente:
        if not self.paredes:
            return self.iniciar_parede_origem(comprimento, angulo_graus, 0.0, 0.0, pe_direito, espessura)

        ultima = self.paredes[-1]
        return self.iniciar_parede_origem(
            comprimento=comprimento,
            angulo_graus=angulo_graus,
            x_ini=ultima.x2,
            y_ini=ultima.y2,
            pe_direito=pe_direito,
            espessura=espessura
        )

    def adicionar_parede_por_pontos(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        pe_direito: Optional[float] = None,
        espessura: Optional[float] = None,
        nome: Optional[str] = None
    ) -> ParedeAmbiente:
        id_p = self._proximo_id_parede()
        nova = ParedeAmbiente(
            id_parede=id_p,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            pe_direito=pe_direito or self.pe_direito_padrao,
            espessura=espessura or self.espessura_padrao,
            nome=nome
        )
        self.paredes.append(nova)
        return nova

    def gerar_preset_ambiente(
        self,
        formato: str = "L",
        larg_a: float = 3600.0,
        larg_b: float = 2600.0,
        larg_c: float = 3600.0
    ) -> List[ParedeAmbiente]:
        self.limpar_paredes()
        f = formato.strip().upper()

        if f == "I":
            self.iniciar_parede_origem(larg_a, 0.0, 0.0, 0.0)
        elif f == "L":
            self.iniciar_parede_origem(larg_a, 0.0, 0.0, 0.0)
            self.adicionar_segmento_continuo(larg_b, 90.0)
        elif f == "U":
            self.iniciar_parede_origem(larg_b, -90.0, 0.0, larg_b)
            self.adicionar_segmento_continuo(larg_a, 0.0)
            self.adicionar_segmento_continuo(larg_c, 90.0)
        else:
            self.iniciar_parede_origem(larg_a, 0.0, 0.0, 0.0)

        return self.paredes

    def buscar_parede(self, id_parede: str) -> Optional[ParedeAmbiente]:
        for p in self.paredes:
            if p.id_parede == id_parede:
                return p
        return self.paredes[0] if self.paredes else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_paredes": len(self.paredes),
            "pe_direito_padrao": self.pe_direito_padrao,
            "espessura_padrao": self.espessura_padrao,
            "paredes": [p.to_dict() for p in self.paredes]
        }