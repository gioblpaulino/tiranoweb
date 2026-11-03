# =============================================================================
# ARQUIVO: servidor_webcad.py
# RESPONSABILIDADE: Servidor Flask unificado do Estúdio TiranoCAD Web 3D/2D,
# com suporte a Seleção Múltipla, Transformação Direcional em Lote (Mover/Girar),
# Exclusão Seletiva de Módulos/Paredes e Ponte Direta para o TiranoCut.
# =============================================================================

import os, copy, json, re
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from tiranocad_core.orquestradores.orquestrador_modulo import OrquestradorModulo
from tiranocad_core.orquestradores.orquestrador_copiloto import OrquestradorCopiloto
from tiranocad_core.orquestradores.orquestrador_ambiente import OrquestradorAmbiente
from tiranocad_core.gerenciador_perfis import ErroPerfilConfiguracao
from tiranocad_core.modelos.entidades import ErroGeometriaCAD

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_TEMPLATES = os.path.join(BASE_DIR, "templates")
PASTA_STATIC = os.path.join(BASE_DIR, "static")
PASTA_PERFIS = os.path.join(BASE_DIR, "tiranocad_core", "catalogos", "perfis")
PASTA_PROJETOS = os.path.join(BASE_DIR, "projetos_salvos")
os.makedirs(PASTA_PROJETOS, exist_ok=True)
os.makedirs(os.path.join(PASTA_STATIC, "img"), exist_ok=True)

# Metadados do Projeto Ativo (Enviados também ao TiranoCut!)
METADADOS_PROJETO = {
    "nome_cliente": "Não Informado",
    "nome_ambiente": "COZINHA_TIRANOGIO",
    "arquivo_salvo": None,
    "estilo_piso": "GRADE_TECNICA",
    "cor_parede": "#263238"
}

# Pilhas da Máquina do Tempo (Ctrl+Z / Ctrl+Y)
HISTORICO_UNDO = []
HISTORICO_REDO = []
MAX_HISTORICO = 40


def capturar_estado_atual() -> dict:
    """Cria uma cópia profunda (Snapshot) das paredes, módulos e metadados."""
    return copy.deepcopy({
        "metadados": METADADOS_PROJETO,
        "ambiente": orq_ambiente.construtor_paredes.to_dict(),
        "modulos": COFRE_MODULOS_ATIVOS
    })


def restaurar_estado_snapshot(snapshot: dict) -> None:
    """Restaura integralmente as paredes, os módulos e os metadados a partir de um Snapshot."""
    global METADADOS_PROJETO
    METADADOS_PROJETO.update(snapshot.get("metadados", {}))

    dados_amb = snapshot.get("ambiente", {})
    orq_ambiente.construtor_paredes.pe_direito_padrao = float(dados_amb.get("pe_direito_padrao", 2700.0))
    orq_ambiente.construtor_paredes.espessura_padrao = float(dados_amb.get("espessura_padrao", 150.0))
    orq_ambiente.construtor_paredes.limpar_paredes()

    for p_dict in dados_amb.get("paredes", []):
        orq_ambiente.construtor_paredes.adicionar_parede_por_pontos(
            x1=float(p_dict["x1"]),
            y1=float(p_dict["y1"]),
            x2=float(p_dict["x2"]),
            y2=float(p_dict["y2"]),
            pe_direito=float(p_dict.get("pe_direito", 2700.0)),
            espessura=float(p_dict.get("espessura", 150.0)),
            nome=p_dict.get("nome")
        )
        # Preserva o ID original da parede para manter o vínculo com os módulos
        orq_ambiente.construtor_paredes.paredes[-1].id_parede = p_dict["id_parede"]

    COFRE_MODULOS_ATIVOS.clear()
    COFRE_MODULOS_ATIVOS.update(copy.deepcopy(snapshot.get("modulos", {})))


def registrar_acao_historico() -> None:
    """Salva o estado atual na pilha de Undo antes de qualquer alteração."""
    HISTORICO_UNDO.append(capturar_estado_atual())
    if len(HISTORICO_UNDO) > MAX_HISTORICO:
        HISTORICO_UNDO.pop(0)
    HISTORICO_REDO.clear()

CATALOGO_MATERIAIS_MDF = [
    {"id": "generico_branco_tx", "nome": "Branco TX (Padrão)", "marca": "Genérico", "hex": "#ECEFF1", "veio": False},
    {"id": "duratex_carvalho_avela", "nome": "Carvalho Avelã", "marca": "Duratex", "hex": "#B68656", "veio": True},
    {"id": "duratex_carvalho_hanover", "nome": "Carvalho Hanover", "marca": "Duratex", "hex": "#C89D66", "veio": True},
    {"id": "duratex_grafite_trama", "nome": "Grafite Trama", "marca": "Duratex", "hex": "#373B3E", "veio": False},
    {"id": "duratex_gianduia_trama", "nome": "Gianduia Trama", "marca": "Duratex", "hex": "#8D7B68", "veio": False},
    {"id": "arauco_louro_freijo", "nome": "Louro Freijó", "marca": "Arauco", "hex": "#A86B3E", "veio": True},
    {"id": "arauco_cinza_cristal", "nome": "Cinza Cristal", "marca": "Arauco", "hex": "#9E9E9E", "veio": False},
    {"id": "duratex_freijo_puro", "nome": "Freijó Puro", "marca": "Duratex", "hex": "#9C6236", "veio": True},
    {"id": "guararapes_azul_petroleo", "nome": "Azul Petróleo", "marca": "Guararapes", "hex": "#1B3B48", "veio": False},
    {"id": "generico_preto_tx", "nome": "Preto TX", "marca": "Genérico", "hex": "#1C1C1C", "veio": False},
    {"id": "mdf_cru", "nome": "MDF Cru (Sem Revestimento)", "marca": "Industrial", "hex": "#D2B48C", "veio": False}
]

app = Flask(__name__, template_folder=PASTA_TEMPLATES, static_folder=PASTA_STATIC)

COFRE_MODULOS_ATIVOS = {}

orquestrador = OrquestradorModulo(pasta_perfis=PASTA_PERFIS)
copiloto = OrquestradorCopiloto()
orq_ambiente = OrquestradorAmbiente()


@app.after_request
def aplicar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
    return response


