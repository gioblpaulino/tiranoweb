# =============================================================================
# ARQUIVO: tiranocad_core/modelos/ambiente.py
# RESPONSABILIDADE: Modelar a geometria arquitetônica do ambiente (Paredes por
# vértices ou comprimento/ângulo, Pé-Direito, Espessura, Portas/Janelas) e
# calcular o posicionamento magnético (Auto-Snap) dos módulos nas paredes.
# =============================================================================

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from tiranocad_core.modelos.entidades import ErroGeometriaCAD


@dataclass
class AberturaParede:
    """
    Representa uma porta de passagem, janela ou ponto hidráulico/elétrico
    posicionado ao longo de uma parede específica.
    """
    tipo: str                  # "PORTA", "JANELA", "PONTO_AGUA", "TOMADA"
    distancia_inicio_mm: float # Distância X a partir do ponto inicial da parede
    largura_mm: float
    altura_mm: float
    peitoril_z_mm: float = 0.0 # Altura do chão até a base (0 para portas, ex: 1100 para janelas)
    id_abertura: str = field(default_factory=lambda: f"ab_{str(uuid.uuid4())[:6]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id_abertura": self.id_abertura,
            "tipo": self.tipo.upper(),
            "distancia_inicio_mm": round(float(self.distancia_inicio_mm), 2),
            "largura_mm": round(float(self.largura_mm), 2),
            "altura_mm": round(float(self.altura_mm), 2),
            "peitoril_z_mm": round(float(self.peitoril_z_mm), 2)
        }


class Parede:
    """
    Representa um segmento de parede definido por um ponto inicial (x1, y1) e
    um ponto final (x2, y2) na planta baixa 2D, com espessura e pé-direito.
    Calcula automaticamente comprimento, ângulo e vetores unitários para Auto-Snap.
    """

    def __init__(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        pe_direito: float = 2700.0,
        espessura: float = 150.0,
        nome: str = "Parede",
        id_parede: Optional[str] = None
    ):
        self.id_parede: str = id_parede or f"par_{str(uuid.uuid4())[:6]}"
        self.nome: str = nome

        self.x1: float = round(float(x1), 2)
        self.y1: float = round(float(y1), 2)
        self.x2: float = round(float(x2), 2)
        self.y2: float = round(float(y2), 2)

        self.pe_direito: float = round(float(pe_direito), 2)
        self.espessura: float = round(float(espessura), 2)
        self.aberturas: List[AberturaParede] = []

        if self.comprimento < 50.0:
            raise ErroGeometriaCAD(
                f"🚨 A '{self.nome}' é curta demais ({self.comprimento:.1f}mm). Mínimo exigido: 50mm."
            )
        if self.pe_direito < 500.0 or self.espessura <= 0.0:
            raise ErroGeometriaCAD(
                f"🚨 Parâmetros inválidos na '{self.nome}': Pé-Direito={self.pe_direito}mm, Espessura={self.espessura}mm."
            )

    @property
    def comprimento(self) -> float:
        """Comprimento interno útil da parede em milímetros."""
        return round(math.hypot(self.x2 - self.x1, self.y2 - self.y1), 2)

    @property
    def angulo_graus(self) -> float:
        """Ângulo da parede na planta baixa em graus (-180 a +180)."""
        ang = math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))
        return round(ang, 2)

    @property
    def vetor_direcao(self) -> Tuple[float, float]:
        """Vetor unitário (ux, uy) que corre ao longo da parede do início ao fim."""
        comp = self.comprimento
        return ((self.x2 - self.x1) / comp, (self.y2 - self.y1) / comp)

    @property
    def vetor_normal_interno(self) -> Tuple[float, float]:
        """
        Vetor unitário (nx, ny) que aponta para DENTRO do ambiente (90° à direita
        do sentido de desenho horário), indicando para onde a frente do móvel olha.
        """
        ux, uy = self.vetor_direcao
        return (-uy, ux)

    def redimensionar_por_comprimento_e_angulo(self, novo_comprimento: float, novo_angulo_graus: float) -> Tuple[float, float]:
        """
        Permite editar o comprimento ou o ângulo da parede mantendo (x1, y1) fixo
        e recalculando o ponto final (x2, y2) — ideal para edição via input na UI!
        """
        if novo_comprimento < 50.0:
            raise ErroGeometriaCAD("🚨 O comprimento da parede deve ser de pelo menos 50mm.")

        rad = math.radians(float(novo_angulo_graus))
        self.x2 = round(self.x1 + float(novo_comprimento) * math.cos(rad), 2)
        self.y2 = round(self.y1 + float(novo_comprimento) * math.sin(rad), 2)
        return self.x2, self.y2

    def adicionar_abertura(
        self,
        tipo: str,
        distancia_inicio_mm: float,
        largura_mm: float,
        altura_mm: float,
        peitoril_z_mm: float = 0.0
    ) -> AberturaParede:
        """Insere uma porta/janela e valida se ela cabe fisicamente na parede."""
        if distancia_inicio_mm < 0 or (distancia_inicio_mm + largura_mm) > self.comprimento:
            raise ErroGeometriaCAD(
                f"🚨 A abertura '{tipo}' ({largura_mm}mm em X={distancia_inicio_mm}mm) "
                f"ultrapassa o comprimento da '{self.nome}' ({self.comprimento}mm)!"
            )
        if (peitoril_z_mm + altura_mm) > self.pe_direito:
            raise ErroGeometriaCAD(
                f"🚨 A abertura '{tipo}' ultrapassa o pé-direito da '{self.nome}' ({self.pe_direito}mm)!"
            )
        ab = AberturaParede(
            tipo=tipo,
            distancia_inicio_mm=distancia_inicio_mm,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            peitoril_z_mm=peitoril_z_mm
        )
        self.aberturas.append(ab)
        return ab

    def calcular_transformacao_modulo(
        self,
        distancia_ao_longo_mm: float,
        elevacao_z_mm: float = 0.0,
        afastamento_parede_mm: float = 0.0
    ) -> Dict[str, float]:
        """
        Calcula a coordenada global 3D (x, y, z) e a rotação exata para posicionar
        um módulo encostado nesta parede a uma distância X do canto inicial.
        """
        ux, uy = self.vetor_direcao
        nx, ny = self.vetor_normal_interno

        pos_x = self.x1 + (ux * distancia_ao_longo_mm) + (nx * afastamento_parede_mm)
        pos_y = self.y1 + (uy * distancia_ao_longo_mm) + (ny * afastamento_parede_mm)

        return {
            "x_ambiente": round(pos_x, 2),
            "y_ambiente": round(pos_y, 2),
            "z_ambiente": round(float(elevacao_z_mm), 2),
            "rotacao_graus": self.angulo_graus
        }

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
            "angulo_graus": self.angulo_graus,
            "pe_direito": self.pe_direito,
            "espessura": self.espessura,
            "vetor_direcao": {"ux": round(ux, 4), "uy": round(uy, 4)},
            "vetor_normal_interno": {"nx": round(nx, 4), "ny": round(ny, 4)},
            "aberturas": [a.to_dict() for a in self.aberturas]
        }


