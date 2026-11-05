/* =============================================================================
 * ARQUIVO: static/js/texturas_ui.js
 * RESPONSABILIDADE: Janelas HUD, Mapeamento 6-Faces (MDF Laminado + Fita de
 * Borda Real + MDF Cru nos topos sem fita), Abertura Separada Portas/Gavetas,
 * Ocultar Frentes e Modal de Resumo Industrial (BOM).
 * ============================================================================= */

const cacheTexturasThree = {};
const loaderTextura = new THREE.TextureLoader();
let modoPalcoLimpoAtivo = false;
let ocultarFrentesExternas = false;

// Inicia com o mapa técnico vermelho desligado para exibir a fita real e o MDF Cru nos topos!
mostrarFitas = false;

// =============================================================================
// 1. GERENCIAMENTO DAS JANELAS FLUTUANTES (HUD) E ABAS
// =============================================================================
function alternarJanelaHUD(idPainel, idBotao) {
    const painel = document.getElementById(idPainel);
    if (!painel) return;
    const oculto = painel.classList.toggle("oculto");
    const btn = document.getElementById(idBotao);
    if (btn) btn.classList.toggle("ativo", !oculto);
}

function abrirAbaDireita(qualAba) {
    const hudDir = document.getElementById("hud_direita");
    hudDir.classList.remove("oculto");
    document.getElementById("btn_hud_direita").classList.add("ativo");

    const ehMat = (qualAba === "MATERIAIS");
    document.getElementById("aba_conteudo_ambiente").style.display = ehMat ? "none" : "flex";
    document.getElementById("painel_flutuante_materiais").style.display = ehMat ? "flex" : "none";

    document.getElementById("tab_btn_ambiente").classList.toggle("ativa", !ehMat);
    document.getElementById("tab_btn_materiais").classList.toggle("ativa", ehMat);
    document.getElementById("btn_menu_materiais").classList.toggle("ativo", ehMat);

    if (ehMat && moduloAtivo) {
        sincronizarMenuMateriaisComModulo(moduloAtivo);
    }
}

alternarPalcoAmplo = function () {
    modoPalcoLimpoAtivo = !modoPalcoLimpoAtivo;
    document.getElementById("btn_palco_amplo").classList.toggle("ativo", modoPalcoLimpoAtivo);

    const paineis = ["hud_construtor", "hud_engenharia", "hud_direita"];
    paineis.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (modoPalcoLimpoAtivo) {
            el.classList.add("oculto");
        } else if (id !== "hud_engenharia") {
            el.classList.remove("oculto");
        }
    });

    document.getElementById("btn_hud_construtor").classList.toggle("ativo", !modoPalcoLimpoAtivo);
    document.getElementById("btn_hud_direita").classList.toggle("ativo", !modoPalcoLimpoAtivo);
    if (modoPalcoLimpoAtivo) document.getElementById("btn_hud_engenharia").classList.remove("ativo");

    if (renderer && camera) {
        const container = document.getElementById("canvas-container");
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
};

selecionarPecaParaPintura = function (pecaDict) {
    pecaIndividualSelecionada = pecaDict;
    abrirAbaDireita("MATERIAIS");

    document.getElementById("nome_peca_pintor").innerText =
        `🪵 ${pecaDict.nome_comercial} (${pecaDict.dimensoes_2d_planificadas.largura_x}x${pecaDict.dimensoes_2d_planificadas.altura_y}mm)`;
    document.getElementById("mat_peca_ind").value = pecaDict.material || "generico_branco_tx";
    document.getElementById("fita_peca_ind").value = pecaDict.cor_fita_borda || pecaDict.material || "generico_branco_tx";

    const fb = pecaDict.fitas_borda || {};
    document.getElementById("chk_fita_base").checked = !!fb.base;
    document.getElementById("chk_fita_topo").checked = !!fb.topo;
    document.getElementById("chk_fita_esq").checked = !!fb.esquerda;
    document.getElementById("chk_fita_dir").checked = !!fb.direita;
};

// =============================================================================
// 2. CONTROLES SEPARADOS DE ABERTURA (PORTAS vs GAVETAS) E OCULTAR FRENTES
// =============================================================================
function alternarOcultarFrentes() {
    ocultarFrentesExternas = !ocultarFrentesExternas;
    const btn = document.getElementById("btn_ocultar_frentes");
    if (btn) btn.classList.toggle("ativo", ocultarFrentesExternas);
    atualizarCinematica3D();
}

atualizarCinematica3D = function () {
    const elExp = document.getElementById("rng_explosao");
    const elPortas = document.getElementById("rng_abertura_portas");
    const elGavetas = document.getElementById("rng_abertura_gavetas");

    const fatorExplosao = elExp ? parseFloat(elExp.value) : 0.0;
    const pctPortas = elPortas ? (parseFloat(elPortas.value) / 100.0) : 0.0;
    const pctGavetas = elGavetas ? (parseFloat(elGavetas.value) / 100.0) : 0.0;

    const categoriasFrentesExternas = [
        "porta_giro_esquerda", "porta_giro_direita", "porta_basculante",
        "frente_gaveta", "frente_porta_tempero"
    ];

    grupoAmbienteModulos.children.forEach(grupoMod => {
        grupoMod.children.forEach(container => {
            if (!container.userData || !container.userData.peca) return;
            const orig = container.userData.posOriginal;
            const dir = container.userData.vetorExplosao;
            const p = container.userData.peca;
            const cat = p.categoria_industrial.toLowerCase();

            // Oculta portas e frentes externas se o botão "🙈 S/ Frentes" estiver ativo
            if (categoriasFrentesExternas.includes(cat)) {
                container.visible = !ocultarFrentesExternas;
            } else {
                container.visible = true;
            }

            const baseX = orig.x + dir.x * fatorExplosao;
            const baseY = orig.y + dir.y * fatorExplosao;
            const baseZ = orig.z + dir.z * fatorExplosao;

            container.rotation.set(0, 0, 0);

            // 1. Movimento exclusivo de Gavetas, Sapateiras e Porta-Tempero
            if (cat.includes("gaveta") || cat.includes("tempero") || cat.includes("sapateira")) {
                if (!cat.includes("engrosso")) {
                    container.position.set(baseX, baseY, baseZ + (pctGavetas * 340.0));
                } else {
                    container.position.set(baseX, baseY, baseZ);
                }
            }
            // 2. Movimento exclusivo de Porta Basculante
            else if (cat.includes("porta_basculante")) {
                const meiaAlt = p.dimensoes.z / 2.0;
                const anguloBasc = pctPortas * ((95.0 * Math.PI) / 180.0);
                const yDobradicaTopo = baseY + meiaAlt;
                const dyCentro = baseY - yDobradicaTopo;

                container.position.set(
                    baseX,
                    yDobradicaTopo + dyCentro * Math.cos(anguloBasc),
                    baseZ - dyCentro * Math.sin(anguloBasc)
                );
                container.rotation.x = -anguloBasc;
            }
            // 3. Movimento exclusivo de Portas de Giro
            else if (cat.includes("porta_giro")) {
                const ehDireita = cat.includes("direita");
                const meiaLarg = p.dimensoes.x / 2.0;
                const angulo = pctPortas * ((92.0 * Math.PI) / 180.0) * (ehDireita ? 1.0 : -1.0);
                const xDobradica = ehDireita ? (baseX + meiaLarg) : (baseX - meiaLarg);
                const dxCentro = baseX - xDobradica;

                container.position.set(
                    xDobradica + dxCentro * Math.cos(angulo),
                    baseY,
                    baseZ - dxCentro * Math.sin(angulo)
                );
                container.rotation.y = angulo;
            } else {
                container.position.set(baseX, baseY, baseZ);
            }
        });
    });
};

