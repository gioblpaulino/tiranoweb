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
        "porta_correr_frente", "porta_correr_tras",
        "frente_gaveta", "frente_porta_tempero"
    ];

    const idsAlvo = obterListaIdsAlvo();

    // Verifica se o usuário clicou em uma frente específica (porta ou gaveta) para abrir só ela!
    const catPecaSel = pecaIndividualSelecionada ? (pecaIndividualSelecionada.categoria_industrial || "").toLowerCase() : "";
    const ehFrenteEspecificaSel = Boolean(
        pecaIndividualSelecionada && (
            catPecaSel.includes("porta") ||
            catPecaSel.includes("gaveta") ||
            catPecaSel.includes("sapateira") ||
            catPecaSel.includes("tempero")
        )
    );
    const nomePecaSel = ehFrenteEspecificaSel ? pecaIndividualSelecionada.nome_comercial : null;
    // Se selecionou "Frente Gaveta 2", extrai o número "2" para puxar o corpo da gaveta 2 junto!
    const matchNumGav = nomePecaSel ? nomePecaSel.match(/(\d+)\s*$/) : null;
    const numGavSel = matchNumGav ? matchNumGav[1] : null;

    grupoAmbienteModulos.children.forEach(grupoMod => {
        const idMod = grupoMod.userData ? grupoMod.userData.idModulo : null;
        const modSelecionado = idsAlvo.includes(idMod);

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

            // Explosão e cinemática atuam apenas no(s) módulo(s) selecionado(s)
            const expEfetiva = modSelecionado ? fatorExplosao : 0.0;
            const baseX = orig.x + dir.x * expEfetiva;
            const baseY = orig.y + dir.y * expEfetiva;
            const baseZ = orig.z + dir.z * expEfetiva;

            container.rotation.set(0, 0, 0);

            if (!modSelecionado) {
                container.position.set(baseX, baseY, baseZ);
                return;
            }

            // Define se esta peça específica deve animar (se houver uma frente selecionada, só ela anima)
            let deveAnimarPeca = true;
            if (ehFrenteEspecificaSel) {
                if (cat.includes("porta")) {
                    deveAnimarPeca = (p.nome_comercial === nomePecaSel);
                } else if (cat.includes("gaveta") || cat.includes("sapateira")) {
                    deveAnimarPeca = numGavSel
                        ? p.nome_comercial.endsWith(` ${numGavSel}`)
                        : (p.nome_comercial === nomePecaSel);
                } else if (cat.includes("tempero")) {
                    deveAnimarPeca = catPecaSel.includes("tempero");
                }
            }

            const pPortas = deveAnimarPeca ? pctPortas : 0.0;
            const pGavetas = deveAnimarPeca ? pctGavetas : 0.0;

            // 1. Movimento exclusivo de Gavetas, Sapateiras e Porta-Tempero
            if (cat.includes("gaveta") || cat.includes("tempero") || cat.includes("sapateira")) {
                if (!cat.includes("engrosso")) {
                    container.position.set(baseX, baseY, baseZ + (pGavetas * 340.0));
                } else {
                    container.position.set(baseX, baseY, baseZ);
                }
            }
            // 2. Movimento exclusivo de Porta Basculante
            else if (cat.includes("porta_basculante")) {
                const meiaAlt = p.dimensoes.z / 2.0;
                const anguloBasc = pPortas * ((95.0 * Math.PI) / 180.0);
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
                const angulo = pPortas * ((92.0 * Math.PI) / 180.0) * (ehDireita ? 1.0 : -1.0);
                const xDobradica = ehDireita ? (baseX + meiaLarg) : (baseX - meiaLarg);
                const dxCentro = baseX - xDobradica;

                container.position.set(
                    xDobradica + dxCentro * Math.cos(angulo),
                    baseY,
                    baseZ - dxCentro * Math.sin(angulo)
                );
                container.rotation.y = angulo;
            }
            // 4. Movimento exclusivo de Portas de Correr (sempre deslizando para dentro do módulo)
            else if (cat.includes("porta_correr")) {
                const cursoX = p.dimensoes.x * 0.85;
                const sentidoCentro = (dir.x > 0.05) ? -1.0 : 1.0;
                const fatorTrilho = cat.includes("frente") ? 1.0 : 0.0;
                container.position.set(baseX + (pPortas * cursoX * sentidoCentro * fatorTrilho), baseY, baseZ);
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

    // Botão Direito na Planta 2D: encerra o desenho contínuo da parede e volta para o Ambiente 3D!
    container.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        if (modoCamera === "PLANTA_2D") {
            pontoInicialParede2D = null;
            ultimoVerticeSnapped2D = null;
            grupoPreviewParedeVerde.clear();
            const st = document.getElementById("status_desenho_2d");
            if (st) st.innerText = "✅ Desenho de paredes encerrado.";
            mudarModoCamera("AMBIENTE_3D");
        }
    });

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
        if (event.button !== 0 || modoCamera === "PLANTA_2D" || mostrarVaos || event.ctrlKey) return;

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

let elementosParedeCache = [];

const _carregarEstadoBase = carregarEstadoAmbiente;
carregarEstadoAmbiente = async function () {
    const resp = await fetch("/api/ambiente");
    const dados = await resp.json();
    elementosParedeCache = dados.elementos_parede || [];

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

// =============================================================================
// 11. ESQUADRIAS (JANELAS/PORTAS) E PONTOS HIDRÁULICOS/ELÉTRICOS NAS PAREDES
// =============================================================================
let grupoEsquadriasEPontos3D = new THREE.Group();

function ajustarPadraoEsquadriaUI() {
    const tipo = document.getElementById("sel_tipo_esquadria").value;
    if (tipo === "JANELA") {
        document.getElementById("inp_esq_z").value = 1100;
        document.getElementById("inp_esq_larg").value = 1200;
        document.getElementById("inp_esq_alt").value = 1000;
    } else if (tipo === "PORTA") {
        document.getElementById("inp_esq_z").value = 0;
        document.getElementById("inp_esq_larg").value = 800;
        document.getElementById("inp_esq_alt").value = 2100;
    } else if (tipo === "PONTO_AGUA") {
        document.getElementById("inp_esq_z").value = 550;
        document.getElementById("inp_esq_larg").value = 100;
        document.getElementById("inp_esq_alt").value = 100;
    } else if (tipo === "PONTO_GAS") {
        document.getElementById("inp_esq_z").value = 400;
        document.getElementById("inp_esq_larg").value = 100;
        document.getElementById("inp_esq_alt").value = 100;
    } else if (tipo === "PONTO_TOMADA") {
        document.getElementById("inp_esq_z").value = 1150;
        document.getElementById("inp_esq_larg").value = 100;
        document.getElementById("inp_esq_alt").value = 100;
    }
}

async function adicionarElementoParedeUI() {
    const payload = {
        id_parede: document.getElementById("sel_parede_esquadria").value,
        tipo: document.getElementById("sel_tipo_esquadria").value,
        distancia_x: parseFloat(document.getElementById("inp_esq_x").value) || 0,
        elevacao_z: parseFloat(document.getElementById("inp_esq_z").value) || 0,
        largura_x: parseFloat(document.getElementById("inp_esq_larg").value) || 800,
        altura_z: parseFloat(document.getElementById("inp_esq_alt").value) || 1000
    };

    const resp = await fetch("/api/ambiente/elemento_parede/adicionar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        await carregarEstadoAmbiente();
    }
}

async function removerElementoParedeUI(idElemento) {
    await fetch("/api/ambiente/elemento_parede/remover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_elemento: idElemento })
    });
    await carregarEstadoAmbiente();
}

function renderizarEsquadriasEPontos3D() {
    if (!scene.children.includes(grupoEsquadriasEPontos3D)) {
        scene.add(grupoEsquadriasEPontos3D);
    }
    grupoEsquadriasEPontos3D.clear();

    const selParEsq = document.getElementById("sel_parede_esquadria");
    const valorAnt = selParEsq ? selParEsq.value : "";
    if (selParEsq) selParEsq.innerHTML = "";

    const containerLista = document.getElementById("lista_elementos_parede_ui");
    if (containerLista) containerLista.innerHTML = "";

    (ambienteCache.paredes || []).forEach(par => {
        if (selParEsq) {
            const opt = document.createElement("option");
            opt.value = par.id_parede;
            opt.innerText = `Parede ${par.id_parede} (${par.comprimento}mm)`;
            selParEsq.appendChild(opt);
        }

        const grupoLocalPar = new THREE.Group();
        grupoLocalPar.position.set(par.x1, 0, par.y1);
        grupoLocalPar.rotation.y = -THREE.MathUtils.degToRad(par.angulo_graus || 0);

        const elsDaParede = (elementosParedeCache || []).filter(e => e.id_parede === par.id_parede);
        elsDaParede.forEach(el => {
            if (containerLista) {
                const itemDiv = document.createElement("div");
                itemDiv.className = "module-item";
                itemDiv.innerHTML = `
                    <span><b>[Par. ${par.id_parede}]</b> ${el.nome} <small style="color:#80D8FF;">(X:${el.distancia_x} Z:${el.elevacao_z})</small></span>
                    <button class="btn btn-danger" style="padding:2px 6px;" onclick="removerElementoParedeUI('${el.id_elemento}')">🗑️</button>
                `;
                containerLista.appendChild(itemDiv);
            }

            const larg = el.largura_x;
            const alt = el.altura_z;
            const cx = el.distancia_x + (larg / 2.0);
            const cy = el.elevacao_z + (alt / 2.0);
            const zFace = 14.0;

            if (el.tipo === "JANELA") {
                const espPerfil = 45.0;
                const profJan = 24.0;
                const matAlum = new THREE.MeshStandardMaterial({ color: 0xB0BEC5, metalness: 0.55, roughness: 0.35 });
                const matFundoEscuro = new THREE.MeshBasicMaterial({ color: 0x0B1622 });
                const matVidro = new THREE.MeshStandardMaterial({
                    color: 0x80D8FF, transparent: true, opacity: 0.32, roughness: 0.1, depthWrite: false
                });

                const fundoVao = new THREE.Mesh(new THREE.BoxGeometry(larg - 20, alt - 20, 6), matFundoEscuro);
                fundoVao.position.set(cx, cy, 4);
                const vidro = new THREE.Mesh(new THREE.BoxGeometry(larg - (espPerfil * 2), alt - (espPerfil * 2), 8), matVidro);
                vidro.position.set(cx, cy, zFace);

                const pSup = new THREE.Mesh(new THREE.BoxGeometry(larg, espPerfil, profJan), matAlum);
                pSup.position.set(cx, el.elevacao_z + alt - (espPerfil / 2), zFace);
                const pInf = new THREE.Mesh(new THREE.BoxGeometry(larg + 40, espPerfil, profJan + 18), matAlum);
                pInf.position.set(cx, el.elevacao_z + (espPerfil / 2), zFace + 6);
                const pEsq = new THREE.Mesh(new THREE.BoxGeometry(espPerfil, alt - (espPerfil * 2), profJan), matAlum);
                pEsq.position.set(el.distancia_x + (espPerfil / 2), cy, zFace);
                const pDir = new THREE.Mesh(new THREE.BoxGeometry(espPerfil, alt - (espPerfil * 2), profJan), matAlum);
                pDir.position.set(el.distancia_x + larg - (espPerfil / 2), cy, zFace);
                const pMeio = new THREE.Mesh(new THREE.BoxGeometry(28, alt - (espPerfil * 2), profJan + 4), matAlum);
                pMeio.position.set(cx, cy, zFace + 2);

                const spJan = criarSpriteTextoCAD(`🪟 ${larg}x${alt} (Z:${el.elevacao_z})`, "#0277BD", "rgba(255,255,255,0.92)", 200);
                spJan.position.set(cx, el.elevacao_z + alt + 55, zFace + 15);
                grupoLocalPar.add(fundoVao, vidro, pSup, pInf, pEsq, pDir, pMeio, spJan);
            } else if (el.tipo === "PORTA") {
                const largG = 60.0;
                const matG = new THREE.MeshStandardMaterial({ color: 0x4E342E, roughness: 0.55 });
                const matF = new THREE.MeshStandardMaterial({ color: 0x795548, roughness: 0.5 });
                const matInox = new THREE.MeshStandardMaterial({ color: 0xECEFF1, metalness: 0.85, roughness: 0.2 });

                const folha = new THREE.Mesh(new THREE.BoxGeometry(larg, alt, 18), matF);
                folha.position.set(cx, cy, zFace);
                const gEsq = new THREE.Mesh(new THREE.BoxGeometry(largG, alt + largG, 26), matG);
                gEsq.position.set(el.distancia_x - (largG / 2), (alt + largG) / 2, zFace + 2);
                const gDir = new THREE.Mesh(new THREE.BoxGeometry(largG, alt + largG, 26), matG);
                gDir.position.set(el.distancia_x + larg + (largG / 2), (alt + largG) / 2, zFace + 2);
                const gSup = new THREE.Mesh(new THREE.BoxGeometry(larg + (largG * 2), largG, 26), matG);
                gSup.position.set(cx, alt + (largG / 2), zFace + 2);
                const mac = new THREE.Mesh(new THREE.BoxGeometry(110, 22, 35), matInox);
                mac.position.set(el.distancia_x + larg - 90, Math.min(1050, alt * 0.5), zFace + 22);

                grupoLocalPar.add(folha, gEsq, gDir, gSup, mac);
            } else {
                let corP = 0x00B0FF, sigla = "🚰 ÁGUA";
                if (el.tipo === "PONTO_GAS") { corP = 0xFFB300; sigla = "🔥 GÁS"; }
                else if (el.tipo === "PONTO_TOMADA") { corP = 0xFF1744; sigla = "⚡ TOMADA"; }

                const matP = new THREE.MeshStandardMaterial({ color: corP, roughness: 0.3 });
                let pecaP;
                if (el.tipo === "PONTO_TOMADA") {
                    pecaP = new THREE.Mesh(new THREE.BoxGeometry(80, 110, 14), matP);
                } else {
                    pecaP = new THREE.Mesh(new THREE.CylinderGeometry(35, 35, 18, 24), matP);
                    pecaP.rotation.x = Math.PI / 2;
                }
                pecaP.position.set(cx, cy, zFace);

                const spPt = criarSpriteTextoCAD(`${sigla} X:${el.distancia_x} Z:${el.elevacao_z}`, "#111111", "rgba(255,255,255,0.92)", 175);
                spPt.position.set(cx, cy + 75, zFace + 12);
                grupoLocalPar.add(pecaP, spPt);
            }
        });

        grupoEsquadriasEPontos3D.add(grupoLocalPar);
    });

    if (selParEsq && valorAnt) selParEsq.value = valorAnt;
    verificarInterferenciasObraUI();
}

async function verificarInterferenciasObraUI() {
    const resp = await fetch("/api/ambiente/verificar_interferencias");
    const dados = await resp.json();
    const box = document.getElementById("box_alertas_obra");
    if (!box) return;

    if (dados.alertas && dados.alertas.length > 0) {
        box.innerHTML = dados.alertas.join("<br>");
        document.getElementById("txt_resposta_copiloto").innerText = dados.alertas[0];
    } else {
        box.innerHTML = "<span style='color:#4CE660;'>✅ Zero colisões entre módulos e esquadrias/pontos!</span>";
    }
}

const _renderAntesEsquadrias = renderizarCenaCompleta;
renderizarCenaCompleta = function () {
    _renderAntesEsquadrias();
    renderizarEsquadriasEPontos3D();
};

// =============================================================================
// 12. BIBLIOTECA DE FAVORITOS, EDIÇÃO PARAMÉTRICA DE VÃO E SMART FILL DE PAREDE
// =============================================================================
async function abrirJanelaFavoritos() {
    alternarJanelaHUD("hud_favoritos", "btn_hud_favoritos");
    const painel = document.getElementById("hud_favoritos");
    if (!painel.classList.contains("oculto")) {
        if (moduloAtivo) {
            document.getElementById("inp_nome_favorito").value =
                `${moduloAtivo.familia.replace("MODULO_", "")} ${moduloAtivo.dimensoes_ocupadas.largura_x}mm (#${moduloAtivo.id_modulo})`;
        }
        await carregarListaFavoritosUI();
    }
}

async function carregarListaFavoritosUI() {
    const resp = await fetch("/api/favoritos/listar");
    const dados = await resp.json();
    const container = document.getElementById("lista_favoritos_ui");
    if (!container) return;
    container.innerHTML = "";

    if (!dados.favoritos || dados.favoritos.length === 0) {
        container.innerHTML = `<div style="padding:10px; color:#90A4AE; text-align:center;">Nenhum módulo salvo nos favoritos ainda.</div>`;
        return;
    }

    dados.favoritos.forEach(fav => {
        const div = document.createElement("div");
        div.className = "module-item";
        div.innerHTML = `
            <div style="flex:1;" onclick="inserirFavoritoNoAmbiente('${fav.arquivo}')">
                <strong style="color:#FFD600;">⭐ ${fav.nome_favorito}</strong><br>
                <small style="color:#80D8FF;">📐 ${fav.largura_x}x${fav.altura_y}x${fav.profundidade_z}mm | 🪵 ${fav.qtd_pecas} pçs</small>
            </div>
            <button class="btn btn-primary" style="padding:4px 8px;" onclick="inserirFavoritoNoAmbiente('${fav.arquivo}')">➕ Inserir</button>
            <button class="btn btn-danger" style="padding:4px 6px;" onclick="excluirFavoritoUI('${fav.arquivo}', event)">🗑️</button>
        `;
        container.appendChild(div);
    });
}

async function salvarModuloAtivoNosFavoritos() {
    if (!moduloAtivo) {
        alert("Selecione um módulo no ambiente para salvar nos favoritos!");
        return;
    }
    const nome = document.getElementById("inp_nome_favorito").value.trim();
    if (!nome) {
        alert("Digite um nome para identificar este módulo na biblioteca!");
        return;
    }

    const resp = await fetch("/api/favoritos/salvar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_modulo: moduloAtivo.id_modulo, nome_favorito: nome })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        await carregarListaFavoritosUI();
    }
}

async function inserirFavoritoNoAmbiente(nomeArquivo) {
    const largCustom = parseFloat(document.getElementById("inp_larg_custom_fav").value) || 0;
    const idPar = document.getElementById("sel_parede_modulo").value || null;

    const resp = await fetch("/api/favoritos/inserir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            arquivo: nomeArquivo,
            largura_custom_mm: largCustom > 100 ? largCustom : null,
            id_parede: idPar
        })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        idsSelecionados.clear();
        idsSelecionados.add(moduloAtivo.id_modulo);
        await carregarEstadoAmbiente();
    } else {
        alert(dados.erro_engenharia || "Erro ao inserir favorito.");
    }
}