@app.route("/", methods=["GET"])
def pagina_estudio_webcad():
    return render_template("estudio_webcad.html")


# =============================================================================
# 1. ROTAS DO CONSTRUTOR DE PAREDES E PLANTA BAIXA 2D
# =============================================================================
@app.route("/api/ambiente", methods=["GET"])
def obter_estado_ambiente():
    modulos_ordenados = [COFRE_MODULOS_ATIVOS[k] for k in sorted(COFRE_MODULOS_ATIVOS.keys())]
    return jsonify({
        "metadados": METADADOS_PROJETO,
        "ambiente": orq_ambiente.construtor_paredes.to_dict(),
        "modulos": modulos_ordenados,
        "historico": {
            "pode_desfazer": len(HISTORICO_UNDO) > 0,
            "pode_refazer": len(HISTORICO_REDO) > 0
        }
    }), 200


@app.route("/api/ambiente/preset", methods=["POST"])
def aplicar_preset_paredes():
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    try:
        formato = str(dados.get("formato", "L")).upper()
        larg_a = float(dados.get("larg_a", 3600.0))
        larg_b = float(dados.get("larg_b", 2600.0))
        pe_dir = float(dados.get("pe_direito", 2700.0))
        esp = float(dados.get("espessura", 150.0))

        orq_ambiente.construtor_paredes.pe_direito_padrao = pe_dir
        orq_ambiente.construtor_paredes.espessura_padrao = esp
        orq_ambiente.construtor_paredes.gerar_preset_ambiente(formato, larg_a, larg_b)
        orq_ambiente.recalcular_todos_modulos(COFRE_MODULOS_ATIVOS)

        return jsonify({"sucesso": True, "ambiente": orq_ambiente.construtor_paredes.to_dict()}), 200
    except ErroGeometriaCAD as e:
        return jsonify({"sucesso": False, "erro_engenharia": str(e)}), 400


@app.route("/api/ambiente/parede/adicionar", methods=["POST"])
def adicionar_parede():
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    try:
        pe_dir = float(dados.get("pe_direito", orq_ambiente.construtor_paredes.pe_direito_padrao))
        esp = float(dados.get("espessura", orq_ambiente.construtor_paredes.espessura_padrao))

        if "x1" in dados and "x2" in dados:
            nova = orq_ambiente.construtor_paredes.adicionar_parede_por_pontos(
                x1=float(dados["x1"]),
                y1=float(dados["y1"]),
                x2=float(dados["x2"]),
                y2=float(dados["y2"]),
                pe_direito=pe_dir,
                espessura=esp
            )
        else:
            nova = orq_ambiente.construtor_paredes.adicionar_segmento_continuo(
                comprimento=float(dados.get("comprimento", 2000.0)),
                angulo_graus=float(dados.get("angulo_graus", 0.0)),
                pe_direito=pe_dir,
                espessura=esp
            )

        return jsonify({
            "sucesso": True,
            "parede": nova.to_dict(),
            "ambiente": orq_ambiente.construtor_paredes.to_dict()
        }), 200
    except ErroGeometriaCAD as e:
        return jsonify({"sucesso": False, "erro_engenharia": str(e)}), 400


@app.route("/api/ambiente/parede/remover_ultima", methods=["POST"])
def remover_ultima_parede():
    """Remove o último segmento de parede criado na Planta Baixa."""
    registrar_acao_historico()
    if orq_ambiente.construtor_paredes.paredes:
        orq_ambiente.construtor_paredes.paredes.pop()
        orq_ambiente.recalcular_todos_modulos(COFRE_MODULOS_ATIVOS)
    return jsonify({"sucesso": True, "ambiente": orq_ambiente.construtor_paredes.to_dict()}), 200


@app.route("/api/ambiente/paredes/limpar", methods=["POST"])
def limpar_paredes():
    registrar_acao_historico()
    orq_ambiente.construtor_paredes.limpar_paredes()
    orq_ambiente.recalcular_todos_modulos(COFRE_MODULOS_ATIVOS)
    return jsonify({"sucesso": True, "ambiente": orq_ambiente.construtor_paredes.to_dict()}), 200