class ConstrutorAmbiente:
    """
    Gerencia o conjunto de paredes da planta baixa e calcula o Auto-Snap
    (empilhamento lateral automático) dos módulos em cada parede.
    """

    def __init__(self, pe_direito_padrao: float = 2700.0, espessura_padrao: float = 150.0):
        self.pe_direito_padrao: float = float(pe_direito_padrao)
        self.espessura_padrao: float = float(espessura_padrao)
        self.paredes: List[Parede] = []

    def limpar_paredes(self) -> None:
        self.paredes.clear()

    def adicionar_parede_por_pontos(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        pe_direito: Optional[float] = None,
        espessura: Optional[float] = None,
        nome: Optional[str] = None
    ) -> Parede:
        """Cria uma parede a partir de dois pontos clicados na Planta Baixa 2D."""
        idx = len(self.paredes) + 1
        letra = chr(64 + idx) if idx <= 26 else str(idx)
        nova_parede = Parede(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            pe_direito=pe_direito or self.pe_direito_padrao,
            espessura=espessura or self.espessura_padrao,
            nome=nome or f"Parede {letra}"
        )
        self.paredes.append(nova_parede)
        return nova_parede

    def adicionar_segmento_continuo(
        self,
        comprimento: float,
        angulo_graus: float,
        pe_direito: Optional[float] = None,
        espessura: Optional[float] = None
    ) -> Parede:
        """
        Adiciona uma nova parede engatada automaticamente no ponto final (x2, y2)
        da última parede criada (estilo linha contínua do Promob!).
        """
        if not self.paredes:
            x_ini, y_ini = 0.0, 0.0
        else:
            ultima = self.paredes[-1]
            x_ini, y_ini = ultima.x2, ultima.y2

        rad = math.radians(float(angulo_graus))
        x_fim = round(x_ini + float(comprimento) * math.cos(rad), 2)
        y_fim = round(y_ini + float(comprimento) * math.sin(rad), 2)

        return self.adicionar_parede_por_pontos(x_ini, y_ini, x_fim, y_fim, pe_direito, espessura)

    def gerar_preset_ambiente(self, formato: str = "L", larg_a: float = 3500.0, larg_b: float = 2500.0) -> List[Parede]:
        """Gera plantas rápidas com 1 clique: Parede Reta ('I'), Canto em 'L' ou Cozinha em 'U'."""
        self.limpar_paredes()
        formato = formato.strip().upper()

        # Parede A (Fundo principal: da esquerda para a direita, ângulo 0°)
        self.adicionar_segmento_continuo(comprimento=larg_a, angulo_graus=0.0)

        if formato in ("L", "U"):
            # Parede B (Vira 90° vindo para a frente da sala)
            self.adicionar_segmento_continuo(comprimento=larg_b, angulo_graus=90.0)

        if formato == "U":
            # Parede C (Vira 180° fechando o U)
            self.adicionar_segmento_continuo(comprimento=larg_a, angulo_graus=180.0)

        return self.paredes

    def obter_parede(self, id_parede: str) -> Optional[Parede]:
        return next((p for p in self.paredes if p.id_parede == id_parede), None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pe_direito_padrao": self.pe_direito_padrao,
            "espessura_padrao": self.espessura_padrao,
            "total_paredes": len(self.paredes),
            "paredes": [p.to_dict() for p in self.paredes]
        }