async function excluirFavoritoUI(nomeArquivo, event) {
    event.stopPropagation();
    await fetch("/api/favoritos/excluir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arquivo: nomeArquivo })
    });
    await carregarListaFavoritosUI();
}

// Preenche automaticamente os inputs de Largura Livre (X) e Altura Livre (Z) ao clicar num vão 3D
const _abrirPainelVaoOrig = abrirPainelVao;
abrirPainelVao = function (no) {
    _abrirPainelVaoOrig(no);
    const g = no.geometria_3d;
    const inpL = document.getElementById("inp_vao_larg_interna");
    const inpA = document.getElementById("inp_vao_alt_interna");
    const lblDica = document.getElementById("lbl_dica_edicao_vao");

    const opGavExistente = (moduloAtivo?.operacoes_internas || []).find(
        o => o.id_vao === no.id_vao && ["GAVETEIRO", "GAVETEIRO_INTERNO"].includes(o.tipo)
    );
    if (opGavExistente && opGavExistente.quantidade) {
        const inpQ = document.getElementById("inp_vao_qtd_itens");
        if (inpQ) inpQ.value = opGavExistente.quantidade;
    }
    renderizarInputsAlturasGavetas(opGavExistente ? opGavExistente.alturas_gavetas : []);

    if (inpL) inpL.value = g.largura;
    if (inpA) inpA.value = g.altura;

    if (lblDica) {
        if (no.id_vao === "raiz") {
            lblDica.innerText = "💡 Vão Raiz: Alterar aqui ajusta a Largura/Altura total do módulo.";
        } else {
            lblDica.innerText = "💡 Sub-Vão: Alterar aqui move a Divisória/Prateleira automaticamente!";
        }
    }
};