# =============================================================================
# 2. ROTAS DE FABRICAÇÃO, TRANSFORMAÇÃO DIRECIONAL E EXCLUSÃO EM LOTE
# =============================================================================
@app.route("/api/fabricar", methods=["POST"])
def api_fabricar_modulo():
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    try:
        id_informado = str(dados.get("id_modulo", "")).strip()
        if not id_informado:
            proximo_num = len(COFRE_MODULOS_ATIVOS) + 1
            while f"{proximo_num:03d}" in COFRE_MODULOS_ATIVOS:
                proximo_num += 1
            id_modulo = f"{proximo_num:03d}"
        else:
            id_modulo = id_informado.zfill(3) if id_informado.isdigit() else id_informado

        # Leitura segura: evita KeyError ('003') quando o módulo é novo!
        era_modulo_existente = id_modulo in COFRE_MODULOS_ATIVOS
        mod_anterior = COFRE_MODULOS_ATIVOS.get(id_modulo) if era_modulo_existente else None
        pos_anterior = mod_anterior.get("posicionamento_ambiente") if mod_anterior else None
        params_anteriores = mod_anterior.get("parametros", {}) if mod_anterior else {}

        nome_projeto = str(dados.get("nome_projeto", "COZINHA_TIRANOGIO")).strip().upper()
        familia = str(dados.get("familia", "MODULO_INFERIOR")).strip().upper()

        largura_x = float(dados.get("largura_x", 800.0))
        altura_y = float(dados.get("altura_y", 700.0))
        profundidade_z = float(dados.get("profundidade_z", 550.0))
        com_fundo = bool(dados.get("com_fundo", True))
        id_perfil = str(dados.get("id_perfil", "padrao_convencional_15mm")).strip()

        overrides_perfil = dados.get("overrides_perfil") or {}
        mat_caixa_ui = str(dados.get("material_caixaria", "")).strip()
        mat_frente_ui = str(dados.get("material_frentes", "")).strip()

        if mat_caixa_ui or mat_frente_ui:
            if "materiais_padrao" not in overrides_perfil:
                overrides_perfil["materiais_padrao"] = {}
            if mat_caixa_ui:
                overrides_perfil["materiais_padrao"]["material_caixaria"] = mat_caixa_ui
            if mat_frente_ui:
                overrides_perfil["materiais_padrao"]["material_frentes"] = mat_frente_ui

        # Recupera ou inicializa as 8 Zonas de Materiais e Fitas sem erro quando o módulo é novo
        zonas_salvas = dict(params_anteriores.get("zonas_materiais") or {})
        overrides_pecas_salvos = dict(params_anteriores.get("overrides_pecas") or {})

        # Se o usuário trocou o MDF Padrão no Construtor Rápido, sincroniza as zonas principais e suas fitas
        mat_caixa_ant = params_anteriores.get("material_caixaria")
        mat_frente_ant = params_anteriores.get("material_frentes")

        if mat_caixa_ui and (not era_modulo_existente or mat_caixa_ui != mat_caixa_ant):
            zonas_salvas["cor_caixaria"] = mat_caixa_ui
            zonas_salvas["cor_internos"] = mat_caixa_ui
            zonas_salvas["fita_frontal_caixaria"] = mat_caixa_ui
            zonas_salvas["fita_internos"] = mat_caixa_ui

        if mat_frente_ui and (not era_modulo_existente or mat_frente_ui != mat_frente_ant):
            zonas_salvas["cor_frentes"] = mat_frente_ui
            zonas_salvas["fita_frentes"] = mat_frente_ui

        operacoes_internas = dados.get("operacoes_internas", [])
        opcoes_especiais = dados.get("opcoes_especiais", {})
        
        tamp_agregado = dados.get("tamponamentos_agregados")
        if tamp_agregado is None and era_modulo_existente:
            tamp_agregado = params_anteriores.get("tamponamentos_agregados")

        prompt_copiloto = str(dados.get("prompt_copiloto", "")).strip()
        msg_copiloto = None
        if prompt_copiloto and familia not in ("MODULO_PAINEL", "MODULO_AVULSO"):
            interpretacao = copiloto.interpretar_comando(prompt_copiloto)
            msg_copiloto = interpretacao["mensagem_copiloto"]
            operacoes_internas = interpretacao["operacoes_internas"]
            dims_ia = interpretacao["dimensoes_detectadas"]
            if "largura_x" in dims_ia: largura_x = dims_ia["largura_x"]
            if "altura_y" in dims_ia: altura_y = dims_ia["altura_y"]
            if "profundidade_z" in dims_ia: profundidade_z = dims_ia["profundidade_z"]

        payload_gerado = orquestrador.fabricar_modulo(
            id_modulo=id_modulo,
            nome_projeto=nome_projeto,
            familia=familia,
            largura_x=largura_x,
            altura_y=altura_y,
            profundidade_z=profundidade_z,
            com_fundo=com_fundo,
            id_perfil=id_perfil,
            overrides_perfil=overrides_perfil if overrides_perfil else None,
            operacoes_internas=operacoes_internas,
            opcoes_especiais=opcoes_especiais,
            zonas_materiais=zonas_salvas,
            overrides_pecas=overrides_pecas_salvos,
            tamponamentos_agregados=tamp_agregado
        )

        if msg_copiloto:
            payload_gerado["resposta_copiloto"] = msg_copiloto
        payload_gerado["prompt_original"] = prompt_copiloto

        id_parede_req = dados.get("id_parede") or (pos_anterior.get("id_parede") if pos_anterior else None)
        usar_snap = bool(dados.get("usar_autosnap", not era_modulo_existente))

        dist_x_req = dados.get("distancia_x_parede")
        if dist_x_req is None and pos_anterior and not usar_snap:
            dist_x_req = pos_anterior.get("distancia_x_parede", 0.0)

        elev_z_req = dados.get("elevacao_z")
        if elev_z_req is None:
            if pos_anterior and era_modulo_existente:
                elev_z_req = pos_anterior.get("elevacao_z")
            elif familia == "MODULO_AEREO":
                elev_z_req = 1450.0
            else:
                elev_z_req = 0.0

        orq_ambiente.ancorar_modulo_na_parede(
            modulo_dict=payload_gerado,
            modulos_ativos=COFRE_MODULOS_ATIVOS,
            id_parede=id_parede_req,
            distancia_x_parede=dist_x_req,
            elevacao_z=elev_z_req,
            afastamento_parede=pos_anterior.get("afastamento_parede", 0.0) if pos_anterior else 0.0,
            rotacao_offset_graus=pos_anterior.get("rotacao_offset_graus", 0.0) if pos_anterior else 0.0,
            usar_autosnap=usar_snap
        )

        payload_gerado["cliente"] = METADADOS_PROJETO["nome_cliente"]
        payload_gerado["nome_cliente"] = METADADOS_PROJETO["nome_cliente"]
        payload_gerado["nome_projeto"] = f"{METADADOS_PROJETO['nome_cliente']} - {METADADOS_PROJETO['nome_ambiente']}"
        
        COFRE_MODULOS_ATIVOS[id_modulo] = payload_gerado

        return jsonify({
            "sucesso": True,
            "id_modulo": id_modulo,
            "total_pecas": len(payload_gerado["lista_de_pecas"]),
            "modulo": payload_gerado,
            "ambiente": orq_ambiente.construtor_paredes.to_dict()
        }), 200

    except (ErroGeometriaCAD, ErroPerfilConfiguracao) as erro_regra:
        return jsonify({"sucesso": False, "erro_engenharia": str(erro_regra)}), 400
    except Exception as e:
        return jsonify({"sucesso": False, "erro_interno": str(e)}), 500


@app.route("/api/modulos/transformar_lote", methods=["POST"])
def api_transformar_lote():
    """
    Move (delta_x, delta_y, delta_z) e/ou rotaciona (delta_rotacao / rotacao_absoluta)
    1 ou múltiplos módulos selecionados de uma só vez!
    """
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    ids_alvo = dados.get("ids_modulos", [])
    if not ids_alvo and "id_modulo" in dados:
        ids_alvo = [str(dados["id_modulo"])]

    modificados = orq_ambiente.transformar_lote_modulos(
        ids_selecionados=[str(i).strip() for i in ids_alvo],
        modulos_ativos=COFRE_MODULOS_ATIVOS,
        delta_x=float(dados.get("delta_x", 0.0)),
        delta_y=float(dados.get("delta_y", 0.0)),
        delta_z=float(dados.get("delta_z", 0.0)),
        delta_rotacao=float(dados.get("delta_rotacao", 0.0)),
        z_absoluto=dados.get("z_absoluto"),
        y_absoluto=dados.get("y_absoluto"),
        rotacao_absoluta=dados.get("rotacao_absoluta"),
        nova_id_parede=dados.get("nova_id_parede"),
        aplicar_autosnap=bool(dados.get("aplicar_autosnap", False))
    )

    return jsonify({
        "sucesso": True,
        "modificados": modificados,
        "modulos": [COFRE_MODULOS_ATIVOS[k] for k in sorted(COFRE_MODULOS_ATIVOS.keys())]
    }), 200