// =============================================================================
// 3. MOTOR DE TEXTURAS DE 6 FACES (MDF LAMINADO + FITA + MDF CRU NOS TOPOS)
// =============================================================================
function gerarCanvasTexturaProcedural(hexColor, temVeio, rotacionarVeio90, ehMdfCru = false) {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    const c = new THREE.Color(hexColor);
    const rBase = Math.floor(c.r * 255);
    const gBase = Math.floor(c.g * 255);
    const bBase = Math.floor(c.b * 255);

    ctx.fillStyle = `rgb(${rBase}, ${gBase}, ${bBase})`;
    ctx.fillRect(0, 0, 512, 512);

    if (rotacionarVeio90) {
        ctx.translate(256, 256);
        ctx.rotate(Math.PI / 2);
        ctx.translate(-256, -256);
    }

    if (ehMdfCru) {
        // Fibras granuladas características de topo de MDF Cru
        for (let i = 0; i < 2200; i++) {
            const delta = (Math.random() - 0.5) * 32;
            const r = Math.min(255, Math.max(0, Math.floor(rBase + delta)));
            const g = Math.min(255, Math.max(0, Math.floor(gBase + delta * 0.85)));
            const b = Math.min(255, Math.max(0, Math.floor(bBase + delta * 0.7)));
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.45)`;
            ctx.fillRect(Math.random() * 512, Math.random() * 512, 4 + Math.random() * 8, 2 + Math.random() * 3);
        }
    } else if (temVeio) {
        for (let i = 0; i < 160; i++) {
            const x = Math.random() * 512;
            const larg = 1 + Math.random() * 5;
            const escurecer = (Math.random() - 0.48) * 26;
            const r = Math.min(255, Math.max(0, Math.floor(rBase + escurecer)));
            const g = Math.min(255, Math.max(0, Math.floor(gBase + escurecer)));
            const b = Math.min(255, Math.max(0, Math.floor(bBase + escurecer)));
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.38)`;
            ctx.fillRect(x, 0, larg, 512);
        }
    } else {
        for (let i = 0; i < 900; i++) {
            const delta = (Math.random() - 0.5) * 10;
            const r = Math.min(255, Math.max(0, Math.floor(rBase + delta)));
            const g = Math.min(255, Math.max(0, Math.floor(gBase + delta)));
            const b = Math.min(255, Math.max(0, Math.floor(bBase + delta)));
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.25)`;
            ctx.fillRect(Math.random() * 512, Math.random() * 512, 3, 3);
        }
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    return tex;
}

function obterTexturaMDF(idMaterial, hexColor, temVeio, orientacao3D) {
    const girarVeio = temVeio && (orientacao3D === "HORIZONTAL_XY");
    const chaveCache = `${idMaterial}_${girarVeio ? "H" : "V"}`;

    if (cacheTexturasThree[chaveCache]) {
        return cacheTexturasThree[chaveCache];
    }

    const infoCat = (catalogoMateriaisCache || []).find(m => m.id === idMaterial);
    if (infoCat && infoCat.textura_url) {
        const texReal = loaderTextura.load(infoCat.textura_url);
        texReal.wrapS = THREE.RepeatWrapping;
        texReal.wrapT = THREE.RepeatWrapping;
        if (girarVeio) {
            texReal.center.set(0.5, 0.5);
            texReal.rotation = Math.PI / 2;
        }
        cacheTexturasThree[chaveCache] = texReal;
        return texReal;
    }

    const texProc = gerarCanvasTexturaProcedural(hexColor, temVeio, girarVeio, idMaterial === "mdf_cru");
    cacheTexturasThree[chaveCache] = texProc;
    return texProc;
}

function criarMaterialFace(idMat, orientacao) {
    const corHex = MAPA_HEX_MATERIAIS[idMat] || 0xECEFF1;
    const info = (catalogoMateriaisCache || []).find(m => m.id === idMat);
    const temVeio = info ? !!info.veio : false;
    const tex = obterTexturaMDF(idMat, corHex, temVeio, orientacao);

    return new THREE.MeshStandardMaterial({
        color: 0xFFFFFF,
        map: tex,
        roughness: idMat === "mdf_cru" ? 0.85 : (temVeio ? 0.48 : 0.62)
    });
}

function construirArray6MateriaisPeca(p) {
    const idLaminado = p.material || "generico_branco_tx";
    const cat = (p.categoria_industrial || "").toLowerCase();

    // Se for Bancada/Rodapé de Pedra, Cuba Inox ou Cooktop, todas as 6 faces são da própria pedra/inox!
    if (cat.startsWith("marmoraria_") || cat.startsWith("acessorio_")) {
        const matUnico = criarMaterialFace(idLaminado, "HORIZONTAL_XY");
        return [matUnico, matUnico, matUnico, matUnico, matUnico, matUnico];
    }

    const idFita = (p.cor_fita_borda && p.cor_fita_borda !== "SEM_FITA") ? p.cor_fita_borda : idLaminado;
    const fb = p.fitas_borda || {};

    const matFacePrincipal = criarMaterialFace(idLaminado, p.orientacao_3d);
    const matCru = criarMaterialFace("mdf_cru", "HORIZONTAL_XY");
    const matFitaH = criarMaterialFace(idFita, "HORIZONTAL_XY");
    const matFitaV = criarMaterialFace(idFita, "VERTICAL_YZ");

    // Ordem das 6 faces no BoxGeometry do Three.js: [0:+X(Dir), 1:-X(Esq), 2:+Y(Topo), 3:-Y(Base), 4:+Z(Frente), 5:-Z(Trás)]
    if (p.orientacao_3d === "HORIZONTAL_XY") {
        // Faces 2 (+Y) e 3 (-Y) são as faces laminadas; as outras 4 são topos (Fita ou MDF Cru!)
        return [
            fb.direita ? matFitaH : matCru,   // 0: +X (Direita)
            fb.esquerda ? matFitaH : matCru,  // 1: -X (Esquerda)
            matFacePrincipal,                 // 2: +Y (Face Superior Laminada)
            matFacePrincipal,                 // 3: -Y (Face Inferior Laminada)
            fb.base ? matFitaH : matCru,      // 4: +Z (Frente Y=0)
            fb.topo ? matFitaH : matCru       // 5: -Z (Traseira Y=dy)
        ];
    } else if (p.orientacao_3d === "VERTICAL_YZ") {
        // Faces 0 (+X) e 1 (-X) são as faces laminadas das laterais/divisórias
        return [
            matFacePrincipal,                 // 0: +X (Face Direita Laminada)
            matFacePrincipal,                 // 1: -X (Face Esquerda Laminada)
            fb.topo ? matFitaH : matCru,      // 2: +Y (Topo Z=dz)
            fb.base ? matFitaH : matCru,      // 3: -Y (Base Z=0)
            fb.esquerda ? matFitaV : matCru,  // 4: +Z (Frente Y=0)
            fb.direita ? matFitaV : matCru    // 5: -Z (Traseira Y=dy)
        ];
    } else {
        // FRONTAL_XZ (Portas, Frentes de Gaveta, Traseiras, Travessas em Pé, Fundo Costa)
        // Faces 4 (+Z) e 5 (-Z) são as faces laminadas
        return [
            fb.direita ? matFitaV : matCru,   // 0: +X (Direita)
            fb.esquerda ? matFitaV : matCru,  // 1: -X (Esquerda)
            fb.topo ? matFitaH : matCru,      // 2: +Y (Topo Z=dz)
            fb.base ? matFitaH : matCru,      // 3: -Y (Base Z=0)
            matFacePrincipal,                 // 4: +Z (Face Frontal Laminada)
            matFacePrincipal                  // 5: -Z (Face Traseira Laminada)
        ];
    }
}

const _renderizarCenaOriginal = renderizarCenaCompleta;
renderizarCenaCompleta = function () {
    _renderizarCenaOriginal();

    if (modoRaioX) return;

    grupoAmbienteModulos.traverse(obj => {
        if (!obj.isMesh) return;

        // Aplica o Array de 6 Materiais (Laminado nas faces, Fita onde tem fita, e MDF Cru onde não tem fita!)
        if (obj.name === "corpo_mdf" && obj.parent && obj.parent.userData.peca) {
            const p = obj.parent.userData.peca;
            obj.material = construirArray6MateriaisPeca(p);
            obj.material.needsUpdate = true;
        }
        // Quando o botão "📼 Mapa Fitas" é ativado, pinta o destaque em Vermelho Técnico para conferência!
        else if (obj.userData && obj.userData.ehFitaBorda) {
            obj.material.map = null;
            obj.material.color.setHex(0xFF1744);
            obj.material.needsUpdate = true;
        }
    });
};

// =============================================================================
// 6. TAMPONAMENTO INTELIGENTE (INDIVIDUAL / LOTE) & REDIMENSIONAMENTO DE PEÇA
// =============================================================================
let pecaTamponamentoEmEdicao = null;

async function aplicarTamponamentoNoModulo(ativar) {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    const configTamp = {
        ativo: ativar,
        lateral_esquerda: document.getElementById("chk_tamp_esq").checked,
        lateral_direita: document.getElementById("chk_tamp_dir").checked,
        vista_superior_l: document.getElementById("chk_tamp_vista_l").checked,
        topo_passante: document.getElementById("chk_tamp_topo").checked,
        espessura_mm: parseFloat(document.getElementById("sel_esp_tamp").value),
        avanco_frontal_mm: parseFloat(document.getElementById("inp_tamp_avanco").value),
        subida_topo_mm: parseFloat(document.getElementById("inp_tamp_subida").value),
        largura_aba_l_mm: parseFloat(document.getElementById("inp_tamp_aba_l").value),
        descida_base_mm: parseFloat(document.getElementById("inp_tamp_descida").value),
        profundidade_lateral_mm: parseFloat(document.getElementById("inp_tamp_prof_lat").value || 0),
        fechamento_esquerda: document.getElementById("chk_fech_esq").checked,
        fechamento_direita: document.getElementById("chk_fech_dir").checked,
        largura_fechamento_mm: parseFloat(document.getElementById("inp_larg_fech").value),
        espessura_fechamento_mm: parseFloat(document.getElementById("inp_esp_fech").value)
    };

    const resp = await fetch("/api/modulos/tamponamento_inteligente", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids, config_tamponamento: configTamp })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        await carregarEstadoAmbiente();
    } else {
        alert(dados.erro_engenharia || dados.erro_interno);
    }
}

function abrirModalRedimensionarTamp(pecaDict, idMod) {
    pecaTamponamentoEmEdicao = { peca: pecaDict, idModulo: idMod };
    document.getElementById("lbl_nome_peca_tamp_edit").innerText = `🪵 ${pecaDict.nome_comercial} (Mód. #${idMod})`;
    document.getElementById("inp_tamp_edit_dx").value = pecaDict.dimensoes.x;
    document.getElementById("inp_tamp_edit_dy").value = pecaDict.dimensoes.y;
    document.getElementById("inp_tamp_edit_dz").value = pecaDict.dimensoes.z;
    document.getElementById("inp_tamp_off_x").value = 0;
    document.getElementById("inp_tamp_off_y").value = 0;
    document.getElementById("inp_tamp_off_z").value = 0;
    document.getElementById("modal_redimensionar_tamp").style.display = "block";
}

function fecharModalRedimensionarTamp() {
    pecaTamponamentoEmEdicao = null;
    document.getElementById("modal_redimensionar_tamp").style.display = "none";
}

async function salvarRedimensionamentoPecaTamp(resetar) {
    if (!pecaTamponamentoEmEdicao) return;
    const resp = await fetch("/api/modulo/redimensionar_peca_tamp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: pecaTamponamentoEmEdicao.idModulo,
            nome_comercial: pecaTamponamentoEmEdicao.peca.nome_comercial,
            dx: parseFloat(document.getElementById("inp_tamp_edit_dx").value),
            dy: parseFloat(document.getElementById("inp_tamp_edit_dy").value),
            dz: parseFloat(document.getElementById("inp_tamp_edit_dz").value),
            offset_x: parseFloat(document.getElementById("inp_tamp_off_x").value),
            offset_y: parseFloat(document.getElementById("inp_tamp_off_y").value),
            offset_z: parseFloat(document.getElementById("inp_tamp_off_z").value),
            resetar: resetar
        })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        fecharModalRedimensionarTamp();
        await carregarEstadoAmbiente();
    }
}