// Localiza um nó na árvore recursiva de vãos pelo seu id_vao
function buscarNoEspacialPorId(noAtual, idAlvo) {
    if (!noAtual) return null;
    if (noAtual.id_vao === idAlvo) return noAtual;
    for (const f of (noAtual.filhos || [])) {
        const achado = buscarNoEspacialPorId(f, idAlvo);
        if (achado) return achado;
    }
    return null;
}

// Aplica a nova Largura Livre (X) e/ou Altura Livre (Z) digitada diretamente para o vão selecionado!
async function redimensionarMedidaInternaDoVao() {
    if (!moduloAtivo || !vaoSelecionadoId) return;

    const noAlvo = buscarNoEspacialPorId(moduloAtivo.arvore_espacial_vaos, vaoSelecionadoId);
    if (!noAlvo) return;

    const novaLarg = parseFloat(document.getElementById("inp_vao_larg_interna").value);
    const novaAlt = parseFloat(document.getElementById("inp_vao_alt_interna").value);
    const largAtual = noAlvo.geometria_3d.largura;
    const altAtual = noAlvo.geometria_3d.altura;

    const espCaixa = parseFloat(document.getElementById("sel_esp_caixa").value) || 15.0;
    let largMod = moduloAtivo.dimensoes_ocupadas.largura_x;
    let altMod = moduloAtivo.dimensoes_ocupadas.altura_y;

    let ops = moduloAtivo.operacoes_internas ? JSON.parse(JSON.stringify(moduloAtivo.operacoes_internas)) : [];

    // CASO 1: Usuário editou a medida interna do Vão Principal ("raiz") -> Ajusta o módulo externo!
    if (vaoSelecionadoId === "raiz") {
        if (!isNaN(novaLarg) && Math.abs(novaLarg - largAtual) > 0.5) {
            largMod = Math.round((largMod + (novaLarg - largAtual)) * 10) / 10;
            document.getElementById("inp_largura").value = largMod;
        }
        if (!isNaN(novaAlt) && Math.abs(novaAlt - altAtual) > 0.5) {
            altMod = Math.round((altMod + (novaAlt - altAtual)) * 10) / 10;
            document.getElementById("inp_altura").value = altMod;
        }
    } else {
        // CASO 2: É um Sub-Vão (IDs do NoEspacial: "raiz.0", "raiz.1", "raiz.0.1", etc.) -> Move a Divisória no Pai!
        
        // A) Mudou a Largura Livre (X) do sub-vão? Sobe na árvore procurando a DIVISORIA_VERTICAL que gerou este ramo
        if (!isNaN(novaLarg) && Math.abs(novaLarg - largAtual) > 0.5) {
            let idCursor = vaoSelecionadoId;
            while (idCursor.includes(".")) {
                const ultimoPonto = idCursor.lastIndexOf(".");
                const idPai = idCursor.substring(0, ultimoPonto);
                const sufixoFilho = idCursor.substring(ultimoPonto + 1); // "0" = Esquerdo, "1" = Direito
                const opDiv = ops.find(o => o.id_vao === idPai && o.tipo === "DIVISORIA_VERTICAL");
                const noPai = buscarNoEspacialPorId(moduloAtivo.arvore_espacial_vaos, idPai);

                if (opDiv && noPai) {
                    const ehVaoEsquerdo = (sufixoFilho === "0");
                    // Chave oficial lida na linha 166 do orquestrador_modulo.py: 'posicao_x'
                    opDiv.posicao_x = ehVaoEsquerdo
                        ? Math.round(novaLarg * 10) / 10
                        : Math.round((noPai.geometria_3d.largura - espCaixa - novaLarg) * 10) / 10;
                    break;
                }
                idCursor = idPai;
            }
        }

        // B) Mudou a Altura Livre (Z) do sub-vão? Sobe na árvore procurando a DIVISORIA_HORIZONTAL que gerou este ramo
        if (!isNaN(novaAlt) && Math.abs(novaAlt - altAtual) > 0.5) {
            let idCursor = vaoSelecionadoId;
            while (idCursor.includes(".")) {
                const ultimoPonto = idCursor.lastIndexOf(".");
                const idPai = idCursor.substring(0, ultimoPonto);
                const sufixoFilho = idCursor.substring(ultimoPonto + 1); // "0" = Inferior, "1" = Superior
                const opDiv = ops.find(o => o.id_vao === idPai && o.tipo === "DIVISORIA_HORIZONTAL");
                const noPai = buscarNoEspacialPorId(moduloAtivo.arvore_espacial_vaos, idPai);

                if (opDiv && noPai) {
                    const ehVaoInferior = (sufixoFilho === "0");
                    // Chave oficial lida na linha 172 do orquestrador_modulo.py: 'posicao_z'
                    opDiv.posicao_z = ehVaoInferior
                        ? Math.round(novaAlt * 10) / 10
                        : Math.round((noPai.geometria_3d.altura - espCaixa - novaAlt) * 10) / 10;
                    break;
                }
                idCursor = idPai;
            }
        }
    }

    document.getElementById("inp_prompt").value = "";
    const overrides = coletarOverridesPerfilUI();

    const resp = await fetch("/api/fabricar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: moduloAtivo.id_modulo,
            familia: moduloAtivo.familia,
            largura_x: largMod,
            altura_y: altMod,
            profundidade_z: moduloAtivo.dimensoes_ocupadas.profundidade_z,
            material_caixaria: document.getElementById("sel_mat_caixa").value,
            material_frentes: document.getElementById("sel_mat_frentes").value,
            overrides_perfil: overrides,
            operacoes_internas: ops
        })
    });
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || dados.erro_interno);
        return;
    }

    moduloAtivo = dados.modulo;
    await carregarEstadoAmbiente();

    // Atualiza os números na janela do vão imediatamente
    const noAtualizado = buscarNoEspacialPorId(moduloAtivo.arvore_espacial_vaos, vaoSelecionadoId);
    if (noAtualizado) abrirPainelVao(noAtualizado);
}