@app.route("/api/modulos/excluir_lote", methods=["POST"])
def api_excluir_lote():
    """Exclui 1 ou múltiplos módulos selecionados pelo usuário."""
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    ids_para_excluir = dados.get("ids_modulos", [])
    removidos = []

    for m_id in ids_para_excluir:
        chave = str(m_id).strip()
        if chave in COFRE_MODULOS_ATIVOS:
            del COFRE_MODULOS_ATIVOS[chave]
            removidos.append(chave)

    return jsonify({
        "sucesso": True,
        "removidos": removidos,
        "modulos": [COFRE_MODULOS_ATIVOS[k] for k in sorted(COFRE_MODULOS_ATIVOS.keys())]
    }), 200


@app.route("/api/modulo/posicionar", methods=["POST"])
def api_posicionar_modulo():
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    id_mod = str(dados.get("id_modulo", "")).strip()
    if id_mod not in COFRE_MODULOS_ATIVOS:
        return jsonify({"sucesso": False, "erro_engenharia": "Módulo não encontrado."}), 404

    mod = COFRE_MODULOS_ATIVOS[id_mod]
    pos_ant = mod.get("posicionamento_ambiente", {})
    nova_par = dados.get("id_parede")
    trocou_parede = (nova_par is not None and nova_par != pos_ant.get("id_parede"))

    pos = orq_ambiente.ancorar_modulo_na_parede(
        modulo_dict=mod,
        modulos_ativos=COFRE_MODULOS_ATIVOS,
        id_parede=nova_par,
        distancia_x_parede=None if trocou_parede else dados.get("distancia_x_parede"),
        elevacao_z=dados.get("elevacao_z"),
        afastamento_parede=dados.get("afastamento_parede"),
        rotacao_offset_graus=dados.get("rotacao_offset_graus"),
        usar_autosnap=bool(dados.get("usar_autosnap", False)) or trocou_parede
    )
    return jsonify({"sucesso": True, "posicionamento": pos, "modulo": mod}), 200


# =============================================================================
# 3. ROTAS DE INTEGRAÇÃO COM O TIRANOCUT
# =============================================================================
@app.route("/api/modulos", methods=["GET"])
def listar_todos_modulos():
    modulos_ordenados = [COFRE_MODULOS_ATIVOS[k] for k in sorted(COFRE_MODULOS_ATIVOS.keys())]
    return jsonify(modulos_ordenados), 200


@app.route("/api/modulo/<id_modulo>", methods=["GET"])
def obter_modulo_por_id(id_modulo):
    id_limpo = str(id_modulo).strip()
    if id_limpo in COFRE_MODULOS_ATIVOS:
        return jsonify(COFRE_MODULOS_ATIVOS[id_limpo]), 200
    return jsonify({"erro": f"Módulo '{id_limpo}' não encontrado."}), 404


@app.route("/api/modulos/limpar", methods=["DELETE", "POST"])
def limpar_projeto_ativo():
    registrar_acao_historico()
    COFRE_MODULOS_ATIVOS.clear()
    return jsonify({"sucesso": True, "mensagem": "Ambiente limpo com sucesso."}), 200

@app.route("/api/catalogo_materiais", methods=["GET"])
def obter_catalogo_materiais():
    """
    Retorna o catálogo de chapas MDF multi-marcas e verifica automaticamente
    se existe arquivo de textura real (.jpg, .jpeg, .png) em static/textures/mdf/.
    """
    pasta_tex = os.path.join(PASTA_STATIC, "textures", "mdf")
    os.makedirs(pasta_tex, exist_ok=True)

    catalogo_enriquecido = []
    for item in CATALOGO_MATERIAIS_MDF:
        copia = dict(item)
        copia["textura_url"] = None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            nome_arq = f"{item['id']}{ext}"
            if os.path.exists(os.path.join(pasta_tex, nome_arq)):
                copia["textura_url"] = f"/static/textures/mdf/{nome_arq}"
                break
        catalogo_enriquecido.append(copia)

    return jsonify({"materiais": catalogo_enriquecido}), 200


