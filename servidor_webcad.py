# =============================================================================
# ARQUIVO: servidor_webcad.py
# RESPONSABILIDADE: Servidor Flask unificado do Estúdio TiranoCAD Web 3D/2D,
# com suporte a Seleção Múltipla, Transformação Direcional em Lote (Mover/Girar),
# Exclusão Seletiva de Módulos/Paredes e Ponte Direta para o TiranoCut.
# =============================================================================

import os
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

CATALOGO_MATERIAIS_MDF = [
    {"id": "generico_branco_tx", "nome": "Branco TX (Padrão)", "marca": "Genérico", "hex": "#ECEFF1", "veio": False},
    {"id": "duratex_carvalho_avela", "nome": "Carvalho Avelã", "marca": "Duratex", "hex": "#B68656", "veio": True},
    {"id": "duratex_carvalho_hanover", "nome": "Carvalho Hanover", "marca": "Duratex", "hex": "#C89D66", "veio": True},
    {"id": "duratex_grafite_trama", "nome": "Grafite Trama", "marca": "Duratex", "hex": "#373B3E", "veio": False},
    {"id": "duratex_gianduia_trama", "nome": "Gianduia Trama", "marca": "Duratex", "hex": "#8D7B68", "veio": False},
    {"id": "arauco_louro_freijo", "nome": "Louro Freijó", "marca": "Arauco", "hex": "#A86B3E", "veio": True},
    {"id": "arauco_cinza_cristal", "nome": "Cinza Cristal", "marca": "Arauco", "hex": "#9E9E9E", "veio": False},
    {"id": "guararapes_freijo_puro", "nome": "Freijó Puro", "marca": "Guararapes", "hex": "#9C6236", "veio": True},
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
        "ambiente": orq_ambiente.construtor_paredes.to_dict(),
        "modulos": modulos_ordenados
    }), 200


@app.route("/api/ambiente/preset", methods=["POST"])
def aplicar_preset_paredes():
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
    if orq_ambiente.construtor_paredes.paredes:
        orq_ambiente.construtor_paredes.paredes.pop()
        orq_ambiente.recalcular_todos_modulos(COFRE_MODULOS_ATIVOS)
    return jsonify({"sucesso": True, "ambiente": orq_ambiente.construtor_paredes.to_dict()}), 200


@app.route("/api/ambiente/paredes/limpar", methods=["POST"])
def limpar_paredes():
    orq_ambiente.construtor_paredes.limpar_paredes()
    orq_ambiente.recalcular_todos_modulos(COFRE_MODULOS_ATIVOS)
    return jsonify({"sucesso": True, "ambiente": orq_ambiente.construtor_paredes.to_dict()}), 200


# =============================================================================
# 2. ROTAS DE FABRICAÇÃO, TRANSFORMAÇÃO DIRECIONAL E EXCLUSÃO EM LOTE
# =============================================================================
@app.route("/api/fabricar", methods=["POST"])
def api_fabricar_modulo():
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

        era_modulo_existente = id_modulo in COFRE_MODULOS_ATIVOS
        pos_anterior = COFRE_MODULOS_ATIVOS[id_modulo].get("posicionamento_ambiente") if era_modulo_existente else None
        
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

        operacoes_internas = dados.get("operacoes_internas", [])
        opcoes_especiais = dados.get("opcoes_especiais", {})

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
            overrides_pecas=COFRE_MODULOS_ATIVOS[id_modulo]["parametros"].get("overrides_pecas"),
            zonas_materiais=COFRE_MODULOS_ATIVOS[id_modulo]["parametros"].get("zonas_materiais")
        )

        if msg_copiloto:
            payload_gerado["resposta_copiloto"] = msg_copiloto
        payload_gerado["prompt_original"] = prompt_copiloto

        # Posicionamento inteligente (Respeita elevação Z de Aéreos!)
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
    COFRE_MODULOS_ATIVOS.clear()
    return jsonify({"sucesso": True, "mensagem": "Ambiente limpo com sucesso."}), 200

@app.route("/api/catalogo_materiais", methods=["GET"])
def obter_catalogo_materiais():
    """Retorna o catálogo de chapas MDF multi-marcas para o Pintor 3D."""
    return jsonify({"materiais": CATALOGO_MATERIAIS_MDF}), 200


@app.route("/api/modulo/pintar", methods=["POST"])
def api_pintar_modulo_ou_peca():
    """
    Atualiza as 8 Zonas de Material/Fita do módulo OU aplica override de material
    e fita de borda em uma Peça Individual SEM alterar a engenharia ou geometria!
    """
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

if __name__ == "__main__":
    os.makedirs(PASTA_TEMPLATES, exist_ok=True)
    os.makedirs(os.path.join(PASTA_STATIC, "css"), exist_ok=True)
    os.makedirs(os.path.join(PASTA_STATIC, "js"), exist_ok=True)

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
    
    