function renderizarInputsAlturasGavetas(alturasSalvas = []) {
    const container = document.getElementById("container_alturas_gavetas");
    const inpQtd = document.getElementById("inp_vao_qtd_itens");
    if (!container || !inpQtd) return;

    const qtd = Math.max(1, Math.min(8, parseInt(inpQtd.value) || 3));
    container.innerHTML = "";
    for (let i = 0; i < qtd; i++) {
        const val = (alturasSalvas && alturasSalvas[i]) ? alturasSalvas[i] : 0;
        const wrap = document.createElement("div");
        wrap.innerHTML = `
            <label style="font-size:9px; color:#90A4AE;">G${i + 1}${i === 0 ? ' (Base)' : ''}</label>
            <input type="number" class="inp-alt-gav-item" value="${val}" min="0" step="10" placeholder="Auto" style="padding:3px 4px; font-size:10px;">
        `;
        container.appendChild(wrap);
    }
}

function coletarAlturasGavetasUI() {
    const inputs = document.querySelectorAll("#container_alturas_gavetas .inp-alt-gav-item");
    const lista = Array.from(inputs).map(el => parseFloat(el.value) || 0);
    return lista.some(v => v > 0) ? lista : null;
}

// Subdivisão e inserção usando as chaves oficiais do orquestrador_modulo.py ('posicao_x' e 'posicao_z')!
async function aplicarOperacaoVaoParametrica(tipoOp, extras = {}) {
    const cotaDiv = parseFloat(document.getElementById("inp_vao_cota_div").value) || 0;
    const qtdItens = parseInt(document.getElementById("inp_vao_qtd_itens").value) || 2;

    const paramsExtras = { ...extras };
    if (tipoOp === "DIVISORIA_VERTICAL" && cotaDiv >= 50) {
        paramsExtras.posicao_x = cotaDiv; // Chave exata da linha 166 do orquestrador_modulo.py!
    } else if (tipoOp === "DIVISORIA_HORIZONTAL" && cotaDiv >= 50) {
        paramsExtras.posicao_z = cotaDiv; // Chave exata da linha 172 do orquestrador_modulo.py!
    }

    if (tipoOp === "PORTAS_CORRER") {
      const elTrilho = document.getElementById("sel_vao_trilho_correr");
      if (elTrilho) paramsExtras.disposicao_trilhos = elTrilho.value;
    }

    if (["GAVETEIRO", "GAVETEIRO_INTERNO"].includes(tipoOp)) {
        const alts = coletarAlturasGavetasUI();
        if (alts) paramsExtras.alturas_gavetas = alts;
    }
    
    if (["GAVETEIRO", "GAVETEIRO_INTERNO", "SAPATEIRA", "PRATELEIRAS", "PORTAS_BASCULANTES", "PORTAS_CORRER"].includes(tipoOp)) {
     paramsExtras.quantidade = qtdItens;
    }

    await aplicarOperacaoNoVao(tipoOp, paramsExtras);
}