// =============================================================================
// 7. TRAVA ORTOGONAL DE PAREDE 2D, ARRASTE 3D COM COLISÃO/SNAP E CLIQUE EM PEÇA
// =============================================================================
let grupoPreviewParedeVerde = new THREE.Group();
let grupoCotasEReguas3D = new THREE.Group();
let primeiroVerticeSala2D = null;
let ultimoVerticeSnapped2D = null;

let modoArrastarModuloAtivo = true;
let estadoArraste3D = null;

function alternarModoArrastar3D() {
    modoArrastarModuloAtivo = !modoArrastarModuloAtivo;
    const btn = document.getElementById("btn_arrastar_modulo");
    if (btn) btn.classList.toggle("ativo", modoArrastarModuloAtivo);
}

function criarSpriteTextoCAD(texto, corTexto = "#FF1744", corFundo = "rgba(255,255,255,0.92)", escala = 240) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = corFundo;
    ctx.fillRect(8, 8, 240, 48);
    ctx.strokeStyle = "#1E88E5";
    ctx.lineWidth = 3;
    ctx.strokeRect(8, 8, 240, 48);

    ctx.fillStyle = corTexto;
    ctx.font = "bold 28px 'Segoe UI', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(texto, 128, 32);

    const tex = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({ map: tex, depthTest: false });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(escala, escala * 0.25, 1);
    return sprite;
}

function atualizarCotasDinamicasEReguasParede() {
    if (!scene.children.includes(grupoCotasEReguas3D)) scene.add(grupoCotasEReguas3D);
    grupoCotasEReguas3D.clear();

    if (modoCamera === "PLANTA_2D" || !moduloAtivo || !moduloAtivo.posicionamento_ambiente) return;

    const pos = moduloAtivo.posicionamento_ambiente;
    const parede = (ambienteCache.paredes || []).find(p => p.id_parede === pos.id_parede);
    if (!parede) return;

    const grupoLocalParede = new THREE.Group();
    grupoLocalParede.position.set(parede.x1, 0, parede.y1);
    grupoLocalParede.rotation.y = -THREE.MathUtils.degToRad(parede.angulo_graus || 0);

    const alturasPadrao = [70, 150, 900, 1500, 1905, 2310];
    const matLinhaRegua = new THREE.LineBasicMaterial({ color: 0x90A4AE });
    alturasPadrao.forEach(h => {
        if (h > parede.pe_direito) return;
        const pts = [new THREE.Vector3(0, h, 8), new THREE.Vector3(140, h, 8)];
        grupoLocalParede.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), matLinhaRegua));
        const sp = criarSpriteTextoCAD(String(h), "#546E7A", "rgba(255,255,255,0.75)", 140);
        sp.position.set(75, h + 22, 12);
        grupoLocalParede.add(sp);
    });

    const xMod = pos.distancia_x_parede || 0;
    const zMod = pos.elevacao_z || 0;
    const largMod = moduloAtivo.dimensoes_ocupadas.largura_x;
    const altMod = moduloAtivo.dimensoes_ocupadas.altura_y;

    const distEsq = Math.round(xMod);
    const distDir = Math.round(parede.comprimento - (xMod + largMod));
    const distTeto = Math.round(parede.pe_direito - (zMod + altMod));
    const zMeioMod = zMod + (altMod / 2.0);
    const xMeioMod = xMod + (largMod / 2.0);

    const matCotaAzul = new THREE.LineBasicMaterial({ color: 0x1E88E5, linewidth: 2 });

    if (distEsq > 5) {
        const ptsEsq = [new THREE.Vector3(0, zMeioMod, 15), new THREE.Vector3(xMod, zMeioMod, 15)];
        grupoLocalParede.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ptsEsq), matCotaAzul));
        const spEsq = criarSpriteTextoCAD(`${distEsq}`, "#D50000", "rgba(255,255,255,0.92)", 190);
        spEsq.position.set(xMod / 2.0, zMeioMod + 35, 20);
        grupoLocalParede.add(spEsq);
    }

    if (distDir > 5) {
        const ptsDir = [new THREE.Vector3(xMod + largMod, zMeioMod, 15), new THREE.Vector3(parede.comprimento, zMeioMod, 15)];
        grupoLocalParede.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ptsDir), matCotaAzul));
        const spDir = criarSpriteTextoCAD(`${distDir}`, "#D50000", "rgba(255,255,255,0.92)", 190);
        spDir.position.set(xMod + largMod + (distDir / 2.0), zMeioMod + 35, 20);
        grupoLocalParede.add(spDir);
    }

    if (distTeto > 5) {
        const ptsTeto = [new THREE.Vector3(xMeioMod, zMod + altMod, 15), new THREE.Vector3(xMeioMod, parede.pe_direito, 15)];
        grupoLocalParede.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ptsTeto), matCotaAzul));
        const spTeto = criarSpriteTextoCAD(`${distTeto}`, "#D50000", "rgba(255,255,255,0.92)", 190);
        spTeto.position.set(xMeioMod + 65, zMod + altMod + (distTeto / 2.0), 20);
        grupoLocalParede.add(spTeto);
    }

    grupoCotasEReguas3D.add(grupoLocalParede);
}