@app.route("/api/modulo/pintar", methods=["POST"])
def api_pintar_modulo_ou_peca():
    """
    Atualiza as 8 Zonas de Material/Fita do módulo OU aplica override de material
    e fita de borda em uma Peça Individual SEM alterar a engenharia ou geometria!
    """
    registrar_acao_historico()
    dados = request.get_json(silent=True) or {}
    id_mod = str(dados.get("id_modulo", "")).strip()
    if id_mod not in COFRE_MODULOS_ATIVOS:
        return jsonify({"sucesso": False, "erro_engenharia": "Módulo não encontrado."}), 404

    mod = COFRE_MODULOS_ATIVOS[id_mod]
    params = mod.setdefault("parametros", {})
    zonas_atuais = params.setdefault("zonas_materiais", {})
    overrides_pecas = params.setdefault("overrides_pecas", {})

    # 1. Atualiza Zonas do Módulo (se enviadas)
    if "zonas_materiais" in dados and isinstance(dados["zonas_materiais"], dict):
        zonas_atuais.update(dados["zonas_materiais"])

    # 2. Atualiza Override de Peça Individual (se enviado)
    if "override_peca" in dados and isinstance(dados["override_peca"], dict):
        ov = dados["override_peca"]
        nome_peca = str(ov.get("nome_comercial", "")).strip()
        if nome_peca:
            overrides_pecas[nome_peca] = {
                "material": ov.get("material"),
                "cor_fita_borda": ov.get("cor_fita_borda"),
                "fitas_borda": ov.get("fitas_borda")
            }

    # Limpa overrides individuais se solicitado
    if dados.get("resetar_pecas_individuais"):
        overrides_pecas.clear()

    def possui_veio(nome_mat: str) -> bool:
        return not any(iso in nome_mat.upper() for iso in ["BRANCO", "CRU", "PRETO", "CINZA", "GRAFITE", "TX"])

    cats_caixaria = {
        "base_inferior", "base_superior", "lateral_esquerda", "lateral_direita",
        "sarrafo_frontal", "sarrafo_traseiro_deitado", "sarrafo_traseiro_em_pe",
        "regua_mao_amiga_movel", "regua_mao_amiga_parede", "travessa_fixacao_aereo",
        "travessa_reforco_torre_sup", "travessa_reforco_torre_inf"
    }
    cats_frentes = {
        "porta_giro_esquerda", "porta_giro_direita", "porta_basculante",
        "frente_gaveta", "frente_porta_tempero", "painel_tamponamento"
    }
    cats_fundo_gaveta = {"fundo_gaveta", "fundo_sapateira"}

    # Reaplica as cores diretamente nos dicionários das peças já calculadas (Zero recálculo geométrico!)
    for p_dict in mod.get("lista_de_pecas", []):
        cat = str(p_dict.get("categoria_industrial", "")).lower()
        nome_com = p_dict.get("nome_comercial", "")

        if cat in cats_caixaria:
            if zonas_atuais.get("cor_caixaria"): p_dict["material"] = zonas_atuais["cor_caixaria"]
            p_dict["cor_fita_borda"] = zonas_atuais.get("fita_frontal_caixaria") or p_dict["material"]
        elif cat in cats_frentes:
            if zonas_atuais.get("cor_frentes"): p_dict["material"] = zonas_atuais["cor_frentes"]
            p_dict["cor_fita_borda"] = zonas_atuais.get("fita_frentes") or p_dict["material"]
        elif cat in cats_fundo_gaveta:
            if zonas_atuais.get("cor_fundo_gaveta"): p_dict["material"] = zonas_atuais["cor_fundo_gaveta"]
            p_dict["cor_fita_borda"] = "SEM_FITA"
        elif cat == "fundo_costa":
            if zonas_atuais.get("cor_fundo_costa"): p_dict["material"] = zonas_atuais["cor_fundo_costa"]
            p_dict["cor_fita_borda"] = "SEM_FITA"
        else:
            if zonas_atuais.get("cor_internos"): p_dict["material"] = zonas_atuais["cor_internos"]
            p_dict["cor_fita_borda"] = zonas_atuais.get("fita_internos") or p_dict["material"]

        p_dict["tem_veio"] = False if "fundo" in cat else possui_veio(p_dict["material"])

        # Aplica o override individual se esta peça específica foi customizada pelo usuário
        if nome_com in overrides_pecas:
            ov_p = overrides_pecas[nome_com]
            if ov_p.get("material"):
                p_dict["material"] = ov_p["material"]
                p_dict["tem_veio"] = False if "fundo" in cat else possui_veio(p_dict["material"])
            if ov_p.get("cor_fita_borda"):
                p_dict["cor_fita_borda"] = ov_p["cor_fita_borda"]
            if isinstance(ov_p.get("fitas_borda"), dict):
                p_dict["fitas_borda"].update(ov_p["fitas_borda"])

    return jsonify({"sucesso": True, "modulo": mod}), 200

@app.route("/api/modulos/tamponamento_inteligente", methods=["POST"])
def api_tamponamento_inteligente():
    """
    Aplica Tamponamento em 1 módulo OU executa o Envelopamento Inteligente em Lote:
    Quando múltiplos módulos são selecionados, aplica a Lateral Esquerda no 1º módulo,
    a Lateral Direita no último módulo, e estende a Vista Superior em 'L' (ou Tampo)
    cobrindo todo o vão entre as duas laterais (respeitando o tamanho da chapa)!
    """
    dados = request.get_json(silent=True) or {}
    ids_req = [str(i).strip() for i in dados.get("ids_modulos", []) if str(i).strip() in COFRE_MODULOS_ATIVOS]
    if not ids_req:
        return jsonify({"sucesso": False, "erro_engenharia": "Nenhum módulo válido selecionado."}), 400

    registrar_acao_historico()
    config_base = dados.get("config_tamponamento", {})
    ativar = bool(config_base.get("ativo", True))

    # Ordena os módulos selecionados da esquerda para a direita ao longo da parede
    mods_ordenados = sorted(
        [COFRE_MODULOS_ATIVOS[i] for i in ids_req],
        key=lambda m: float(m.get("posicionamento_ambiente", {}).get("distancia_x_parede", 0.0))
    )

    # Calcula a largura total abrangida do início do 1º módulo até o final do último módulo
    x_ini_primeiro = float(mods_ordenados[0].get("posicionamento_ambiente", {}).get("distancia_x_parede", 0.0))
    mod_ultimo = mods_ordenados[-1]
    x_fim_ultimo = (
        float(mod_ultimo.get("posicionamento_ambiente", {}).get("distancia_x_parede", 0.0)) +
        float(mod_ultimo["dimensoes_ocupadas"]["largura_x"])
    )
    largura_total_conjunto = round(x_fim_ultimo - x_ini_primeiro, 2)

    for idx, mod in enumerate(mods_ordenados):
        eh_primeiro = (idx == 0)
        eh_ultimo = (idx == len(mods_ordenados) - 1)
        eh_unico = (len(mods_ordenados) == 1)

        cfg_mod = dict(config_base)
        if not ativar:
            cfg_mod["ativo"] = False
        elif not eh_unico:
            # No modo Multi-Módulos:
            # - 1º módulo recebe Lateral Esq, Fechamento Esq e a Vista Superior do conjunto inteiro
            # - Último módulo recebe Lateral Dir e Fechamento Dir
            # - Módulos intermediários ficam limpos para não duplicar chapas internas
            cfg_mod["lateral_esquerda"] = bool(config_base.get("lateral_esquerda")) and eh_primeiro
            cfg_mod["fechamento_esquerda"] = bool(config_base.get("fechamento_esquerda")) and eh_primeiro
            cfg_mod["lateral_direita"] = bool(config_base.get("lateral_direita")) and eh_ultimo
            cfg_mod["fechamento_direita"] = bool(config_base.get("fechamento_direita")) and eh_ultimo
            cfg_mod["vista_superior_l"] = bool(config_base.get("vista_superior_l")) and eh_primeiro
            cfg_mod["topo_passante"] = bool(config_base.get("topo_passante")) and eh_primeiro
            cfg_mod["largura_conjunto_mm"] = largura_total_conjunto if eh_primeiro else mod["dimensoes_ocupadas"]["largura_x"]
            cfg_mod["conjunto_tem_lat_dir"] = bool(config_base.get("lateral_direita"))

        params = mod.get("parametros", {})
        pos_ant = mod.get("posicionamento_ambiente", {})
        prompt_orig = mod.get("prompt_original", "")
        msg_cop = mod.get("resposta_copiloto")

        reconstruido = orquestrador.fabricar_modulo(
            id_modulo=mod["id_modulo"],
            nome_projeto=mod.get("nome_projeto", "COZINHA_TIRANOGIO"),
            familia=mod["familia"],
            largura_x=float(mod["dimensoes_ocupadas"]["largura_x"]),
            altura_y=float(mod["dimensoes_ocupadas"]["altura_y"]),
            profundidade_z=float(mod["dimensoes_ocupadas"]["profundidade_z"]),
            overrides_perfil=params.get("perfil_ativo"),
            operacoes_internas=mod.get("operacoes_internas", []),
            zonas_materiais=params.get("zonas_materiais"),
            overrides_pecas=params.get("overrides_pecas"),
            tamponamentos_agregados=cfg_mod
        )
        reconstruido["posicionamento_ambiente"] = pos_ant
        reconstruido["prompt_original"] = prompt_orig
        reconstruido["resposta_copiloto"] = msg_cop
        COFRE_MODULOS_ATIVOS[mod["id_modulo"]] = reconstruido

    return jsonify({"sucesso": True, "modulo": COFRE_MODULOS_ATIVOS[mods_ordenados[0]["id_modulo"]]}), 200