// Limpa os componentes internos do vão clicado (ou desfaz a divisão do pai se o sub-vão já estiver vazio!)
async function limparOperacoesDoVaoSelecionado() {
    if (!moduloAtivo || !vaoSelecionadoId) return;
    let ops = moduloAtivo.operacoes_internas ? [...moduloAtivo.operacoes_internas] : [];

    const tinhaNoVao = ops.some(op => op.id_vao === vaoSelecionadoId);
    if (tinhaNoVao) {
        ops = ops.filter(op => op.id_vao !== vaoSelecionadoId);
    } else if (vaoSelecionadoId.includes(".")) {
        const idPai = vaoSelecionadoId.substring(0, vaoSelecionadoId.lastIndexOf("."));
        ops = ops.filter(op => !op.id_vao.startsWith(idPai));
        vaoSelecionadoId = idPai;
    } else if (ops.length > 0) {
        ops.pop();
    }

    document.getElementById("inp_prompt").value = "";
    const overrides = coletarOverridesPerfilUI();

    const resp = await fetch("/api/fabricar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: moduloAtivo.id_modulo,
            familia: moduloAtivo.familia,
            largura_x: moduloAtivo.dimensoes_ocupadas.largura_x,
            altura_y: moduloAtivo.dimensoes_ocupadas.altura_y,
            profundidade_z: moduloAtivo.dimensoes_ocupadas.profundidade_z,
            material_caixaria: document.getElementById("sel_mat_caixa").value,
            material_frentes: document.getElementById("sel_mat_frentes").value,
            overrides_perfil: overrides,
            operacoes_internas: ops
        })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        fecharPainelVao();
        await carregarEstadoAmbiente();
    }
}