const _renderComTexturas = renderizarCenaCompleta;
renderizarCenaCompleta = function () {
    _renderComTexturas();
    atualizarCotasDinamicasEReguasParede();
    if (moduloAtivo) {
        const lblT = document.getElementById("lbl_mod_tamp");
        if (lblT) {
            const qtdSel = idsSelecionados.size;
            lblT.innerText = qtdSel > 1 ? `${qtdSel} Módulos em Lote` : `#${moduloAtivo.id_modulo}`;
        }
    }
};

// Calcula a posição X ao longo da parede com SNAP MAGNÉTICO e COLISÃO SÓLIDA contra módulos vizinhos!
function calcularXComSnapEColisao(modArrastado, xProposto, parede) {
    const larg = modArrastado.dimensoes_ocupadas.largura_x;
    const alt = modArrastado.dimensoes_ocupadas.altura_y;
    const zIni = (modArrastado.posicionamento_ambiente && modArrastado.posicionamento_ambiente.elevacao_z) || 0;
    const zFim = zIni + alt;
    const TOLERANCIA_SNAP = 45.0;

    let xFinal = Math.round(xProposto / 10.0) * 10.0;

    // 1. Snap no início (X=0) e no fim da parede
    if (Math.abs(xFinal) <= TOLERANCIA_SNAP) xFinal = 0.0;
    if (Math.abs((xFinal + larg) - parede.comprimento) <= TOLERANCIA_SNAP) {
        xFinal = parede.comprimento - larg;
    }
    xFinal = Math.max(0.0, Math.min(parede.comprimento - larg, xFinal));

    
    // 2. Verifica todos os outros módulos na mesma parede que se sobrepõem na altura Z
    const ehBancadaOuRodape = ["MODULO_BANCADA_PEDRA", "MODULO_RODAPE"].includes(modArrastado.familia);
    const vizinhos = modulosCache.filter(m => {
        if (m.id_modulo === modArrastado.id_modulo) return false;
        // Bancadas e Rodapés podem deslizar livremente por cima/baixo dos armários sem travar neles!
        if (ehBancadaOuRodape || ["MODULO_BANCADA_PEDRA", "MODULO_RODAPE"].includes(m.familia)) return false;

        const posM = m.posicionamento_ambiente || {};
        if (posM.id_parede !== parede.id_parede) return false;
        const mZIni = posM.elevacao_z || 0;
        const mZFim = mZIni + m.dimensoes_ocupadas.altura_y;
        return (zIni < mZFim - 5) && (zFim > mZIni + 5);
    });

    vizinhos.forEach(v => {
        const vxIni = v.posicionamento_ambiente.distancia_x_parede || 0;
        const vxFim = vxIni + v.dimensoes_ocupadas.largura_x;

        // A) Snap Magnético encostando na direita do vizinho
        if (Math.abs(xFinal - vxFim) <= TOLERANCIA_SNAP) {
            xFinal = vxFim;
        }
        // B) Snap Magnético encostando na esquerda do vizinho
        else if (Math.abs((xFinal + larg) - vxIni) <= TOLERANCIA_SNAP) {
            xFinal = vxIni - larg;
        }

        // C) Barreira de Colisão Sólida (Impede atravessar o vizinho!)
        const sobrepoeX = (xFinal < vxFim - 1) && ((xFinal + larg) > vxIni + 1);
        if (sobrepoeX) {
            const centroAtual = (modArrastado.posicionamento_ambiente.distancia_x_parede || 0) + (larg / 2.0);
            const centroVizinho = vxIni + (v.dimensoes_ocupadas.largura_x / 2.0);
            if (centroAtual >= centroVizinho) {
                xFinal = vxFim; // Trava encostado no lado direito do vizinho
            } else {
                xFinal = Math.max(0, vxIni - larg); // Trava encostado no lado esquerdo do vizinho
            }
        }
    });

    return Math.round(xFinal);
}