@app.route("/api/modulo/redimensionar_peca_tamp", methods=["POST"])
def api_redimensionar_peca_tamponamento():
    """Redimensiona ou desloca uma peça específica do tamponamento sem afetar o módulo."""
    dados = request.get_json(silent=True) or {}
    id_mod = str(dados.get("id_modulo", "")).strip()
    nome_peca = str(dados.get("nome_comercial", "")).strip()
    if id_mod not in COFRE_MODULOS_ATIVOS or not nome_peca:
        return jsonify({"sucesso": False, "erro_engenharia": "Módulo ou peça não encontrados."}), 404

    registrar_acao_historico()
    mod = COFRE_MODULOS_ATIVOS[id_mod]
    params = mod.get("parametros", {})
    cfg_tamp = dict(params.get("tamponamentos_agregados") or {})
    ov_map = dict(cfg_tamp.get("overrides_pecas_tamp") or {})

    if dados.get("resetar"):
        ov_map.pop(nome_peca, None)
    else:
        ov_map[nome_peca] = {
            "dx": float(dados.get("dx")),
            "dy": float(dados.get("dy")),
            "dz": float(dados.get("dz")),
            "offset_x": float(dados.get("offset_x", 0.0)),
            "offset_y": float(dados.get("offset_y", 0.0)),
            "offset_z": float(dados.get("offset_z", 0.0))
        }

    cfg_tamp["overrides_pecas_tamp"] = ov_map
    pos_ant = mod.get("posicionamento_ambiente", {})

    reconstruido = orquestrador.fabricar_modulo(
        id_modulo=id_mod,
        nome_projeto=mod.get("nome_projeto", "COZINHA_TIRANOGIO"),
        familia=mod["familia"],
        largura_x=float(mod["dimensoes_ocupadas"]["largura_x"]),
        altura_y=float(mod["dimensoes_ocupadas"]["altura_y"]),
        profundidade_z=float(mod["dimensoes_ocupadas"]["profundidade_z"]),
        overrides_perfil=params.get("perfil_ativo"),
        operacoes_internas=mod.get("operacoes_internas", []),
        zonas_materiais=params.get("zonas_materiais"),
        overrides_pecas=params.get("overrides_pecas"),
        tamponamentos_agregados=cfg_tamp
    )
    reconstruido["posicionamento_ambiente"] = pos_ant
    COFRE_MODULOS_ATIVOS[id_mod] = reconstruido
    return jsonify({"sucesso": True, "modulo": reconstruido}), 200
@app.route("/api/ambiente/resumo_industrial", methods=["GET"])