async function preencherSobraParedeComModulo() {
    if (!moduloAtivo || !moduloAtivo.posicionamento_ambiente) return;
    const sobra = Math.round(moduloAtivo.posicionamento_ambiente.sobra_parede_mm || 0);
    if (sobra < 150) {
        alert(`Espaço restante na parede (${sobra}mm) é menor que 150mm!`);
        return;
    }
    document.getElementById("inp_largura").value = Math.min(sobra, 2710);
    criarNovoSlotModulo();
}

// =============================================================================
// 13. SELETOR E EDITOR DATA-DRIVEN DE PERFIS MULTI-MARCENARIA
// =============================================================================
let perfilEmEdicaoJSON = null;
let abaAtualEditorPerfil = "geometria_caixaria";

async function carregarListaPerfisUI() {
    const resp = await fetch("/api/perfis/listar");
    const dados = await resp.json();
    if (!dados.sucesso) return;

    const sel = document.getElementById("sel_perfil_ativo_topo");
    if (!sel) return;
    sel.innerHTML = "";

    (dados.perfis || []).forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id_perfil;
        opt.innerText = `🏭 ${p.nome_exibicao}`;
        if (p.id_perfil === dados.perfil_ativo) opt.selected = true;
        sel.appendChild(opt);
    });
}

function sincronizarInputsEngenhariaComPerfil(perfil) {
    if (!perfil) return;
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined && val !== null) el.value = val;
    };

    setVal("sel_sistema_fixacao", perfil.tipo_montagem_caixa);
    if (perfil.materiais_padrao) {
        setVal("sel_esp_caixa", Number(perfil.materiais_padrao.espessura_estrutural_mm).toFixed(1));
        setVal("sel_esp_frente", Number(perfil.materiais_padrao.espessura_frente_mm).toFixed(1));
    }
    if (perfil.geometria_caixaria) {
        const gc = perfil.geometria_caixaria;
        setVal("sel_modo_base", gc.montagem_base_inferior);
        setVal("sel_modo_fundo", gc.tipo_montagem_fundo);
        setVal("sel_fixacao_aereo", gc.sistema_fixacao_aereo);
        setVal("sel_reforco_torre", gc.reforco_traseiro_torre);
        setVal("inp_larg_sarrafo", gc.largura_sarrafo);
        setVal("inp_recuo_prat", gc.recuo_frontal_prateleira);
        setVal("inp_recuo_fundo", gc.recuo_canal_fundo);
        if (gc.montagem_teto_balcao === "TAMPO_INTEIRO") {
            setVal("sel_topo_balcao", "TAMPO_INTEIRO");
        } else {
            setVal("sel_topo_balcao", gc.posicao_sarrafo_traseiro_balcao || "DEITADO");
        }
    }
    if (perfil.folgas_frentes) {
        const ff = perfil.folgas_frentes;
        setVal("sel_modo_frente", ff.tipo_montagem_frente);
        setVal("inp_gap_esq", ff.gap_lateral_esquerda);
        setVal("inp_gap_dir", ff.gap_lateral_direita);
        setVal("inp_gap_vert", ff.gap_superior);
        setVal("inp_gap_entre", ff.gap_entre_frentes);
    }
    if (perfil.regras_gaveta) {
        setVal("inp_folga_corredica", perfil.regras_gaveta.folga_corredica_cada_lado);
    }
    if (perfil.parametros_usinagem) {
        const pu = perfil.parametros_usinagem;
        setVal("inp_larg_canal", pu.largura_canal_fundo);
        setVal("inp_prof_canal", pu.profundidade_canal_fundo);
        setVal("inp_broca_estrut", pu.broca_parafuso_estrutural);
        setVal("inp_cota_caneco", pu.distancia_centro_caneco_borda);
    }
}

