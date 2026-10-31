# =============================================================================
# ARQUIVO: tiranocad_core/modelos/no_espacial.py
# RESPONSABILIDADE: Gerenciar a Árvore Binária Espacial (BSP Tree) dos vãos
# internos do móvel. Rastreia sub-vãos, componentes internos e peças vizinhas
# para furação automática e seleção interativa no Web CAD 3D.
# =============================================================================

from typing import Any, Dict, List, Optional
from tiranocad_core.modelos.entidades import ErroGeometriaCAD, Peca


class NoEspacial:
    """
    Representa um volume (vão livre) dentro do módulo 3D.
    Pode ser um nó folha (vão aberto ou ocupado por gavetas) ou um nó pai
    (dividido por prateleiras fixas ou divisórias verticais).
    """

    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        largura: float,
        profundidade: float,
        altura: float,
        nome_vao: str = "Vão Principal",
        id_vao: str = "raiz",
        vizinhos: Optional[Dict[str, Optional[Peca]]] = None
    ):
        if largura <= 0 or profundidade <= 0 or altura <= 0:
            raise ErroGeometriaCAD(
                f"🚨 [VÃO INVÁLIDO] O '{nome_vao}' ({id_vao}) ficou com medidas inválidas: "
                f"Largura={largura}mm, Profundidade={profundidade}mm, Altura={altura}mm."
            )

        self.id_vao: str = id_vao
        self.nome_vao: str = nome_vao

        self.x: float = round(float(x), 2)
        self.y: float = round(float(y), 2)
        self.z: float = round(float(z), 2)
        self.largura: float = round(float(largura), 2)
        self.profundidade: float = round(float(profundidade), 2)
        self.altura: float = round(float(altura), 2)

        self.vizinhos: Dict[str, Optional[Peca]] = vizinhos or {
            "esquerda": None,
            "direita": None,
            "base": None,
            "topo": None
        }

        self.tipo_divisao: Optional[str] = None  # "VERTICAL" ou "HORIZONTAL"
        self.peca_divisora: Optional[Peca] = None
        self.filhos: List["NoEspacial"] = []

        self.ocupacao_interna: Optional[str] = None
        self.pecas_internas: List[Peca] = []

    @property
    def eh_folha(self) -> bool:
        """Retorna True se o vão estiver livre de divisórias ou prateleiras estruturais."""
        return len(self.filhos) == 0

    def dividir_verticalmente(
        self,
        peca_divisoria: Peca,
        cota_x_relativa: Optional[float] = None
    ) -> List["NoEspacial"]:
        """Fatia o vão em Esquerdo (.0) e Direito (.1) usando uma Divisória Vertical."""
        if not self.eh_folha:
            raise ErroGeometriaCAD(f"🚨 O '{self.nome_vao}' ({self.id_vao}) já possui subdivisões.")

        esp_div = peca_divisoria.espessura
        larg_esq = ((self.largura - esp_div) / 2.0) if cota_x_relativa is None else float(cota_x_relativa)
        larg_dir = self.largura - larg_esq - esp_div

        if larg_esq <= 50.0 or larg_dir <= 50.0:
            raise ErroGeometriaCAD(
                f"🚨 [DIVISÃO IMPOSSÍVEL] O '{self.nome_vao}' ({self.largura}mm) não comporta "
                f"os sub-vãos de {larg_esq:.1f}mm e {larg_dir:.1f}mm."
            )

        self.tipo_divisao = "VERTICAL"
        self.peca_divisora = peca_divisoria

        vao_esquerdo = NoEspacial(
            x=self.x,
            y=self.y,
            z=self.z,
            largura=larg_esq,
            profundidade=self.profundidade,
            altura=self.altura,
            nome_vao=f"{self.nome_vao} [Esq]",
            id_vao=f"{self.id_vao}.0",
            vizinhos={
                "esquerda": self.vizinhos["esquerda"],
                "direita": peca_divisoria,
                "base": self.vizinhos["base"],
                "topo": self.vizinhos["topo"]
            }
        )

        vao_direito = NoEspacial(
            x=self.x + larg_esq + esp_div,
            y=self.y,
            z=self.z,
            largura=larg_dir,
            profundidade=self.profundidade,
            altura=self.altura,
            nome_vao=f"{self.nome_vao} [Dir]",
            id_vao=f"{self.id_vao}.1",
            vizinhos={
                "esquerda": peca_divisoria,
                "direita": self.vizinhos["direita"],
                "base": self.vizinhos["base"],
                "topo": self.vizinhos["topo"]
            }
        )

        self.filhos = [vao_esquerdo, vao_direito]
        return self.filhos

    def dividir_horizontalmente(
        self,
        peca_prateleira: Peca,
        cota_z_relativa: Optional[float] = None
    ) -> List["NoEspacial"]:
        """Fatia o vão em Inferior (.0) e Superior (.1) usando uma Prateleira."""
        if not self.eh_folha:
            raise ErroGeometriaCAD(f"🚨 O '{self.nome_vao}' ({self.id_vao}) já possui subdivisões.")

        esp_prat = peca_prateleira.espessura
        alt_inf = ((self.altura - esp_prat) / 2.0) if cota_z_relativa is None else float(cota_z_relativa)
        alt_sup = self.altura - alt_inf - esp_prat

        if alt_inf <= 50.0 or alt_sup <= 50.0:
            raise ErroGeometriaCAD(
                f"🚨 [ALTURA INSUFICIENTE] O '{self.nome_vao}' ({self.altura}mm) não comporta "
                f"a divisão horizontal ({alt_inf:.1f}mm / {alt_sup:.1f}mm)."
            )

        self.tipo_divisao = "HORIZONTAL"
        self.peca_divisora = peca_prateleira

        vao_inferior = NoEspacial(
            x=self.x,
            y=self.y,
            z=self.z,
            largura=self.largura,
            profundidade=self.profundidade,
            altura=alt_inf,
            nome_vao=f"{self.nome_vao} [Inf]",
            id_vao=f"{self.id_vao}.0",
            vizinhos={
                "esquerda": self.vizinhos["esquerda"],
                "direita": self.vizinhos["direita"],
                "base": self.vizinhos["base"],
                "topo": peca_prateleira
            }
        )

        vao_superior = NoEspacial(
            x=self.x,
            y=self.y,
            z=self.z + alt_inf + esp_prat,
            largura=self.largura,
            profundidade=self.profundidade,
            altura=alt_sup,
            nome_vao=f"{self.nome_vao} [Sup]",
            id_vao=f"{self.id_vao}.1",
            vizinhos={
                "esquerda": self.vizinhos["esquerda"],
                "direita": self.vizinhos["direita"],
                "base": peca_prateleira,
                "topo": self.vizinhos["topo"]
            }
        )

        self.filhos = [vao_inferior, vao_superior]
        return self.filhos

    def listar_vaos_folha(self) -> List["NoEspacial"]:
        if self.eh_folha:
            return [self]
        folhas = []
        for f in self.filhos:
            folhas.extend(f.listar_vaos_folha())
        return folhas

    def buscar_vao_por_id(self, id_procurado: str) -> Optional["NoEspacial"]:
        if self.id_vao == id_procurado:
            return self
        for f in self.filhos:
            achado = f.buscar_vao_por_id(id_procurado)
            if achado:
                return achado
        return None

    def to_dict(self) -> Dict[str, Any]:
        tem_portas = hasattr(self, "metadados_portas") and bool(getattr(self, "metadados_portas"))
        return {
            "id_vao": self.id_vao,
            "nome_vao": self.nome_vao,
            "eh_folha": self.eh_folha,
            "ocupacao_interna": self.ocupacao_interna,
            "tem_portas": tem_portas,
            "tipo_divisao": self.tipo_divisao,
            "geometria_3d": {
                "x": self.x,
                "y": self.y,
                "z": self.z,
                "largura": self.largura,
                "profundidade": self.profundidade,
                "altura": self.altura
            },
            "id_vizinhos": {
                lado: (peca.id_peca if peca else None)
                for lado, peca in self.vizinhos.items()
            },
            "filhos": [f.to_dict() for f in self.filhos]
        }