def obter_resumo_industrial_bom():
    """
    Calcula o Totalizador Industrial (BOM) de todo o ambiente ativo:
    1. Consumo de Chapas MDF por cor e espessura (m² e chapas inteiras 2750x1850mm).
    2. Consumo de Fitas de Borda por cor e largura (metros lineares + perda de destopo).
    3. Quantitativo exato de Ferragens (Dobradiças, Corrediças por medida, Fixadores).
    """
    import math

    AREA_CHAPA_PADRAO_M2 = (2750.0 * 1850.0) / 1_000_000.0  # 5.0875 m²
    FATOR_PERDA_CORTE = 1.15  # 15% de margem de perda/refilo
    PERDA_DESTOPO_POR_BORDA_MM = 30.0

    mapa_nomes_mat = {m["id"]: f"[{m['marca']}] {m['nome']}" for m in CATALOGO_MATERIAIS_MDF}

    chapas_agrupadas = {}
    fitas_agrupadas = {}
    ferragens = {
        "dobradicas_35mm": 0,
        "parafusos_estruturais_4_5mm": 0,
        "tambores_minifix_15mm": 0,
        "cavilhas_madeira_8mm": 0,
        "suportes_prateleira_pitao": 0,
        "pistoes_gas_basculante": 0,
        "corredicas_por_tamanho": {}
    }

    for mod in COFRE_MODULOS_ATIVOS.values():
        for p in mod.get("lista_de_pecas", []):
            d2 = p.get("dimensoes_2d_planificadas", {})
            comp_x = float(d2.get("largura_x", 0.0))
            larg_y = float(d2.get("altura_y", 0.0))
            esp = float(d2.get("espessura", 15.0))
            id_mat = str(p.get("material", "generico_branco_tx"))
            cat = str(p.get("categoria_industrial", "")).lower()

            # 1. Acumula Área de Chapa por (Material, Espessura)
            chave_chapa = f"{id_mat}__{esp:.1f}"
            if chave_chapa not in chapas_agrupadas:
                chapas_agrupadas[chave_chapa] = {
                    "id_material": id_mat,
                    "nome_material": mapa_nomes_mat.get(id_mat, id_mat),
                    "espessura_mm": esp,
                    "qtd_pecas": 0,
                    "area_liquida_m2": 0.0
                }
            chapas_agrupadas[chave_chapa]["qtd_pecas"] += 1
            chapas_agrupadas[chave_chapa]["area_liquida_m2"] += (comp_x * larg_y) / 1_000_000.0

            # 2. Acumula Metros Lineares de Fita de Borda
            fb = p.get("fitas_borda", {})
            id_fita = str(p.get("cor_fita_borda") or id_mat)
            if id_fita != "SEM_FITA":
                mm_fita_peca = 0.0
                if fb.get("base"): mm_fita_peca += comp_x + PERDA_DESTOPO_POR_BORDA_MM
                if fb.get("topo"): mm_fita_peca += comp_x + PERDA_DESTOPO_POR_BORDA_MM
                if fb.get("esquerda"): mm_fita_peca += larg_y + PERDA_DESTOPO_POR_BORDA_MM
                if fb.get("direita"): mm_fita_peca += larg_y + PERDA_DESTOPO_POR_BORDA_MM

                if mm_fita_peca > 0:
                    larg_comercial_fita = 22 if esp <= 18.5 else 29
                    chave_fita = f"{id_fita}__{larg_comercial_fita}"
                    if chave_fita not in fitas_agrupadas:
                        fitas_agrupadas[chave_fita] = {
                            "id_cor": id_fita,
                            "nome_cor": mapa_nomes_mat.get(id_fita, id_fita),
                            "largura_fita_mm": larg_comercial_fita,
                            "metros_lineares": 0.0
                        }
                    fitas_agrupadas[chave_fita]["metros_lineares"] += (mm_fita_peca / 1000.0)

            # 3. Contagem de Ferragens por Categoria e Usinagens
            if cat == "porta_basculante":
                ferragens["pistoes_gas_basculante"] += 2
            elif cat == "prateleira_livre":
                ferragens["suportes_prateleira_pitao"] += 4
            elif cat in ("lateral_gaveta_esquerda", "lateral_sapateira_esquerda"):
                tam_trilho = int(round(comp_x))
                chave_trilho = f"Par Corrediça Telescópica {tam_trilho}mm"
                ferragens["corredicas_por_tamanho"][chave_trilho] = (
                    ferragens["corredicas_por_tamanho"].get(chave_trilho, 0) + 1
                )

            for f in p.get("usinagens", {}).get("furos", []):
                tf = str(f.get("tipo_furo", "")).upper()
                diam = float(f.get("diametro", 0.0))
                if tf == "CANECO" or diam >= 30.0:
                    ferragens["dobradicas_35mm"] += 1
                elif tf == "MINIFIX" or (14.0 <= diam <= 16.0):
                    ferragens["tambores_minifix_15mm"] += 1
                elif tf == "CAVILHA" or (7.5 <= diam <= 8.5):
                    ferragens["cavilhas_madeira_8mm"] += 1
                elif tf == "ESTRUTURAL":
                    ferragens["parafusos_estruturais_4_5mm"] += 1

    lista_chapas = []
    for item in chapas_agrupadas.values():
        area_liq = round(item["area_liquida_m2"], 2)
        chapas_est = max(1, math.ceil((area_liq * FATOR_PERDA_CORTE) / AREA_CHAPA_PADRAO_M2)) if area_liq > 0 else 0
        item["area_liquida_m2"] = area_liq
        item["chapas_inteiras_estimadas"] = chapas_est
        lista_chapas.append(item)

    lista_fitas = []
    for item in fitas_agrupadas.values():
        item["metros_lineares"] = math.ceil(item["metros_lineares"])
        lista_fitas.append(item)

    return jsonify({
        "sucesso": True,
        "chapas": lista_chapas,
        "fitas": lista_fitas,
        "ferragens": ferragens
    }), 200

# =============================================================================
# ROTAS DE UNDO / REDO (CTRL+Z / CTRL+Y) E GERENCIAMENTO DE PROJETOS SALVOS
# =============================================================================
@app.route("/api/historico/undo", methods=["POST"])
def api_desfazer_acao():
    if not HISTORICO_UNDO:
        return jsonify({"sucesso": False, "mensagem": "Nada para desfazer."}), 200
    HISTORICO_REDO.append(capturar_estado_atual())
    estado_anterior = HISTORICO_UNDO.pop()
    restaurar_estado_snapshot(estado_anterior)
    return jsonify({"sucesso": True}), 200


@app.route("/api/historico/redo", methods=["POST"])
def api_refazer_acao():
    if not HISTORICO_REDO:
        return jsonify({"sucesso": False, "mensagem": "Nada para refazer."}), 200
    HISTORICO_UNDO.append(capturar_estado_atual())
    estado_futuro = HISTORICO_REDO.pop()
    restaurar_estado_snapshot(estado_futuro)
    return jsonify({"sucesso": True}), 200


@app.route("/api/projeto/novo", methods=["POST"])
def api_criar_novo_projeto():
    """Inicializa um novo ambiente do zero com Cliente, Ambiente e Planta escolhidos."""
    dados = request.get_json(silent=True) or {}
    registrar_acao_historico()

    cliente = str(dados.get("nome_cliente", "")).strip() or "Cliente Padrão"
    ambiente_nome = str(dados.get("nome_ambiente", "")).strip() or "Cozinha Planejada"
    formato = str(dados.get("formato_planta", "L")).strip().upper()
    larg_a = float(dados.get("larg_a", 3600.0))
    larg_b = float(dados.get("larg_b", 2600.0))
    pe_dir = float(dados.get("pe_direito", 2700.0))

    METADADOS_PROJETO["nome_cliente"] = cliente
    METADADOS_PROJETO["nome_ambiente"] = ambiente_nome
    METADADOS_PROJETO["arquivo_salvo"] = None

    COFRE_MODULOS_ATIVOS.clear()
    orq_ambiente.construtor_paredes.pe_direito_padrao = pe_dir
    orq_ambiente.construtor_paredes.gerar_preset_ambiente(formato, larg_a, larg_b)

    return jsonify({"sucesso": True, "metadados": METADADOS_PROJETO}), 200