async function trocarPerfilAtivoUI(idPerfil) {
    const resp = await fetch("/api/perfis/ativar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_perfil: idPerfil })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        sincronizarInputsEngenhariaComPerfil(dados.perfil);
        document.getElementById("txt_resposta_copiloto").innerText =
            `🏭 Perfil ativo alterado para: ${dados.perfil.nome_exibicao}`;
    }
}

async function abrirEditorPerfisUI() {
    const sel = document.getElementById("sel_perfil_ativo_topo");
    const idAtivo = sel ? sel.value : "padrao_convencional_15mm";
    const resp = await fetch(`/api/perfis/obter/${idAtivo}`);
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || "Erro ao carregar perfil.");
        return;
    }

    perfilEmEdicaoJSON = dados.perfil;
    document.getElementById("inp_perf_nome_exibicao").value = perfilEmEdicaoJSON.nome_exibicao || "";
    document.getElementById("inp_perf_id_arquivo").value = perfilEmEdicaoJSON.id_perfil || "";

    renderizarCamposAbaEditorPerfil(abaAtualEditorPerfil);
    document.getElementById("modal_editor_perfis").style.display = "block";
}

function fecharEditorPerfisUI() {
    document.getElementById("modal_editor_perfis").style.display = "none";
}

function selecionarAbaEditorPerfil(nomeSecao, btnEl) {
    abaAtualEditorPerfil = nomeSecao;
    document.querySelectorAll("#abas_editor_perfil .btn").forEach(b => b.classList.remove("ativo"));
    if (btnEl) btnEl.classList.add("ativo");
    renderizarCamposAbaEditorPerfil(nomeSecao);
}

function formatarRotuloChaveJSON(chave) {
    return chave.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

function renderizarCamposAbaEditorPerfil(secao) {
    const grid = document.getElementById("grid_campos_editor_perfil");
    if (!grid || !perfilEmEdicaoJSON) return;
    grid.innerHTML = "";

    const bloco = perfilEmEdicaoJSON[secao];
    if (!bloco || typeof bloco !== "object") {
        grid.innerHTML = `<div style="color:#90A4AE;">Seção '${secao}' não encontrada neste perfil.</div>`;
        return;
    }

    Object.entries(bloco).forEach(([chave, valor]) => {
        const div = document.createElement("div");
        const label = document.createElement("label");
        label.innerText = formatarRotuloChaveJSON(chave);
        div.appendChild(label);

        const inp = document.createElement("input");
        if (typeof valor === "number") {
            inp.type = "number";
            inp.step = "any";
            inp.value = valor;
            inp.oninput = () => {
                const n = parseFloat(inp.value);
                if (!isNaN(n)) perfilEmEdicaoJSON[secao][chave] = n;
            };
        } else if (Array.isArray(valor)) {
            inp.type = "text";
            inp.value = valor.join(", ");
            inp.title = "Valores separados por vírgula";
            inp.onchange = () => {
                const itens = inp.value.split(",").map(v => v.trim()).filter(Boolean);
                const ehNum = itens.every(v => !isNaN(parseFloat(v)));
                perfilEmEdicaoJSON[secao][chave] = ehNum ? itens.map(Number) : itens;
            };
        } else {
            inp.type = "text";
            inp.value = String(valor);
            inp.oninput = () => {
                perfilEmEdicaoJSON[secao][chave] = inp.value;
            };
        }

        div.appendChild(inp);
        grid.appendChild(div);
    });
}

async function salvarPerfilEditadoUI(comoNovo) {
    if (!perfilEmEdicaoJSON) return;

    let nomeExib = document.getElementById("inp_perf_nome_exibicao").value.trim();
    let idArq = document.getElementById("inp_perf_id_arquivo").value.trim();

    if (comoNovo) {
        const novoNome = prompt("Digite o Nome da Nova Marcenaria / Perfil:", `${nomeExib} (Cópia)`);
        if (!novoNome) return;
        nomeExib = novoNome.trim();
        idArq = nomeExib.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "_");
    }

    const resp = await fetch("/api/perfis/salvar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_perfil: idArq,
            nome_exibicao: nomeExib,
            dados_perfil: perfilEmEdicaoJSON
        })
    });
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || "Erro ao salvar perfil.");
        return;
    }

    await carregarListaPerfisUI();
    sincronizarInputsEngenhariaComPerfil(perfilEmEdicaoJSON);
    fecharEditorPerfisUI();
    document.getElementById("txt_resposta_copiloto").innerText =
        `🏭 Perfil '${dados.nome_exibicao}' salvo e ativado!`;
}

// Carrega os perfis automaticamente ao iniciar o estúdio
window.addEventListener("load", () => {
    carregarListaPerfisUI();
});

// =============================================================================
// 14. COPIAR / COLAR (CTRL+C / CTRL+V) E ARRANJO EM SÉRIE COM ID ÚNICO
// =============================================================================
let idModuloCopiadoClipboard = null;

async function clonarModuloServidor(idOrigem, quantidade = 1, direcao = "AUTO_SNAP", espacamento = 0) {
    const resp = await fetch("/api/modulo/clonar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo_origem: idOrigem,
            quantidade: quantidade,
            direcao: direcao,
            espacamento_mm: espacamento
        })
    });
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || dados.erro_interno || "Erro ao clonar módulo.");
        return;
    }

    if (dados.modulo) {
        moduloAtivo = dados.modulo;
        idsSelecionados.clear();
        (dados.ids_criados || []).forEach(id => idsSelecionados.add(id));
    }
    await carregarEstadoAmbiente();
    document.getElementById("txt_resposta_copiloto").innerText =
        `📑 ${dados.ids_criados.length} cópia(s) criada(s): #${dados.ids_criados.join(", #")}`;
}