window.addEventListener("load", () => {
    scene.add(grupoPreviewParedeVerde);
    const container = document.getElementById("canvas-container");

    // A) INTERCEPTA O CLIQUE NA PLANTA 2D EM FASE DE CAPTURA (Garante Trava Ortogonal 90°/0° Cravada!)
    container.addEventListener("pointerup", async (event) => {
        if (modoCamera === "PLANTA_2D" && event.button === 0) {
            event.stopImmediatePropagation(); // Impede o clique sem trava do estudio_3d.js!

            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);

            const pt = new THREE.Vector3();
            raycaster.ray.intersectPlane(planoPiso, pt);
            if (!pt) return;

            if (!pontoInicialParede2D) {
                const xGrid = Math.round(pt.x / 50.0) * 50.0;
                const yGrid = Math.round(pt.z / 50.0) * 50.0;
                pontoInicialParede2D = { x: xGrid, y: yGrid };
                if (!primeiroVerticeSala2D) primeiroVerticeSala2D = { x: xGrid, y: yGrid };
                document.getElementById("status_desenho_2d").innerText =
                    `📍 Origem (${xGrid}, ${yGrid}) travada! Mova o mouse (Segure Shift p/ 45°).`;
            } else if (ultimoVerticeSnapped2D && ultimoVerticeSnapped2D.dist >= 100) {
                const xFim = ultimoVerticeSnapped2D.x;
                const yFim = ultimoVerticeSnapped2D.y;

                await fetch("/api/ambiente/parede/adicionar", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        x1: pontoInicialParede2D.x,
                        y1: pontoInicialParede2D.y,
                        x2: xFim,
                        y2: yFim,
                        pe_direito: parseFloat(document.getElementById("inp_pe_direito").value),
                        espessura: parseFloat(document.getElementById("inp_esp_parede").value)
                    })
                });
                // Engata a próxima parede exatamente no ponto final ortogonal!
                pontoInicialParede2D = { x: xFim, y: yFim };
                ultimoVerticeSnapped2D = null;
                grupoPreviewParedeVerde.clear();
                await carregarEstadoAmbiente();
            }
            return;
        }

        // Finaliza o arraste 3D do módulo e grava na pilha do servidor
        if (estadoArraste3D) {
            const arr = estadoArraste3D;
            estadoArraste3D = null;
            controls.enabled = true;
            if (arr.moveu) {
                await fetch("/api/modulo/posicionar", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        id_modulo: arr.modulo.id_modulo,
                        id_parede: arr.parede.id_parede,
                        distancia_x_parede: arr.novoX,
                        elevacao_z: arr.modulo.posicionamento_ambiente.elevacao_z,
                        afastamento_parede: arr.modulo.posicionamento_ambiente.afastamento_parede,
                        rotacao_offset_graus: arr.modulo.posicionamento_ambiente.rotacao_offset_graus,
                        usar_autosnap: false
                    })
                });
                await carregarEstadoAmbiente();
                return;
            }
        }
    }, true);

    // B) INÍCIO DO ARRASTE 3D DE MÓDULO E SELEÇÃO DIRETA DE PEÇA NO 3D
    container.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || modoCamera === "PLANTA_2D") return;

        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);

        const malhasMdf = [];
        grupoAmbienteModulos.traverse(obj => {
            if (obj.isMesh && obj.name === "corpo_mdf") malhasMdf.push(obj);
        });

        const hits = raycaster.intersectObjects(malhasMdf, false);
        if (hits.length > 0) {
            const meshClicada = hits[0].object;
            const idMod = meshClicada.userData.idModulo;
            const pecaClicada = meshClicada.parent ? meshClicada.parent.userData.peca : null;

            // 1. Se clicou numa peça no 3D, já alimenta o Pintor de Peça Individual!
            if (pecaClicada) {
                pecaIndividualSelecionada = pecaClicada;
                destacarPecaSelecionadaNoPalco3D();
                const elNomeP = document.getElementById("nome_peca_pintor");
                if (elNomeP) {
                    elNomeP.innerText = `🪵 ${pecaClicada.nome_comercial} (${pecaClicada.dimensoes_2d_planificadas.largura_x}x${pecaClicada.dimensoes_2d_planificadas.altura_y}mm)`;
                    document.getElementById("mat_peca_ind").value = pecaClicada.material || "generico_branco_tx";
                    document.getElementById("fita_peca_ind").value = pecaClicada.cor_fita_borda || pecaClicada.material || "generico_branco_tx";
                    const fb = pecaClicada.fitas_borda || {};
                    document.getElementById("chk_fita_base").checked = !!fb.base;
                    document.getElementById("chk_fita_topo").checked = !!fb.topo;
                    document.getElementById("chk_fita_esq").checked = !!fb.esquerda;
                    document.getElementById("chk_fita_dir").checked = !!fb.direita;
                }

                // Se a peça clicada for de Tamponamento ou Fechamento, abre o menu;
                // caso contrário (clicou numa porta, lateral ou gaveta), fecha o menu na hora!
                if (pecaClicada.categoria_industrial === "painel_tamponamento" && idMod) {
                    abrirModalRedimensionarTamp(pecaClicada, idMod);
                } else {
                    fecharModalRedimensionarTamp();
                }
            }

            // 2. Prepara o Arraste Magnético do Módulo ao longo da parede (se ativo)
            if (modoArrastarModuloAtivo && modoCamera === "AMBIENTE_3D" && !event.shiftKey) {
                const mod = modulosCache.find(m => m.id_modulo === idMod);
                if (mod && mod.posicionamento_ambiente && mod.posicionamento_ambiente.id_parede) {
                    const parede = (ambienteCache.paredes || []).find(p => p.id_parede === mod.posicionamento_ambiente.id_parede);
                    if (parede) {
                        const grupo3D = grupoAmbienteModulos.children.find(g => g.userData.idModulo === idMod);
                        const ptPiso = new THREE.Vector3();
                        raycaster.ray.intersectPlane(planoPiso, ptPiso);
                        const ux = parede.vetor_direcao.ux;
                        const uy = parede.vetor_direcao.uy;
                        const projMouseIni = ((ptPiso.x - parede.x1) * ux) + ((ptPiso.z - parede.y1) * uy);

                        estadoArraste3D = {
                            modulo: mod,
                            parede: parede,
                            grupo3D: grupo3D,
                            xInicialMod: mod.posicionamento_ambiente.distancia_x_parede || 0,
                            projMouseIni: projMouseIni,
                            novoX: mod.posicionamento_ambiente.distancia_x_parede || 0,
                            moveu: false
                        };
                        controls.enabled = false; // Pausa o giro da câmera enquanto arrasta o móvel!
                    }
                }
            }
        } else { fecharModalRedimensionarTamp(); }
    });

    // C) MOVIMENTO DO MOUSE: PREVIEW ORTOGONAL DE PAREDE 2D + ARRASTE DE MÓDULO 3D COM SNAP E COLISÃO
    container.addEventListener("pointermove", (event) => {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);

        // CASO 1: Arrastando um Módulo no Ambiente 3D com Snap e Colisão!
        if (estadoArraste3D) {
            const ptPiso = new THREE.Vector3();
            raycaster.ray.intersectPlane(planoPiso, ptPiso);
            if (!ptPiso) return;

            const par = estadoArraste3D.parede;
            const ux = par.vetor_direcao.ux;
            const uy = par.vetor_direcao.uy;
            const projAtual = ((ptPiso.x - par.x1) * ux) + ((ptPiso.z - par.y1) * uy);
            const deltaX = projAtual - estadoArraste3D.projMouseIni;

            if (Math.abs(deltaX) > 8) {
                estadoArraste3D.moveu = true;
                const xBruto = estadoArraste3D.xInicialMod + deltaX;
                const xComSnap = calcularXComSnapEColisao(estadoArraste3D.modulo, xBruto, par);
                estadoArraste3D.novoX = xComSnap;
                estadoArraste3D.modulo.posicionamento_ambiente.distancia_x_parede = xComSnap;

                // Atualiza a posição 3D em tempo real a 60fps
                const nx = par.vetor_normal_interno.nx;
                const ny = par.vetor_normal_interno.ny;
                const afast = estadoArraste3D.modulo.posicionamento_ambiente.afastamento_parede || 0;
                const posXGlobal = par.x1 + (ux * xComSnap) + (nx * afast);
                const posZGlobal = par.y1 + (uy * xComSnap) + (ny * afast);

                if (estadoArraste3D.grupo3D) {
                    estadoArraste3D.grupo3D.position.x = posXGlobal;
                    estadoArraste3D.grupo3D.position.z = posZGlobal;
                }
                document.getElementById("inp_dist_x_parede").value = xComSnap;
                atualizarCotasDinamicasEReguasParede();
            }
            return;
        }

        // CASO 2: Desenho de Parede 2D com Trava Ortogonal 90° Padrão (ou 45° segurando Shift)
        if (modoCamera !== "PLANTA_2D" || !pontoInicialParede2D) {
            grupoPreviewParedeVerde.clear();
            return;
        }

        const pt = new THREE.Vector3();
        raycaster.ray.intersectPlane(planoPiso, pt);
        if (!pt) return;

        const dxBruto = pt.x - pontoInicialParede2D.x;
        const dyBruto = pt.z - pontoInicialParede2D.y;

        // Trava Ortogonal Estrita (90° por padrão; libera 45° se segurar Shift!)
        const passoAngulo = event.shiftKey ? 45.0 : 90.0;
        let angGraus = Math.atan2(dyBruto, dxBruto) * (180.0 / Math.PI);
        angGraus = Math.round(angGraus / passoAngulo) * passoAngulo;
        if (angGraus === -180) angGraus = 180;

        const rad = THREE.MathUtils.degToRad(angGraus);
        // Projeta a distância exatamente sobre o eixo travado!
        const distProjetada = Math.abs(dxBruto * Math.cos(rad) + dyBruto * Math.sin(rad));
        const dist = Math.round(distProjetada / 50.0) * 50.0;
        if (dist < 100) return;

        const xFim = Math.round(pontoInicialParede2D.x + dist * Math.cos(rad));
        const yFim = Math.round(pontoInicialParede2D.y + dist * Math.sin(rad));

        ultimoVerticeSnapped2D = { x: xFim, y: yFim, dist: dist, angulo: angGraus };

        grupoPreviewParedeVerde.clear();
        const esp = parseFloat(document.getElementById("inp_esp_parede").value) || 150;
        const geomPrev = new THREE.BoxGeometry(dist, 250, esp);
        const edgesPrev = new THREE.EdgesGeometry(geomPrev);
        const linePrev = new THREE.LineSegments(edgesPrev, new THREE.LineBasicMaterial({ color: 0x00E676 }));

        linePrev.position.set((pontoInicialParede2D.x + xFim) / 2.0, 125, (pontoInicialParede2D.y + yFim) / 2.0);
        linePrev.rotation.y = -rad;
        grupoPreviewParedeVerde.add(linePrev);

        const spCota = criarSpriteTextoCAD(`${dist} < ${angGraus}°`, "#FF1744", "rgba(255,255,255,0.95)", 340);
        spCota.position.set((pontoInicialParede2D.x + xFim) / 2.0, 280, (pontoInicialParede2D.y + yFim) / 2.0);
        grupoPreviewParedeVerde.add(spCota);

        document.getElementById("status_desenho_2d").innerText =
            `🔒 Trava Ortogonal: ${dist}mm | ${angGraus}° (Clique p/ fixar, Shift p/ 45°, Botão Direito p/ encerrar)`;
    });
});

// =============================================================================
// 8. DESTAQUE 3D EXATO DA PEÇA SELECIONADA E MENUS ARRASTÁVEIS / REDIMENSIONÁVEIS
// =============================================================================
function destacarPecaSelecionadaNoPalco3D() {
    const nomeAlvo = pecaIndividualSelecionada ? pecaIndividualSelecionada.nome_comercial : null;
    const idModAlvo = (pecaTamponamentoEmEdicao && pecaTamponamentoEmEdicao.idModulo)
        ? pecaTamponamentoEmEdicao.idModulo
        : (moduloAtivo ? moduloAtivo.id_modulo : null);

    // 1. Destaca a peça no Palco 3D com Contorno Ciano Brilhante e leve brilho emissivo
    grupoAmbienteModulos.traverse(obj => {
        if (obj.isMesh && obj.name === "corpo_mdf" && obj.parent && obj.parent.userData.peca) {
            const p = obj.parent.userData.peca;
            const idModPeca = obj.userData.idModulo;
            const ehPecaAlvo = (nomeAlvo && p.nome_comercial === nomeAlvo && idModPeca === idModAlvo);

            // Atualiza a cor do contorno (LineSegments irmão do mesh)
            obj.parent.children.forEach(filho => {
                if (filho.isLineSegments && filho.material) {
                    if (ehPecaAlvo) {
                        filho.material.color.setHex(0x00E5FF);
                    } else {
                        const modEhAtivo = (moduloAtivo && idModPeca === moduloAtivo.id_modulo);
                        filho.material.color.setHex(modEhAtivo ? 0x4CE660 : 0x263238);
                    }
                }
            });

            // Aplica leve brilho emissivo nas faces da peça selecionada para certeza visual imediata
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
            mats.forEach(m => {
                if (m && m.emissive) {
                    m.emissive.setHex(ehPecaAlvo ? 0x003B46 : 0x000000);
                    m.needsUpdate = true;
                }
            });
        }
    });

    // 2. Destaca o item correspondente na lista de peças à direita
    document.querySelectorAll("#lista_pecas_modulo .part-item").forEach(el => {
        const textoItem = el.innerText || "";
        const bateu = nomeAlvo && textoItem.includes(nomeAlvo);
        el.classList.toggle("peca-destacada", !!bateu);
    });
}