@app.route("/api/projeto/salvar", methods=["POST"])
def api_salvar_projeto():
    """Salva todo o estado do ambiente e módulos em projetos_salvos/*.json."""
    dados = request.get_json(silent=True) or {}
    if dados.get("nome_cliente"):
        METADADOS_PROJETO["nome_cliente"] = str(dados["nome_cliente"]).strip()
    if dados.get("nome_ambiente"):
        METADADOS_PROJETO["nome_ambiente"] = str(dados["nome_ambiente"]).strip()
    if dados.get("estilo_piso"):
        METADADOS_PROJETO["estilo_piso"] = str(dados["estilo_piso"])
    if dados.get("cor_parede"):
        METADADOS_PROJETO["cor_parede"] = str(dados["cor_parede"])

    # Atualiza o nome do cliente em todos os módulos ativos para o TiranoCut
    for mod in COFRE_MODULOS_ATIVOS.values():
        mod["cliente"] = METADADOS_PROJETO["nome_cliente"]
        mod["nome_cliente"] = METADADOS_PROJETO["nome_cliente"]
        mod["nome_projeto"] = f"{METADADOS_PROJETO['nome_cliente']} - {METADADOS_PROJETO['nome_ambiente']}"

    slug_base = f"{METADADOS_PROJETO['nome_cliente']}_{METADADOS_PROJETO['nome_ambiente']}"
    slug_limpo = re.sub(r"[^a-zA-Z0-9_-]", "_", slug_base).strip("_").lower()
    nome_arquivo = f"{slug_limpo or 'projeto_tirano'}.json"
    METADADOS_PROJETO["arquivo_salvo"] = nome_arquivo

    caminho = os.path.join(PASTA_PROJETOS, nome_arquivo)
    pacote = capturar_estado_atual()
    pacote["data_salvamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=2)

    return jsonify({"sucesso": True, "arquivo": nome_arquivo, "data": pacote["data_salvamento"]}), 200


@app.route("/api/projeto/listar", methods=["GET"])
def api_listar_projetos_salvos():
    """Lista todos os projetos salvos na pasta projetos_salvos/."""
    lista = []
    for arq in sorted(os.listdir(PASTA_PROJETOS)):
        if not arq.endswith(".json"):
            continue
        caminho = os.path.join(PASTA_PROJETOS, arq)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                d = json.load(f)
            meta = d.get("metadados", {})
            mods = d.get("modulos", {})
            total_pecas = sum(len(m.get("lista_de_pecas", [])) for m in mods.values())
            lista.append({
                "arquivo": arq,
                "nome_cliente": meta.get("nome_cliente", "Sem Nome"),
                "nome_ambiente": meta.get("nome_ambiente", "Ambiente"),
                "data_salvamento": d.get("data_salvamento", "-"),
                "qtd_modulos": len(mods),
                "total_pecas": total_pecas
            })
        except Exception:
            continue
    return jsonify({"projetos": lista}), 200


@app.route("/api/projeto/carregar", methods=["POST"])
def api_carregar_projeto():
    """Carrega um projeto salvo do disco para a memória ativa."""
    dados = request.get_json(silent=True) or {}
    nome_arq = str(dados.get("arquivo", "")).strip()
    caminho = os.path.join(PASTA_PROJETOS, nome_arq)
    if not os.path.exists(caminho):
        return jsonify({"sucesso": False, "erro": "Arquivo de projeto não encontrado."}), 404

    registrar_acao_historico()
    with open(caminho, "r", encoding="utf-8") as f:
        pacote = json.load(f)

    restaurar_estado_snapshot(pacote)
    return jsonify({"sucesso": True, "metadados": METADADOS_PROJETO}), 200


@app.route("/api/projeto/excluir", methods=["POST"])
def api_excluir_projeto_salvo():
    dados = request.get_json(silent=True) or {}
    nome_arq = str(dados.get("arquivo", "")).strip()
    caminho = os.path.join(PASTA_PROJETOS, nome_arq)
    if os.path.exists(caminho):
        os.remove(caminho)
    return jsonify({"sucesso": True}), 200
    
if __name__ == "__main__":
    os.makedirs(PASTA_TEMPLATES, exist_ok=True)
    os.makedirs(os.path.join(PASTA_STATIC, "css"), exist_ok=True)
    os.makedirs(os.path.join(PASTA_STATIC, "js"), exist_ok=True)
    os.makedirs(os.path.join(PASTA_STATIC, "textures", "mdf"), exist_ok=True)
    
    cmd_1 = copiloto.interpretar_comando("Coloque 4 gavetas")
    m1 = orquestrador.fabricar_modulo(
        id_modulo="001", nome_projeto="COZINHA_TIRANOGIO", familia="MODULO_INFERIOR",
        largura_x=800.0, altura_y=700.0, profundidade_z=550.0, operacoes_internas=cmd_1["operacoes_internas"]
    )
    m1["resposta_copiloto"] = cmd_1["mensagem_copiloto"]
    orq_ambiente.ancorar_modulo_na_parede(m1, COFRE_MODULOS_ATIVOS, usar_autosnap=True)
    COFRE_MODULOS_ATIVOS["001"] = m1

    cmd_2 = copiloto.interpretar_comando("Coloque porta-tempero de 200mm na esquerda e 1 prateleira na direita e 2 portas na direita")
    m2 = orquestrador.fabricar_modulo(
        id_modulo="002", nome_projeto="COZINHA_TIRANOGIO", familia="MODULO_INFERIOR",
        largura_x=1200.0, altura_y=700.0, profundidade_z=550.0, operacoes_internas=cmd_2["operacoes_internas"]
    )
    m2["resposta_copiloto"] = cmd_2["mensagem_copiloto"]
    orq_ambiente.ancorar_modulo_na_parede(m2, COFRE_MODULOS_ATIVOS, usar_autosnap=True)
    COFRE_MODULOS_ATIVOS["002"] = m2

    print("🚀 Estúdio Web CAD 3D disponível em: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
    
    