function abrirModalArranjoUI() {
    if (!moduloAtivo) {
        alert("Selecione um módulo no ambiente para fazer cópias em série!");
        return;
    }
    document.getElementById("lbl_mod_arranjo").innerText = `#${moduloAtivo.id_modulo}`;
    document.getElementById("modal_arranjo_copias").style.display = "block";
}

function fecharModalArranjoUI() {
    document.getElementById("modal_arranjo_copias").style.display = "none";
}

async function executarArranjoUI() {
    if (!moduloAtivo) return;
    const qtd = parseInt(document.getElementById("inp_arranjo_qtd").value) || 1;
    const espaco = parseFloat(document.getElementById("inp_arranjo_espaco").value) || 0;
    const dir = document.getElementById("sel_arranjo_direcao").value;

    await clonarModuloServidor(moduloAtivo.id_modulo, qtd, dir, espaco);
    fecharModalArranjoUI();
}

window.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c") {
        if (!moduloAtivo) return;
        e.preventDefault();
        idModuloCopiadoClipboard = moduloAtivo.id_modulo;
        document.getElementById("txt_resposta_copiloto").innerText =
            `📋 Módulo #${idModuloCopiadoClipboard} copiado! Pressione Ctrl+V para colar com novo ID.`;
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v") {
        if (!idModuloCopiadoClipboard) return;
        e.preventDefault();
        clonarModuloServidor(idModuloCopiadoClipboard, 1, "AUTO_SNAP", 0);
    }
});

// =============================================================================
// 15. SELEÇÃO POR CAIXA (CTRL + ARRASTAR) E INDICADOR DE LOTE EM MATERIAIS
// =============================================================================
const _atualizarContadorOrig = atualizarContadorSelecaoUI;
atualizarContadorSelecaoUI = function () {
    _atualizarContadorOrig();
    const lblMat = document.getElementById("lbl_mod_mat");
    if (lblMat) {
        const qtd = idsSelecionados.size;
        lblMat.innerText = qtd > 1 ? `${qtd} Módulos (Lote)` : (moduloAtivo ? `#${moduloAtivo.id_modulo}` : "Nenhum");
    }
};

window.addEventListener("load", () => {
    const container = document.getElementById("canvas-container");
    if (!container) return;

    // Cria o retângulo visual de seleção (Marquee)
    const caixaEl = document.createElement("div");
    caixaEl.id = "caixa_selecao_marquee";
    caixaEl.style.cssText = `
        position: fixed;
        display: none;
        border: 1.5px dashed #00E5FF;
        background: rgba(0, 229, 255, 0.14);
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(caixaEl);

    let marqueeAtivo = null;

    container.addEventListener("pointerdown", (e) => {
        if (e.button !== 0 || !e.ctrlKey || modoCamera === "PLANTA_2D") return;
        e.stopImmediatePropagation();
        marqueeAtivo = { xIni: e.clientX, yIni: e.clientY, xFim: e.clientX, yFim: e.clientY };
        caixaEl.style.left = `${e.clientX}px`;
        caixaEl.style.top = `${e.clientY}px`;
        caixaEl.style.width = "0px";
        caixaEl.style.height = "0px";
        caixaEl.style.display = "block";
    }, true);

    window.addEventListener("pointermove", (e) => {
        if (!marqueeAtivo) return;
        marqueeAtivo.xFim = e.clientX;
        marqueeAtivo.yFim = e.clientY;

        const left = Math.min(marqueeAtivo.xIni, marqueeAtivo.xFim);
        const top = Math.min(marqueeAtivo.yIni, marqueeAtivo.yFim);
        const width = Math.abs(marqueeAtivo.xFim - marqueeAtivo.xIni);
        const height = Math.abs(marqueeAtivo.yFim - marqueeAtivo.yIni);

        caixaEl.style.left = `${left}px`;
        caixaEl.style.top = `${top}px`;
        caixaEl.style.width = `${width}px`;
        caixaEl.style.height = `${height}px`;
    });

    window.addEventListener("pointerup", (e) => {
        if (!marqueeAtivo) return;
        const left = Math.min(marqueeAtivo.xIni, marqueeAtivo.xFim);
        const right = Math.max(marqueeAtivo.xIni, marqueeAtivo.xFim);
        const top = Math.min(marqueeAtivo.yIni, marqueeAtivo.yFim);
        const bottom = Math.max(marqueeAtivo.yIni, marqueeAtivo.yFim);

        caixaEl.style.display = "none";
        marqueeAtivo = null;

        // Ignora cliques curtos sem arrastar
        if ((right - left) < 8 && (bottom - top) < 8) return;

        const rectCanvas = renderer.domElement.getBoundingClientRect();
        if (!e.shiftKey) idsSelecionados.clear();

        const box3 = new THREE.Box3();
        const centro3D = new THREE.Vector3();

        grupoAmbienteModulos.children.forEach(grupoMod => {
            const idMod = grupoMod.userData ? grupoMod.userData.idModulo : null;
            if (!idMod || idsModulosOcultos.has(idMod)) return;

            box3.setFromObject(grupoMod);
            box3.getCenter(centro3D);
            centro3D.project(camera);

            const sx = ((centro3D.x + 1) / 2) * rectCanvas.width + rectCanvas.left;
            const sy = ((-centro3D.y + 1) / 2) * rectCanvas.height + rectCanvas.top;

            if (sx >= left && sx <= right && sy >= top && sy <= bottom) {
                idsSelecionados.add(idMod);
            }
        });

        if (idsSelecionados.size > 0) {
            const primeiroId = Array.from(idsSelecionados)[0];
            moduloAtivo = modulosCache.find(m => m.id_modulo === primeiroId) || moduloAtivo;
            document.getElementById("txt_resposta_copiloto").innerText =
                `🔲 ${idsSelecionados.size} módulo(s) selecionado(s) por caixa!`;
        } else {
            moduloAtivo = null;
        }

        atualizarContadorSelecaoUI();
        atualizarListaModulosDOM();
        renderizarCenaCompleta();
    });
});