// Conecta o destaque de peça à seleção na lista e ao ciclo de renderização
const _selecionarPecaOrig = selecionarPecaParaPintura;
selecionarPecaParaPintura = function (pecaDict) {
    _selecionarPecaOrig(pecaDict);
    destacarPecaSelecionadaNoPalco3D();
};

const _renderFinalOrig = renderizarCenaCompleta;
renderizarCenaCompleta = function () {
    _renderFinalOrig();
    destacarPecaSelecionadaNoPalco3D();
};

// Torna todos os Menus Flutuantes (.hud-panel e .floating-modal) Arrastáveis e Redimensionáveis Proporcionalmente!
function inicializarMenusArrastaveisERedimensionaveis() {
    const paineis = document.querySelectorAll(".hud-panel, .floating-modal");

    paineis.forEach(painel => {
        const cabecalho = painel.querySelector(".hud-header") || painel.firstElementChild;

        // A) ARRASTAR PELO CABEÇALHO
        if (cabecalho) {
            cabecalho.style.cursor = "grab";
            let arrastandoMenu = false;
            let offsetMouseX = 0, offsetMouseY = 0;

            cabecalho.addEventListener("pointerdown", (e) => {
                if (["INPUT", "SELECT", "BUTTON", "SPAN"].includes(e.target.tagName) && e.target.classList.contains("hud-close")) return;
                e.stopPropagation();
                arrastandoMenu = true;
                cabecalho.style.cursor = "grabbing";

                const rect = painel.getBoundingClientRect();
                const parentRect = painel.offsetParent ? painel.offsetParent.getBoundingClientRect() : { left: 0, top: 0 };

                // Converte posicionamento 'right' ou 'transform' em 'left/top' explícitos ao iniciar o arraste
                painel.style.left = `${rect.left - parentRect.left}px`;
                painel.style.top = `${rect.top - parentRect.top}px`;
                painel.style.right = "auto";
                painel.style.transform = "none";

                offsetMouseX = e.clientX - rect.left;
                offsetMouseY = e.clientY - rect.top;
            });

            window.addEventListener("pointermove", (e) => {
                if (!arrastandoMenu) return;
                const parentRect = painel.offsetParent ? painel.offsetParent.getBoundingClientRect() : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
                let novoLeft = e.clientX - parentRect.left - offsetMouseX;
                let novoTop = e.clientY - parentRect.top - offsetMouseY;

                novoLeft = Math.max(4, Math.min(window.innerWidth - 120, novoLeft));
                novoTop = Math.max(4, Math.min(window.innerHeight - 100, novoTop));

                painel.style.left = `${novoLeft}px`;
                painel.style.top = `${novoTop}px`;
            });

            window.addEventListener("pointerup", () => {
                if (arrastandoMenu) {
                    arrastandoMenu = false;
                    cabecalho.style.cursor = "grab";
                }
            });
        }

        // B) ALÇA DE REDIMENSIONAMENTO PROPORCIONAL (CANTO INFERIOR DIREITO ◢)
        const alca = document.createElement("div");
        alca.className = "hud-resize-handle";
        alca.innerText = "◢";
        alca.title = "Arraste para redimensionar proporcionalmente (Duplo clique p/ 100%)";
        painel.appendChild(alca);

        let redimensionando = false;
        let xInicialResize = 0;
        let escalaAtual = 1.0;

        alca.addEventListener("pointerdown", (e) => {
            e.stopPropagation();
            e.preventDefault();
            redimensionando = true;
            xInicialResize = e.clientX;
        });

        alca.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            escalaAtual = 1.0;
            painel.style.zoom = "1";
        });

        window.addEventListener("pointermove", (e) => {
            if (!redimensionando) return;
            const deltaX = e.clientX - xInicialResize;
            xInicialResize = e.clientX;
            escalaAtual = Math.max(0.72, Math.min(1.35, escalaAtual + (deltaX / 320.0)));
            painel.style.zoom = String(escalaAtual.toFixed(2));
        });

        window.addEventListener("pointerup", () => {
            redimensionando = false;
        });
    });
}

window.addEventListener("load", () => {
    inicializarMenusArrastaveisERedimensionaveis();
});

// =============================================================================
// 9. RESUMO INDUSTRIAL (BOM), TELA INICIAL, SALVAR/ABRIR E CTRL+Z / CTRL+Y
// =============================================================================
let malhaPisoArquitetonico = null;

async function abrirModalResumoIndustrial() {
    const resp = await fetch("/api/ambiente/resumo_industrial");
    const dados = await resp.json();
    if (!dados.sucesso) return;

    const container = document.getElementById("conteudo_resumo_bom");
    let htmlChapas = `<div class="card"><div class="card-title" style="color:#4CE660;">1. Totalizador de Chapas MDF (Padrão 2750x1850mm + 15% Margem)</div>`;
    dados.chapas.forEach(c => {
        htmlChapas += `
            <div style="display:flex; justify-content:space-between; border-bottom:1px solid #263238; padding:4px 0;">
                <span><b>${c.nome_material}</b> (${c.espessura_mm}mm) — ${c.qtd_pecas} pçs</span>
                <span style="color:#4CE660; font-weight:bold;">${c.area_liquida_m2} m² ➔ ~${c.chapas_inteiras_estimadas} Chapa(s)</span>
            </div>`;
    });
    htmlChapas += `</div>`;

    let htmlFitas = `<div class="card"><div class="card-title" style="color:#FF9800;">2. Totalizador de Fitas de Borda (Metros Lineares c/ Destopo)</div>`;
    if (dados.fitas.length === 0) {
        htmlFitas += `<div>Nenhuma fita de borda aplicada.</div>`;
    } else {
        dados.fitas.forEach(f => {
            htmlFitas += `
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #263238; padding:4px 0;">
                    <span>Fita <b>${f.nome_cor}</b> (Largura ${f.largura_fita_mm}mm)</span>
                    <span style="color:#FFB74D; font-weight:bold;">${f.metros_lineares} metros</span>
                </div>`;
        });
    }
    htmlFitas += `</div>`;

    const fer = dados.ferragens;
    let htmlCorredicas = "";
    Object.entries(fer.corredicas_por_tamanho || {}).forEach(([nome, qtd]) => {
        htmlCorredicas += `<div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• ${nome}</span><b style="color:#00E5FF;">${qtd} par(es)</b></div>`;
    });

    const htmlFerragens = `
        <div class="card">
            <div class="card-title" style="color:#00E5FF;">3. Checklist de Ferragens & Fixadores (Almoxarifado)</div>
            <div class="row-2" style="gap:12px;">
                <div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• Dobradiças Caneco Ø35mm:</span><b>${fer.dobradicas_35mm} un.</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• Parafusos Estruturais 4.5mm:</span><b>${fer.parafusos_estruturais_4_5mm} un.</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• Tambores Minifix 15mm:</span><b>${fer.tambores_minifix_15mm} un.</b></div>
                </div>
                <div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• Cavilhas de Madeira 8mm:</span><b>${fer.cavilhas_madeira_8mm} un.</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• Pistões a Gás (Basculantes):</span><b>${fer.pistoes_gas_basculante} un.</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>• Suportes Prateleira (Pitão):</span><b>${fer.suportes_prateleira_pitao} un.</b></div>
                </div>
            </div>
            ${htmlCorredicas ? `<div style="margin-top:6px; border-top:1px solid #263238; padding-top:4px;">${htmlCorredicas}</div>` : ""}
        </div>`;

    container.innerHTML = htmlChapas + htmlFitas + htmlFerragens;
    document.getElementById("modal_resumo_bom").style.display = "block";
}

