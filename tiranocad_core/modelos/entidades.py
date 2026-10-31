# =============================================================================
# ARQUIVO: tiranocad_core/modelos/entidades.py
# RESPONSABILIDADE: Modelar Furos, Rasgos, Fitas de Borda e Peças com auditoria
# Fail-Fast e cálculo automático da geometria 3D das usinagens para o Web CAD.
# =============================================================================

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


class ErroGeometriaCAD(Exception):
    """Exceção disparada imediatamente quando uma peça ou usinagem viola leis físicas."""
    pass


@dataclass
class Furo:
    """Representa uma furação nas coordenadas 2D da peça e sua projeção 3D."""
    x: float
    y: float
    diametro: float
    profundidade: float
    face_normal: str = "FACE_INTERNA"
    tipo_furo: str = "ESTRUTURAL"
    id_furo: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self, projecao_3d: Dict[str, Any] = None) -> Dict[str, Any]:
        dados = {
            "id_furo": self.id_furo,
            "x": round(float(self.x), 2),
            "y": round(float(self.y), 2),
            "diametro": round(float(self.diametro), 2),
            "profundidade": round(float(self.profundidade), 2),
            "face_normal": self.face_normal,
            "tipo_furo": self.tipo_furo
        }
        if projecao_3d:
            dados["geometria_3d"] = projecao_3d
        return dados


@dataclass
class Rasgo:
    """Representa um canal/rasgo no plano 2D da peça e sua caixa 3D para renderização."""
    x: float
    y: float
    largura: float
    comprimento: float
    profundidade: float
    direcao: str  # "H" ou "V"
    tipo: str = "CANAL_FUNDO"

    def to_dict(self, projecao_3d: Dict[str, Any] = None) -> Dict[str, Any]:
        sufixo = "_H" if self.direcao.upper() == "H" else "_V"
        tipo_formatado = self.tipo if self.tipo.endswith(sufixo) else f"{self.tipo}{sufixo}"
        dados = {
            "x": round(float(self.x), 2),
            "y": round(float(self.y), 2),
            "pos_x": round(float(self.x), 2),
            "pos_y": round(float(self.y), 2),
            "largura": round(float(self.largura), 2),
            "comprimento": round(float(self.comprimento), 2),
            "profundidade": round(float(self.profundidade), 2),
            "direcao": self.direcao.upper(),
            "tipo": tipo_formatado
        }
        if projecao_3d:
            dados["geometria_3d"] = projecao_3d
        return dados


@dataclass
class FitasBorda:
    """Define explicitamente quais lados da peça 2D recebem fita de borda."""
    base: bool = False      # Y = 0
    direita: bool = False   # X = comprimento_corte
    topo: bool = False      # Y = largura_corte
    esquerda: bool = False  # X = 0

    def to_dict(self) -> Dict[str, bool]:
        return {
            "base": self.base,
            "direita": self.direita,
            "topo": self.topo,
            "esquerda": self.esquerda
        }