function fecharModalResumoIndustrial() {
    document.getElementById("modal_resumo_bom").style.display = "none";
}

function abrirTelaInicial() {
    voltarMenuSplash();
    document.getElementById("tela_inicial_splash").classList.remove("oculto");
}

function fecharTelaInicial() {
    document.getElementById("tela_inicial_splash").classList.add("oculto");
}

function voltarMenuSplash() {
    document.getElementById("splash_menu_principal").style.display = "flex";
    document.getElementById("dialogo_novo_projeto").style.display = "none";
    document.getElementById("dialogo_abrir_projeto").style.display = "none";
}

function abrirDialogoNovoProjeto() {
    document.getElementById("splash_menu_principal").style.display = "none";
    document.getElementById("dialogo_novo_projeto").style.display = "flex";
    document.getElementById("inp_splash_cliente").focus();
}

async function confirmarCriacaoNovoProjeto() {
    const nome_cliente = document.getElementById("inp_splash_cliente").value.trim();
    const nome_ambiente = document.getElementById("inp_splash_ambiente").value.trim();
    if (!nome_cliente || !nome_ambiente) {
        alert("⚠️ Informe o Nome do Cliente e o Nome do Ambiente para iniciar o projeto!");
        return;
    }
    const payload = {
        nome_cliente: document.getElementById("inp_splash_cliente").value,
        nome_ambiente: document.getElementById("inp_splash_ambiente").value,
        formato_planta: document.getElementById("sel_splash_formato").value,
        larg_a: parseFloat(document.getElementById("inp_splash_larg_a").value),
        pe_direito: parseFloat(document.getElementById("inp_splash_pe_dir").value)
    };

    const resp = await fetch("/api/projeto/novo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        idsSelecionados.clear();
        moduloAtivo = null;
        fecharModalRedimensionarTamp();
        fecharTelaInicial();
        await carregarEstadoAmbiente();
    }
}

async function salvarProjetoAtual() {
    const estiloPiso = document.getElementById("sel_estilo_piso") ? document.getElementById("sel_estilo_piso").value : "GRADE_TECNICA";
    const corParede = document.getElementById("sel_cor_parede") ? document.getElementById("sel_cor_parede").value : "#263238";

    const resp = await fetch("/api/projeto/salvar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estilo_piso: estiloPiso, cor_parede: corParede })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        document.getElementById("txt_resposta_copiloto").innerText =
            `💾 Projeto salvo em '${dados.arquivo}' às ${dados.data}!`;
        await carregarEstadoAmbiente();
    }
}

async function abrirDialogoProjetosSalvos() {
    document.getElementById("splash_menu_principal").style.display = "none";
    document.getElementById("dialogo_abrir_projeto").style.display = "flex";

    const resp = await fetch("/api/projeto/listar");
    const dados = await resp.json();
    const container = document.getElementById("lista_projetos_salvos_ui");
    container.innerHTML = "";

    if (!dados.projetos || dados.projetos.length === 0) {
        container.innerHTML = `<div style="padding:12px; color:#90A4AE; text-align:center;">Nenhum projeto salvo ainda.</div>`;
        return;
    }

    dados.projetos.forEach(proj => {
        const div = document.createElement("div");
        div.className = "module-item";
        div.innerHTML = `
            <div style="flex:1;" onclick="carregarProjetoDoServidor('${proj.arquivo}')">
                <strong style="color:#4CE660;">👤 ${proj.nome_cliente}</strong> — ${proj.nome_ambiente}<br>
                <small style="color:#90A4AE;">🕒 ${proj.data_salvamento} | 📦 ${proj.qtd_modulos} mód. (${proj.total_pecas} pçs)</small>
            </div>
            <button class="btn btn-primary" onclick="carregarProjetoDoServidor('${proj.arquivo}')">Abrir</button>
            <button class="btn btn-danger" onclick="excluirProjetoDoServidor('${proj.arquivo}', event)">🗑️</button>
        `;
        container.appendChild(div);
    });
}

async function carregarProjetoDoServidor(nomeArquivo) {
    const resp = await fetch("/api/projeto/carregar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arquivo: nomeArquivo })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        idsSelecionados.clear();
        moduloAtivo = null;
        fecharModalRedimensionarTamp();
        fecharTelaInicial();
        await carregarEstadoAmbiente();
    }
}

async function excluirProjetoDoServidor(nomeArquivo, event) {
    event.stopPropagation();
    await fetch("/api/projeto/excluir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arquivo: nomeArquivo })
    });
    await abrirDialogoProjetosSalvos();
}

function exportarProjetoJSONArquivo() {
    window.open("/api/ambiente", "_blank");
}

async function acionarUndo() {
    const resp = await fetch("/api/historico/undo", { method: "POST" });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = null;
        idsSelecionados.clear();
        fecharModalRedimensionarTamp();
        await carregarEstadoAmbiente();
    }
}

async function acionarRedo() {
    const resp = await fetch("/api/historico/redo", { method: "POST" });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = null;
        idsSelecionados.clear();
        fecharModalRedimensionarTamp();
        await carregarEstadoAmbiente();
    }
}

function aplicarAcabamentoAmbiente3D() {
    const selPiso = document.getElementById("sel_estilo_piso");
    const selPar = document.getElementById("sel_cor_parede");
    const estiloPiso = selPiso ? selPiso.value : "GRADE_TECNICA";
    const corParedeHex = selPar ? selPar.value : "#263238";

    grupoParedes3D.children.forEach(meshPar => {
        if (meshPar.isMesh && meshPar.material) {
            meshPar.material.color.set(corParedeHex);
        }
    });

    if (malhaPisoArquitetonico) {
        scene.remove(malhaPisoArquitetonico);
        malhaPisoArquitetonico = null;
    }

    if (estiloPiso !== "GRADE_TECNICA") {
        let corPiso = 0xE5E5E5;
        let ehMadeira = false;
        if (estiloPiso === "MADEIRA_VINILICO") { corPiso = 0x9C6B43; ehMadeira = true; }
        else if (estiloPiso === "CIMENTO_QUEIMADO") { corPiso = 0x616161; }

        const texPiso = gerarCanvasTexturaProcedural(corPiso, ehMadeira, false, false);
        texPiso.repeat.set(8, 8);

        const geomPiso = new THREE.PlaneGeometry(8000, 8000);
        const matPiso = new THREE.MeshStandardMaterial({
            map: texPiso,
            roughness: estiloPiso === "PORCELANATO_CLARO" ? 0.18 : 0.65
        });
        malhaPisoArquitetonico = new THREE.Mesh(geomPiso, matPiso);
        malhaPisoArquitetonico.rotation.x = -Math.PI / 2;
        malhaPisoArquitetonico.position.set(2000, -1, 1500);
        scene.add(malhaPisoArquitetonico);
    }
}

const _carregarEstadoBase = carregarEstadoAmbiente;
carregarEstadoAmbiente = async function () {
    const resp = await fetch("/api/ambiente");
    const dados = await resp.json();

    if (dados.metadados) {
        const lblCli = document.getElementById("lbl_cliente_ativo");
        if (lblCli) {
            lblCli.innerText = `[👤 ${dados.metadados.nome_cliente} • ${dados.metadados.nome_ambiente}]`;
        }
    }
    if (dados.historico) {
        const bUndo = document.getElementById("btn_undo");
        const bRedo = document.getElementById("btn_redo");
        if (bUndo) bUndo.disabled = !dados.historico.pode_desfazer;
        if (bRedo) bRedo.disabled = !dados.historico.pode_refazer;
    }

    await _carregarEstadoBase();
    aplicarAcabamentoAmbiente3D();
};

window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        acionarUndo();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        acionarRedo();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        salvarProjetoAtual();
    }
});

// =============================================================================
// 10. CONSTRUTOR DE BANCADAS DE PEDRA (MARMORARIA 3D) & RODAPÉS DEDICADOS
// =============================================================================
Object.assign(MAPA_HEX_MATERIAIS, {
    "pedra_preto_sao_gabriel": 0x1A1D20,
    "pedra_quartzo_branco": 0xF5F7F8,
    "pedra_cinza_absoluto": 0x54595F,
    "pedra_travertino": 0xD8C8B0,
    "inox_escovado": 0xB0BEC5
});

let modoPedraFantasma = false;

function alternarPedraFantasma() {
    modoPedraFantasma = !modoPedraFantasma;
    const btn = document.getElementById("btn_fantasma_pedra");
    if (btn) btn.classList.toggle("ativo", modoPedraFantasma);
    renderizarCenaCompleta();
}

function obterLimitesModulosSelecionados() {
    const ids = obterListaIdsAlvo();
    const validos = modulosCache.filter(
        m => ids.includes(m.id_modulo) && !["MODULO_BANCADA_PEDRA", "MODULO_RODAPE", "MODULO_AEREO"].includes(m.familia)
    );
    if (validos.length === 0) return null;

    let minX = Infinity, maxX = -Infinity, maxZTopo = 0, maxProf = 550, idParede = null;
    validos.forEach(m => {
        const pos = m.posicionamento_ambiente || {};
        const xIni = floatOrZero(pos.distancia_x_parede);
        const xFim = xIni + m.dimensoes_ocupadas.largura_x;
        const zTopo = floatOrZero(pos.elevacao_z) + m.dimensoes_ocupadas.altura_y;
        if (xIni < minX) minX = xIni;
        if (xFim > maxX) maxX = xFim;
        if (zTopo > maxZTopo) maxZTopo = zTopo;
        if (m.dimensoes_ocupadas.profundidade_z > maxProf) maxProf = m.dimensoes_ocupadas.profundidade_z;
        if (!idParede && pos.id_parede) idParede = pos.id_parede;
    });

    return {
        ids: validos.map(v => v.id_modulo),
        xInicio: minX,
        larguraTotal: Math.round(maxX - minX),
        zTopoModulos: Math.round(maxZTopo),
        profundidadeBase: maxProf,
        idParede: idParede
    };
}

function floatOrZero(v) {
    const n = parseFloat(v);
    return isNaN(n) ? 0.0 : n;
}

async function gerarBancadaPedra(cobrirSelecionados = false) {
    let larg = parseFloat(document.getElementById("inp_banc_larg").value) || 2000;
    let prof = parseFloat(document.getElementById("inp_banc_prof").value) || 600;
    let cotaZ = parseFloat(document.getElementById("inp_banc_z").value) || 860;
    const altSaia = parseFloat(document.getElementById("inp_banc_saia").value) || 40;

    // Se criar solta ("Criar Bancada (Medidas)"), usa a Cota X atual ou 0.0 na parede ativa
    let xPosParede = 0.0;
    let idParedeAlvo = document.getElementById("sel_parede_modulo").value || null;
    if (!idParedeAlvo && ambienteCache.paredes && ambienteCache.paredes.length > 0) {
        idParedeAlvo = ambienteCache.paredes[0].id_parede;
    }

    if (cobrirSelecionados) {
        const lim = obterLimitesModulosSelecionados();
        if (!lim) {
            alert("Selecione pelo menos 1 balcão inferior para cobrir automaticamente com a bancada!");
            return;
        }
        larg = lim.larguraTotal;
        prof = lim.profundidadeBase + 35.0;
        cotaZ = lim.zTopoModulos - altSaia + 20.0;
        xPosParede = lim.xInicio;
        if (lim.idParede) idParedeAlvo = lim.idParede;

        document.getElementById("inp_banc_larg").value = larg;
        document.getElementById("inp_banc_prof").value = prof;
        document.getElementById("inp_banc_z").value = cotaZ;
    }

    let maiorNum = 0;
    modulosCache.forEach(m => {
        const n = parseInt(m.id_modulo);
        if (!isNaN(n) && n > maiorNum) maiorNum = n;
    });
    const novoId = String(maiorNum + 1).padStart(3, "0");
    const matPedraEscolhida = document.getElementById("sel_mat_pedra").value;

    const opcoesBancada = {
        espessura_pedra_mm: 20.0,
        altura_saia_frontal_mm: altSaia,
        altura_frontao_traseiro_mm: parseFloat(document.getElementById("inp_banc_frontao").value) || 0,
        cascata_esquerda: document.getElementById("chk_banc_casc_esq").checked,
        cascata_direita: document.getElementById("chk_banc_casc_dir").checked,
        altura_instalacao_z: cotaZ,
        material_pedra: matPedraEscolhida,
        possui_cuba: document.getElementById("chk_banc_cuba").checked,
        pos_x_cuba_mm: parseFloat(document.getElementById("inp_cuba_x").value) || (larg * 0.35),
        possui_cooktop: document.getElementById("chk_banc_cooktop").checked,
        pos_x_cooktop_mm: parseFloat(document.getElementById("inp_cooktop_x").value) || (larg * 0.7)
    };

    const resp = await fetch("/api/fabricar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: novoId,
            familia: "MODULO_BANCADA_PEDRA",
            largura_x: larg,
            altura_y: Math.max(altSaia, 20.0),
            profundidade_z: prof,
            material_caixaria: matPedraEscolhida,
            material_frentes: matPedraEscolhida,
            opcoes_especiais: opcoesBancada,
            id_parede: idParedeAlvo,
            distancia_x_parede: xPosParede,
            elevacao_z: cotaZ,
            usar_autosnap: false
        })
    });
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || dados.erro_interno || "Erro ao criar bancada.");
        return;
    }
    moduloAtivo = dados.modulo;
    idsSelecionados.clear();
    idsSelecionados.add(moduloAtivo.id_modulo);
    await carregarEstadoAmbiente();
}

async function gerarRodapeDedicado(sobSelecionados = false) {
    let larg = parseFloat(document.getElementById("inp_rod_larg").value) || 2000;
    const altRodape = parseFloat(document.getElementById("inp_rod_alt").value) || 150;
    const recuoFront = parseFloat(document.getElementById("inp_rod_recuo").value) || 50;
    const modeloRod = document.getElementById("sel_modelo_rodape").value;
    const espMdf = parseFloat(document.getElementById("sel_esp_rodape").value) || 15.0;

    let profBase = 550.0;
    let xPosParede = 0.0;
    let idParedeAlvo = document.getElementById("sel_parede_modulo").value || null;
    if (!idParedeAlvo && ambienteCache.paredes && ambienteCache.paredes.length > 0) {
        idParedeAlvo = ambienteCache.paredes[0].id_parede;
    }

    if (sobSelecionados) {
        const lim = obterLimitesModulosSelecionados();
        if (!lim) {
            alert("Selecione os balcões inferiores para criar o rodapé embaixo deles!");
            return;
        }
        larg = lim.larguraTotal;
        profBase = lim.profundidadeBase;
        xPosParede = lim.xInicio;
        if (lim.idParede) idParedeAlvo = lim.idParede;
        document.getElementById("inp_rod_larg").value = larg;

        await fetch("/api/modulos/transformar_lote", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids_modulos: lim.ids, z_absoluto: altRodape })
        });
    }

    let maiorNum = 0;
    modulosCache.forEach(m => {
        const n = parseInt(m.id_modulo);
        if (!isNaN(n) && n > maiorNum) maiorNum = n;
    });
    const novoId = String(maiorNum + 1).padStart(3, "0");

    const matRod = modeloRod === "PEDRA_GRANITO"
        ? document.getElementById("sel_mat_pedra").value
        : (document.getElementById("sel_mat_caixa").value || "generico_branco_tx");

    const opcoesRodape = {
        modelo_rodape: modeloRod,
        espessura_mdf_mm: espMdf,
        recuo_frontal_mm: recuoFront,
        recuo_traseiro_mm: 20.0,
        material_rodape: matRod
    };

    const resp = await fetch("/api/fabricar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: novoId,
            familia: "MODULO_RODAPE",
            largura_x: larg,
            altura_y: altRodape,
            profundidade_z: profBase,
            material_caixaria: matRod,
            material_frentes: matRod,
            opcoes_especiais: opcoesRodape,
            id_parede: idParedeAlvo,
            distancia_x_parede: xPosParede,
            elevacao_z: 0.0,
            usar_autosnap: false
        })
    });
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || dados.erro_interno || "Erro ao criar rodapé.");
        return;
    }
    moduloAtivo = dados.modulo;
    idsSelecionados.clear();
    idsSelecionados.add(moduloAtivo.id_modulo);
    await carregarEstadoAmbiente();
}