class Peca:
    """
    Entidade central de uma peça de marcenaria.
    Converte automaticamente suas usinagens 2D em coordenadas 3D relativas
    ao centro da peça para renderização fiel no navegador (Three.js).
    """

    def __init__(
        self,
        categoria_industrial: str,
        nome_comercial: str,
        dim_3d: Tuple[float, float, float],
        pos_3d: Tuple[float, float, float],
        material: str,
        id_pai: str = "001",
        tem_veio: bool = False,
        espelhar_cam_x: bool = False
    ):
        self.id_peca: str = str(uuid.uuid4())
        self.id_pai: str = id_pai
        self.categoria_industrial: str = categoria_industrial
        self.nome_comercial: str = nome_comercial
        self.material: str = material
        self.tem_veio: bool = tem_veio
        self.espelhar_cam_x: bool = espelhar_cam_x

        dx, dy, dz = float(dim_3d[0]), float(dim_3d[1]), float(dim_3d[2])
        if dx <= 0 or dy <= 0 or dz <= 0:
            raise ErroGeometriaCAD(
                f"🚨 Dimensão inválida na peça '{nome_comercial}' ({categoria_industrial}): "
                f"x={dx}, y={dy}, z={dz}."
            )

        self.dimensoes_3d = {"x": round(dx, 2), "y": round(dy, 2), "z": round(dz, 2)}
        self.posicao_relativa = {
            "pos_x": round(float(pos_3d[0]), 2),
            "pos_y": round(float(pos_3d[1]), 2),
            "pos_z": round(float(pos_3d[2]), 2)
        }

        self.espessura, self.dim_x_2d, self.dim_y_2d, self.orientacao_3d = self._planificar_dimensoes(dx, dy, dz)

        self.furos: List[Furo] = []
        self.rasgos: List[Rasgo] = []
        self.fitas: FitasBorda = FitasBorda()
        self.cor_fita_borda: str = material
        self.avisos_auditoria: List[str] = []

    @staticmethod
    def _planificar_dimensoes(dx: float, dy: float, dz: float) -> Tuple[float, float, float, str]:
        """Identifica a orientação espacial da peça no 3D e extrai suas cotas 2D."""
        esp = min(dx, dy, dz)
        if esp == dz:
            return esp, dx, dy, "HORIZONTAL_XY"      # Base, Tampo, Prateleira, Sarrafo
        elif esp == dx:
            return esp, dy, dz, "VERTICAL_YZ"        # Lateral Esq/Dir, Divisória, Lateral Gaveta
        else:
            return esp, dx, dz, "FRONTAL_XZ"         # Porta, Frente Gaveta, Contra-Frente, Traseira, Fundo

    def adicionar_furo(
        self,
        x: float,
        y: float,
        diametro: float,
        profundidade: float,
        face: str = "FACE_INTERNA",
        tipo_furo: str = "ESTRUTURAL"
    ) -> None:
        if not (0.0 <= x <= self.dim_x_2d) or not (0.0 <= y <= self.dim_y_2d):
            raise ErroGeometriaCAD(
                f"🚨 [FURO FORA DA PEÇA] Tentativa de furar em (X={x}, Y={y}) na peça "
                f"'{self.nome_comercial}' [{self.id_pai}], que mede {self.dim_x_2d}x{self.dim_y_2d}mm!"
            )
        if profundidade > self.espessura + 1.0:
            raise ErroGeometriaCAD(
                f"🚨 [FURO PROFUNDO DEMAIS] Profundidade {profundidade}mm excede a espessura "
                f"({self.espessura}mm) na peça '{self.nome_comercial}'."
            )
        self.furos.append(
            Furo(x=x, y=y, diametro=diametro, profundidade=profundidade, face_normal=face, tipo_furo=tipo_furo)
        )

    def adicionar_rasgo(
        self,
        x: float,
        y: float,
        largura: float,
        comprimento: float,
        profundidade: float,
        direcao: str,
        tipo: str = "CANAL_FUNDO"
    ) -> None:
        direcao = direcao.upper()
        if direcao not in ("H", "V"):
            raise ErroGeometriaCAD(f"🚨 Direção de rasgo inválida ('{direcao}') na peça '{self.nome_comercial}'.")

        if profundidade >= self.espessura:
            raise ErroGeometriaCAD(
                f"🚨 [RASGO ATRAVESSOU A PEÇA] O rasgo de {profundidade}mm partiria a peça "
                f"'{self.nome_comercial}' ({self.espessura}mm) ao meio!"
            )
        self.rasgos.append(
            Rasgo(x=x, y=y, largura=largura, comprimento=comprimento, profundidade=profundidade, direcao=direcao, tipo=tipo)
        )

    def _projetar_furo_3d(self, furo: Furo) -> Dict[str, Any]:
        """
        Calcula a coordenada 3D exata (X, Y, Z) do furo no espaço do módulo.
        Se a peça for frontal espelhada (ex: Porta Direita), projeta o furo
        no lado direito real do espaço 3D, mantendo a cota padrão para o CAM.
        """
        px, py, pz = self.posicao_relativa["pos_x"], self.posicao_relativa["pos_y"], self.posicao_relativa["pos_z"]
        esp = self.espessura

        if self.orientacao_3d == "HORIZONTAL_XY":
            # Peça deitada (Base, Tampo, Prateleira, Sarrafo): furo vertical (eixo Z)
            x_local = (self.dim_x_2d - furo.x) if self.espelhar_cam_x else furo.x
            z_furo = pz + (esp / 2.0)
            return {"x": round(px + x_local, 2), "y": round(py + furo.y, 2), "z": round(z_furo, 2), "eixo": "Z"}

        elif self.orientacao_3d == "VERTICAL_YZ":
            # Peça lateral em pé (Lateral Esq/Dir, Divisória, Lateral Gaveta): furo horizontal (eixo X)
            # No 3D, a profundidade Y vai de 0 (frente) até dim_x_2d (fundo)
            x_furo = px + (esp / 2.0)
            return {"x": round(x_furo, 2), "y": round(py + furo.x, 2), "z": round(pz + furo.y, 2), "eixo": "X"}

        else:
            # Peça frontal em pé (Porta Esquerda, Porta Direita, Frente Gaveta): furo frontal (eixo Y)
            # Se for Porta Direita (espelhar_cam_x = True), o caneco fica na borda direita no 3D!
            x_local = (self.dim_x_2d - furo.x) if self.espelhar_cam_x else furo.x
            y_furo = py + (esp / 2.0)
            return {"x": round(px + x_local, 2), "y": round(y_furo, 2), "z": round(pz + furo.y, 2), "eixo": "Y"}
        
    def _projetar_rasgo_3d(self, rasgo: Rasgo) -> Dict[str, Any]:
        """Calcula a caixa 3D (pos_x, pos_y, pos_z e dx, dy, dz) do rasgo na face interna da peça."""
        px, py, pz = self.posicao_relativa["pos_x"], self.posicao_relativa["pos_y"], self.posicao_relativa["pos_z"]
        esp = self.espessura
        cat = self.categoria_industrial.lower()

        if self.orientacao_3d == "HORIZONTAL_XY":
            # Ex: Base Inferior (rasgo na face superior) ou Base Superior (rasgo na face inferior)
            eh_teto = "superior" in cat or "teto" in cat
            pos_z_r = pz if eh_teto else (pz + esp - rasgo.profundidade)
            if rasgo.direcao == "H":
                return {
                    "pos_x": round(px + rasgo.x, 2),
                    "pos_y": round(py + rasgo.y, 2),
                    "pos_z": round(pos_z_r, 2),
                    "dx": round(rasgo.comprimento, 2),
                    "dy": round(rasgo.largura, 2),
                    "dz": round(rasgo.profundidade, 2)
                }
            else:
                return {
                    "pos_x": round(px + rasgo.x, 2),
                    "pos_y": round(py + rasgo.y, 2),
                    "pos_z": round(pos_z_r, 2),
                    "dx": round(rasgo.largura, 2),
                    "dy": round(rasgo.comprimento, 2),
                    "dz": round(rasgo.profundidade, 2)
                }

        elif self.orientacao_3d == "VERTICAL_YZ":
            # Ex: Lateral Esquerda (rasgo na face direita +X) ou Lateral Direita (rasgo na face esquerda -X)
            eh_direita = "direita" in cat or self.espelhar_cam_x
            pos_x_r = px if eh_direita else (px + esp - rasgo.profundidade)
            if rasgo.direcao == "V":
                return {
                    "pos_x": round(pos_x_r, 2),
                    "pos_y": round(py + rasgo.x, 2),
                    "pos_z": round(pz + rasgo.y, 2),
                    "dx": round(rasgo.profundidade, 2),
                    "dy": round(rasgo.largura, 2),
                    "dz": round(rasgo.comprimento, 2)
                }
            else:
                # Ex: Lateral de Gaveta (Rasgo Horizontal correndo ao longo da profundidade Y)
                return {
                    "pos_x": round(pos_x_r, 2),
                    "pos_y": round(py + rasgo.x, 2),
                    "pos_z": round(pz + rasgo.y, 2),
                    "dx": round(rasgo.profundidade, 2),
                    "dy": round(rasgo.comprimento, 2),
                    "dz": round(rasgo.largura, 2)
                }

        else:
            # Peça Frontal/Traseira (Contra-Frente ou Traseira de Gaveta)
            eh_traseira = "traseira" in cat
            pos_y_r = py if eh_traseira else (py + esp - rasgo.profundidade)
            return {
                "pos_x": round(px + rasgo.x, 2),
                "pos_y": round(pos_y_r, 2),
                "pos_z": round(pz + rasgo.y, 2),
                "dx": round(rasgo.comprimento, 2),
                "dy": round(rasgo.profundidade, 2),
                "dz": round(rasgo.largura, 2)
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id_peca": self.id_peca,
            "id_pai": self.id_pai,
            "id_vinculo_structure": None,
            "categoria_industrial": self.categoria_industrial,
            "nome_comercial": self.nome_comercial,
            "material": self.material,
            "tem_veio": self.tem_veio,
            "espelhar_cam_x": self.espelhar_cam_x,
            "orientacao_3d": self.orientacao_3d,
            "dimensoes": self.dimensoes_3d,
            "dimensoes_2d_planificadas": {
                "largura_x": round(self.dim_x_2d, 2),
                "altura_y": round(self.dim_y_2d, 2),
                "espessura": round(self.espessura, 2)
            },
            "posicao_relativa": self.posicao_relativa,
            "fitas_borda": self.fitas.to_dict(),
            "cor_fita_borda": self.cor_fita_borda,
            "usinagens": {
                "furos": [f.to_dict(self._projetar_furo_3d(f)) for f in self.furos],
                "rasgos": [r.to_dict(self._projetar_rasgo_3d(r)) for r in self.rasgos]
            }
        }