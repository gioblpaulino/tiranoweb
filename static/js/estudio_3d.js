/* =============================================================================
 * ARQUIVO: static/js/estudio_3d.js
 * RESPONSABILIDADE: Controlar o palco Three.js (Ambiente 3D, Módulo Isolado e
 * Planta Baixa 2D), cinemática de portas/gavetas, multi-seleção e chamadas API.
 * ============================================================================= */

let scene, camera, renderer, controls;
let grupoAmbienteModulos = new THREE.Group();
let grupoParedes3D = new THREE.Group();
let grupoVaos3D = new THREE.Group();

let modoCamera = "AMBIENTE_3D";
let mostrarVaos = false;
let mostrarUsinagens = true;
let mostrarFitas = true;
let modoRaioX = false;

let ambienteCache = { paredes: [] };
let modulosCache = [];
let moduloAtivo = null;
let idsSelecionados = new Set();
let vaoSelecionadoId = null;

let pontoInicialParede2D = null;
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const planoPiso = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

// =============================================================================
// 1. INICIALIZAÇÃO DO PALCO 3D E SMART WALL CULLING
// =============================================================================
function inicializarPalco3D() {
    const container = document.getElementById("canvas-container");
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07090C);

    camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 1, 35000);
    camera.position.set(2200, 2100, 3800);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.target.set(1600, 600, 800);
    controls.update();

    scene.add(new THREE.AmbientLight(0xffffff, 0.72));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.65);
    dirLight.position.set(2000, 3500, 2500);
    scene.add(dirLight);

    const grid = new THREE.GridHelper(8000, 80, 0x263238, 0x151C24);
    grid.position.set(2000, 0, 1500);
    scene.add(grid);

    scene.add(grupoParedes3D);
    scene.add(grupoAmbienteModulos);
    scene.add(grupoVaos3D);

    window.addEventListener("resize", () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });

    configurarEventosMouseETeclado();
    animar();
}

function animar() {
    requestAnimationFrame(animar);
    atualizarTransparenciaInteligenteParedes();
    renderer.render(scene, camera);
}

function atualizarTransparenciaInteligenteParedes() {
    if (modoCamera === "PLANTA_2D") return;
    const posCam = camera.position;

    grupoParedes3D.children.forEach(meshPar => {
        if (!meshPar.userData || !meshPar.userData.dadosParede) return;
        const p = meshPar.userData.dadosParede;
        const mx = (p.x1 + p.x2) / 2.0;
        const mz = (p.y1 + p.y2) / 2.0;
        const vx = posCam.x - mx;
        const vz = posCam.z - mz;
        const nx = p.vetor_normal_interno.nx;
        const nz = p.vetor_normal_interno.ny;

        const dot = (vx * nx) + (vz * nz);
        meshPar.material.opacity = (dot < 0) ? 0.12 : 0.85;
    });
}

// =============================================================================
// 2. COLETA UNIFICADA DE PARÂMETROS E FABRICAÇÃO DE MÓDULOS
// =============================================================================
function coletarOverridesPerfilUI() {
    const escolhaTopo = document.getElementById("sel_topo_balcao").value;
    let posSarrafoTraseiro = "DEITADO";
    if (escolhaTopo === "EM_PE") posSarrafoTraseiro = "EM_PE";
    else if (escolhaTopo === "SEM_TRAVESSA_TRASEIRA") posSarrafoTraseiro = "SEM_TRAVESSA_TRASEIRA";

    return {
        tipo_montagem_caixa: document.getElementById("sel_sistema_fixacao").value,
        materiais_padrao: {
            espessura_estrutural_mm: parseFloat(document.getElementById("sel_esp_caixa").value),
            espessura_frente_mm: parseFloat(document.getElementById("sel_esp_frente").value)
        },
        geometria_caixaria: {
            montagem_base_inferior: document.getElementById("sel_modo_base").value,
            montagem_teto_balcao: escolhaTopo === "TAMPO_INTEIRO" ? "TAMPO_INTEIRO" : "SARRAFOS",
            posicao_sarrafo_traseiro_balcao: posSarrafoTraseiro,
            tipo_montagem_fundo: document.getElementById("sel_modo_fundo").value,
            sistema_fixacao_aereo: document.getElementById("sel_fixacao_aereo").value,
            reforco_traseiro_torre: document.getElementById("sel_reforco_torre").value,
            largura_sarrafo: parseFloat(document.getElementById("inp_larg_sarrafo").value),
            recuo_frontal_prateleira: parseFloat(document.getElementById("inp_recuo_prat").value),
            recuo_canal_fundo: parseFloat(document.getElementById("inp_recuo_fundo").value)
        },
        folgas_frentes: {
            tipo_montagem_frente: document.getElementById("sel_modo_frente").value,
            gap_lateral_esquerda: parseFloat(document.getElementById("inp_gap_esq").value),
            gap_lateral_direita: parseFloat(document.getElementById("inp_gap_dir").value),
            gap_superior: parseFloat(document.getElementById("inp_gap_vert").value),
            gap_inferior: parseFloat(document.getElementById("inp_gap_vert").value),
            gap_entre_frentes: parseFloat(document.getElementById("inp_gap_entre").value)
        },
        regras_gaveta: {
            folga_corredica_cada_lado: parseFloat(document.getElementById("inp_folga_corredica").value)
        },
        parametros_usinagem: {
            largura_canal_fundo: parseFloat(document.getElementById("inp_larg_canal").value),
            profundidade_canal_fundo: parseFloat(document.getElementById("inp_prof_canal").value),
            broca_parafuso_estrutural: parseFloat(document.getElementById("inp_broca_estrut").value),
            distancia_centro_caneco_borda: parseFloat(document.getElementById("inp_cota_caneco").value)
        }
    };
}

function alternarFamiliaUI() {
    const fam = document.getElementById("sel_familia").value;
    document.getElementById("card_opcoes_painel").style.display = (fam === "MODULO_PAINEL") ? "flex" : "none";
    document.getElementById("card_opcoes_avulso").style.display = (fam === "MODULO_AVULSO") ? "flex" : "none";
    document.getElementById("card_caixaria_fabrica").style.display =
        (fam === "MODULO_PAINEL" || fam === "MODULO_AVULSO") ? "none" : "flex";

    if (fam === "MODULO_AEREO") {
        document.getElementById("inp_elevacao_z").value = 1450;
        document.getElementById("inp_profundidade").value = 350;
    } else if (fam === "MODULO_TORRE") {
        document.getElementById("inp_elevacao_z").value = 0;
        document.getElementById("inp_altura").value = 2200;
        document.getElementById("inp_profundidade").value = 550;
    } else if (fam === "MODULO_INFERIOR") {
        document.getElementById("inp_elevacao_z").value = 0;
        document.getElementById("inp_altura").value = 700;
        document.getElementById("inp_profundidade").value = 550;
    }
}

function mudarModoCamera(novoModo) {
    modoCamera = novoModo;
    document.getElementById("btn_modo_isolado").classList.toggle("ativo", novoModo === "ISOLADO");
    document.getElementById("btn_modo_ambiente3d").classList.toggle("ativo", novoModo === "AMBIENTE_3D");
    document.getElementById("btn_modo_planta2d").classList.toggle("ativo", novoModo === "PLANTA_2D");
    document.getElementById("painel_construtor_paredes").style.display = (novoModo === "PLANTA_2D") ? "block" : "none";

    if (novoModo === "PLANTA_2D") {
        camera.position.set(1800, 5200, 1200);
        controls.target.set(1800, 0, 1200);
        controls.enableRotate = false;
    } else if (novoModo === "AMBIENTE_3D") {
        controls.enableRotate = true;
        camera.position.set(2200, 2100, 3800);
        controls.target.set(1600, 600, 800);
    } else {
        controls.enableRotate = true;
        if (moduloAtivo) {
            const lx = moduloAtivo.dimensoes_ocupadas.largura_x / 2.0;
            const ay = moduloAtivo.dimensoes_ocupadas.altura_y / 2.0;
            const pz = moduloAtivo.dimensoes_ocupadas.profundidade_z / 2.0;
            camera.position.set(lx + 900, ay + 800, pz + 1700);
            controls.target.set(lx, ay, pz);
        }
    }
    controls.update();
    renderizarCenaCompleta();
}

function usarPreset(texto) {
    document.getElementById("inp_prompt").value = texto;
    fabricarModuloAtual(false);
}

function criarNovoSlotModulo() {
    let maiorNum = 0;
    modulosCache.forEach(m => {
        const n = parseInt(m.id_modulo);
        if (!isNaN(n) && n > maiorNum) maiorNum = n;
    });
    const proximoId = String(maiorNum + 1).padStart(3, "0");
    document.getElementById("inp_id_modulo").value = proximoId;

    const fam = document.getElementById("sel_familia").value;
    document.getElementById("inp_elevacao_z").value = (fam === "MODULO_AEREO") ? 1450 : 0;

    fabricarModuloAtual(true);
}

async function fabricarModuloAtual(forcarAutoSnap = false) {
    const overrides = coletarOverridesPerfilUI();
    const opcoesEspeciais = {
        modo_espessura: document.getElementById("sel_modo_painel").value,
        orientacao_espacial: document.getElementById("sel_orient_painel").value,
        nome_personalizado: document.getElementById("inp_nome_painel").value,
        subtipo_avulso: document.getElementById("sel_subtipo_avulso").value,
        quantidade_avulso: parseInt(document.getElementById("inp_qtd_avulso").value)
    };

    const payload = {
        id_modulo: document.getElementById("inp_id_modulo").value,
        familia: document.getElementById("sel_familia").value,
        largura_x: parseFloat(document.getElementById("inp_largura").value),
        altura_y: parseFloat(document.getElementById("inp_altura").value),
        profundidade_z: parseFloat(document.getElementById("inp_profundidade").value),
        material_caixaria: document.getElementById("sel_mat_caixa").value,
        material_frentes: document.getElementById("sel_mat_frentes").value,
        overrides_perfil: overrides,
        opcoes_especiais: opcoesEspeciais,
        prompt_copiloto: document.getElementById("inp_prompt").value,
        id_parede: document.getElementById("sel_parede_modulo").value || null,
        elevacao_z: parseFloat(document.getElementById("inp_elevacao_z").value),
        usar_autosnap: forcarAutoSnap
    };

    const resp = await fetch("/api/fabricar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const dados = await resp.json();

    if (!dados.sucesso) {
        alert(dados.erro_engenharia || dados.erro_interno);
        return;
    }

    moduloAtivo = dados.modulo;
    idsSelecionados.clear();
    idsSelecionados.add(moduloAtivo.id_modulo);
    await carregarEstadoAmbiente();
}

// =============================================================================
// 3. CONTROLE DIRECIONAL (D-PAD), MULTI-SELEÇÃO E TRANSFORMAÇÃO EM LOTE
// =============================================================================
function obterListaIdsAlvo() {
    if (idsSelecionados.size > 0) return Array.from(idsSelecionados);
    if (moduloAtivo) return [moduloAtivo.id_modulo];
    return [];
}

async function moverSelecionados(dirX, dirY, dirZ) {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    const passo = parseFloat(document.getElementById("sel_passo_dpad").value) || 100.0;
    const resp = await fetch("/api/modulos/transformar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            ids_modulos: ids,
            delta_x: dirX * passo,
            delta_y: dirY * passo,
            delta_z: dirZ * passo
        })
    });
    const dados = await resp.json();
    if (dados.sucesso) await carregarEstadoAmbiente();
}

async function girarSelecionados(deltaGraus) {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    const resp = await fetch("/api/modulos/transformar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids, delta_rotacao: deltaGraus })
    });
    const dados = await resp.json();
    if (dados.sucesso) await carregarEstadoAmbiente();
}

async function definirZAbsolutoSelecionados(novoZ) {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    await fetch("/api/modulos/transformar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids, z_absoluto: novoZ })
    });
    await carregarEstadoAmbiente();
}

async function resetarRotacaoEParedeSelecionados() {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    await fetch("/api/modulos/transformar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids, y_absoluto: 0.0, rotacao_absoluta: 0.0 })
    });
    await carregarEstadoAmbiente();
}

async function encostarAutoSnapSelecionados() {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    await fetch("/api/modulos/transformar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids, aplicar_autosnap: true, y_absoluto: 0.0, rotacao_absoluta: 0.0 })
    });
    await carregarEstadoAmbiente();
}

async function trocarParedeSelecionados(idNovaParede) {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    await fetch("/api/modulos/transformar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids, nova_id_parede: idNovaParede, aplicar_autosnap: true })
    });
    await carregarEstadoAmbiente();
}

async function excluirSelecionados() {
    const ids = obterListaIdsAlvo();
    if (ids.length === 0) return;

    const resp = await fetch("/api/modulos/excluir_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids_modulos: ids })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        idsSelecionados.clear();
        moduloAtivo = null;
        await carregarEstadoAmbiente();
    }
}

function selecionarTodosModulos() {
    modulosCache.forEach(m => idsSelecionados.add(m.id_modulo));
    atualizarContadorSelecaoUI();
    renderizarCenaCompleta();
    atualizarListaModulosDOM();
}

function limparSelecaoMultipla() {
    idsSelecionados.clear();
    if (moduloAtivo) idsSelecionados.add(moduloAtivo.id_modulo);
    atualizarContadorSelecaoUI();
    renderizarCenaCompleta();
    atualizarListaModulosDOM();
}

function alternarCheckboxModulo(idMod, event) {
    event.stopPropagation();
    if (idsSelecionados.has(idMod)) idsSelecionados.delete(idMod);
    else idsSelecionados.add(idMod);
    atualizarContadorSelecaoUI();
    renderizarCenaCompleta();
    atualizarListaModulosDOM();
}

function atualizarContadorSelecaoUI() {
    const qtd = idsSelecionados.size;
    document.getElementById("lbl_selecao_dpad").innerText =
        qtd > 1 ? `🎯 ${qtd} Módulos (Lote)` : `🎯 ${qtd === 1 ? '#' + Array.from(idsSelecionados)[0] : 'Nenhum'}`;
}

// =============================================================================
// 4. SINCRONIZAÇÃO DE ESTADO DO AMBIENTE E FILA DE MÓDULOS
// =============================================================================
async function carregarEstadoAmbiente() {
    const resp = await fetch("/api/ambiente");
    const dados = await resp.json();
    ambienteCache = dados.ambiente;
    modulosCache = dados.modulos;

    const selPar = document.getElementById("sel_parede_modulo");
    const parAtual = selPar.value;
    selPar.innerHTML = "";
    (ambienteCache.paredes || []).forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id_parede;
        opt.innerText = `${p.nome} (${p.comprimento}mm | ${p.angulo_graus}°)`;
        selPar.appendChild(opt);
    });
    if (parAtual) selPar.value = parAtual;

    if (!moduloAtivo && modulosCache.length > 0) moduloAtivo = modulosCache[0];
    if (moduloAtivo) {
        moduloAtivo = modulosCache.find(m => m.id_modulo === moduloAtivo.id_modulo) || modulosCache[0] || null;
    }
    if (moduloAtivo && idsSelecionados.size === 0) idsSelecionados.add(moduloAtivo.id_modulo);

    atualizarContadorSelecaoUI();
    atualizarListaModulosDOM();

    let totalPecas = 0;
    modulosCache.forEach(m => totalPecas += m.lista_de_pecas.length);
    document.getElementById("lbl_resumo_topo").innerText =
        `🏠 ${ambienteCache.paredes.length} Parede(s) | 📦 ${modulosCache.length} Item(ns) | ${totalPecas} Peças p/ TiranoCut`;

    if (moduloAtivo) sincronizarInputsPosicao(moduloAtivo);
    renderizarCenaCompleta();
}

function atualizarListaModulosDOM() {
    const container = document.getElementById("lista_modulos_ambiente");
    container.innerHTML = "";

    modulosCache.forEach(mod => {
        const pos = mod.posicionamento_ambiente || {};
        const ehAtivo = (moduloAtivo && moduloAtivo.id_modulo === mod.id_modulo);
        const ehMarcado = idsSelecionados.has(mod.id_modulo);

        const div = document.createElement("div");
        div.className = "module-item" + (ehAtivo ? " active" : (ehMarcado ? " multi-selected" : ""));
        div.innerHTML = `
            <input type="checkbox" class="chk-sel" ${ehMarcado ? 'checked' : ''} onclick="alternarCheckboxModulo('${mod.id_modulo}', event)">
            <span style="flex:1;" onclick="selecionarModuloDaFila('${mod.id_modulo}', false)">
                <strong>#${mod.id_modulo}</strong> ${mod.familia.replace('MODULO_', '')} (${mod.dimensoes_ocupadas.largura_x}mm)
                <small style="color:#80D8FF;">[${pos.nome_parede || 'Livre'} X:${pos.distancia_x_parede || 0} Z:${pos.elevacao_z || 0}]</small>
            </span>
            <span style="color:#4CE660;">${mod.lista_de_pecas.length}pç</span>
        `;
        container.appendChild(div);
    });
}

function sincronizarInputsPosicao(mod) {
    if (!mod || !mod.posicionamento_ambiente) return;
    const pos = mod.posicionamento_ambiente;
    if (pos.id_parede) document.getElementById("sel_parede_modulo").value = pos.id_parede;
    document.getElementById("inp_dist_x_parede").value = pos.distancia_x_parede || 0;
    document.getElementById("inp_afast_y").value = pos.afastamento_parede || 0;
    document.getElementById("inp_elevacao_z").value = pos.elevacao_z || 0;
    document.getElementById("inp_rot_offset").value = pos.rotacao_offset_graus || 0;
    document.getElementById("lbl_sobra_parede").innerText =
        `Espaço restante na ${pos.nome_parede}: ${pos.sobra_parede_mm} mm`;
}

function selecionarModuloDaFila(idMod, somarSelecao = false) {
    const achado = modulosCache.find(m => m.id_modulo === idMod);
    if (!achado) return;
    moduloAtivo = achado;

    if (somarSelecao) {
        if (idsSelecionados.has(idMod)) idsSelecionados.delete(idMod);
        else idsSelecionados.add(idMod);
    } else {
        idsSelecionados.clear();
        idsSelecionados.add(idMod);
    }

    document.getElementById("inp_id_modulo").value = achado.id_modulo;
    document.getElementById("sel_familia").value = achado.familia;
    alternarFamiliaUI();
    document.getElementById("inp_largura").value = achado.dimensoes_ocupadas.largura_x;
    document.getElementById("inp_altura").value = achado.dimensoes_ocupadas.altura_y;
    document.getElementById("inp_profundidade").value = achado.dimensoes_ocupadas.profundidade_z;
    if (achado.prompt_original) document.getElementById("inp_prompt").value = achado.prompt_original;

    sincronizarInputsPosicao(achado);
    atualizarContadorSelecaoUI();
    atualizarListaModulosDOM();
    renderizarCenaCompleta();
}

async function posicionarModuloManual(usarSnap) {
    if (!moduloAtivo) return;
    const resp = await fetch("/api/modulo/posicionar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: moduloAtivo.id_modulo,
            id_parede: document.getElementById("sel_parede_modulo").value,
            distancia_x_parede: parseFloat(document.getElementById("inp_dist_x_parede").value),
            afastamento_parede: parseFloat(document.getElementById("inp_afast_y").value),
            elevacao_z: parseFloat(document.getElementById("inp_elevacao_z").value),
            rotacao_offset_graus: parseFloat(document.getElementById("inp_rot_offset").value),
            usar_autosnap: usarSnap
        })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        await carregarEstadoAmbiente();
    }
}

function descontarCantoParede() {
    const atual = parseFloat(document.getElementById("inp_dist_x_parede").value) || 0;
    document.getElementById("inp_dist_x_parede").value = atual + 550;
    posicionarModuloManual(false);
}

// =============================================================================
// 5. MOTOR DE RENDERIZAÇÃO 3D E CINEMÁTICA (GIRO, BASCULANTE E GAVETAS)
// =============================================================================
function cadParaThree(x, y, z, profTotal) {
    return new THREE.Vector3(x, z, profTotal - y);
}

function renderizarCenaCompleta() {
    grupoParedes3D.clear();
    grupoAmbienteModulos.clear();
    grupoVaos3D.clear();

    if (modoCamera !== "ISOLADO") renderizarParedesAmbiente();

    const listaParaDesenhar = (modoCamera === "ISOLADO" && moduloAtivo)
        ? [moduloAtivo]
        : modulosCache;

    listaParaDesenhar.forEach(mod => {
        const ehAtivo = (moduloAtivo && mod.id_modulo === moduloAtivo.id_modulo);
        const ehMultiSel = idsSelecionados.has(mod.id_modulo);
        const grupoMod = construirGrupo3DDoModulo(mod, ehAtivo, ehMultiSel);

        if (modoCamera !== "ISOLADO" && mod.posicionamento_ambiente) {
            const pos = mod.posicionamento_ambiente;
            grupoMod.position.set(pos.x_ambiente, pos.z_ambiente, pos.y_ambiente);
            grupoMod.rotation.y = -THREE.MathUtils.degToRad(pos.rotacao_graus || 0);
        }

        grupoAmbienteModulos.add(grupoMod);
    });

    if (moduloAtivo) atualizarListaPecasUI(moduloAtivo);
    atualizarCinematica3D();
}

function renderizarParedesAmbiente() {
    (ambienteCache.paredes || []).forEach(p => {
        const comp = p.comprimento;
        const alt = (modoCamera === "PLANTA_2D") ? 120.0 : p.pe_direito;
        const esp = p.espessura;

        const geom = new THREE.BoxGeometry(comp, alt, esp);
        const mat = new THREE.MeshStandardMaterial({
            color: 0x263238,
            roughness: 0.9,
            transparent: true,
            opacity: modoCamera === "PLANTA_2D" ? 0.95 : 0.85
        });
        const mesh = new THREE.Mesh(geom, mat);

        const rad = THREE.MathUtils.degToRad(p.angulo_graus);
        const nx = p.vetor_normal_interno.nx;
        const ny = p.vetor_normal_interno.ny;

        const cx = ((p.x1 + p.x2) / 2.0) - (nx * (esp / 2.0));
        const cz = ((p.y1 + p.y2) / 2.0) - (ny * (esp / 2.0));

        mesh.position.set(cx, alt / 2.0, cz);
        mesh.rotation.y = -rad;
        mesh.userData = { dadosParede: p };

        const edges = new THREE.EdgesGeometry(geom);
        mesh.add(new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xFFB74D })));

        grupoParedes3D.add(mesh);
    });
}

function construirGrupo3DDoModulo(modulo, ehAtivo, ehMultiSel) {
    const grupoMod = new THREE.Group();
    grupoMod.userData = { idModulo: modulo.id_modulo };

    const largTotal = modulo.dimensoes_ocupadas.largura_x;
    const altTotal = modulo.dimensoes_ocupadas.altura_y;
    const profTotal = modulo.dimensoes_ocupadas.profundidade_z;

    const cxMod = largTotal / 2.0;
    const cyMod = altTotal / 2.0;
    const czMod = profTotal / 2.0;

    if (ehAtivo || ehMultiSel) {
        const origemGizmo = new THREE.Vector3(cxMod, altTotal + 45, czMod);
        grupoMod.add(new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), origemGizmo, 240, 0xFF5252, 45, 28));
        grupoMod.add(new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), origemGizmo, 240, 0x448AFF, 45, 28));
        grupoMod.add(new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), origemGizmo, 240, 0x4CE660, 45, 28));
    }

    modulo.lista_de_pecas.forEach(p => {
        const dx = p.dimensoes.x, dy = p.dimensoes.y, dz = p.dimensoes.z;
        const px = p.posicao_relativa.pos_x, py = p.posicao_relativa.pos_y, pz = p.posicao_relativa.pos_z;

        const containerPeca = new THREE.Group();
        const centroThree = cadParaThree(px + dx / 2.0, py + dy / 2.0, pz + dz / 2.0, profTotal);
        containerPeca.position.copy(centroThree);

        containerPeca.userData = {
            peca: p,
            idModulo: modulo.id_modulo,
            posOriginal: centroThree.clone(),
            vetorExplosao: new THREE.Vector3(centroThree.x - cxMod, centroThree.y - cyMod, centroThree.z - czMod).normalize()
        };

        let corHex = MAPA_HEX_MATERIAIS[p.material] || 0xECEFF1;
        if (p.material && p.material.toLowerCase().includes("freijo")) corHex = 0xB87A4B;
        else if (p.material && p.material.toLowerCase().includes("carvalho")) corHex = 0xC89D66;
        else if (p.categoria_industrial.includes("fundo")) corHex = 0xBCAAA4;
        else if (p.categoria_industrial.includes("regua_mao_amiga") || p.categoria_industrial.includes("reforco")) corHex = 0x90A4AE;
        else if (p.categoria_industrial.includes("frente") || p.categoria_industrial.includes("porta")) corHex = 0xDCE775;

        const geom = new THREE.BoxGeometry(dx, dz, dy);
        const mat = new THREE.MeshStandardMaterial({
            color: corHex,
            roughness: 0.55,
            transparent: modoRaioX,
            opacity: modoRaioX ? 0.22 : 1.0
        });
        const meshMdf = new THREE.Mesh(geom, mat);
        meshMdf.name = "corpo_mdf";
        meshMdf.userData = { idModulo: modulo.id_modulo };
        containerPeca.add(meshMdf);

        let corBorda = 0x263238;
        if (ehAtivo) corBorda = 0x4CE660;
        else if (ehMultiSel) corBorda = 0x00E5FF;

        containerPeca.add(new THREE.LineSegments(new THREE.EdgesGeometry(geom), new THREE.LineBasicMaterial({ color: corBorda })));

        const grupoFitas = new THREE.Group();
        grupoFitas.name = "camada_fitas";
        grupoFitas.visible = mostrarFitas;
        adicionarFitasBorda3D(grupoFitas, p, dx, dy, dz);
        containerPeca.add(grupoFitas);

        const grupoUsinagens = new THREE.Group();
        grupoUsinagens.name = "camada_usinagens";
        grupoUsinagens.visible = mostrarUsinagens;
        adicionarUsinagens3D(grupoUsinagens, p, centroThree, profTotal);
        containerPeca.add(grupoUsinagens);

        grupoMod.add(containerPeca);
    });

    if (ehAtivo && modulo.arvore_espacial_vaos) {
        desenharNoEspacialRecursivo(modulo.arvore_espacial_vaos, profTotal, grupoMod);
    }

    return grupoMod;
}

function atualizarListaPecasUI(modulo) {
    document.getElementById("txt_resposta_copiloto").innerText =
        modulo.resposta_copiloto || `Item #${modulo.id_modulo} selecionado.`;

    const listaUI = document.getElementById("lista_pecas_modulo");
    listaUI.innerHTML = "";
    document.getElementById("qtd_pecas_mod").innerText = modulo.lista_de_pecas.length;

    modulo.lista_de_pecas.forEach((p, idx) => {
        const item = document.createElement("div");
        item.className = "part-item";
        const d2 = p.dimensoes_2d_planificadas;
        const tagEsp = p.espelhar_cam_x ? `<span class="tag-mirror">🔄 ESP</span>` : "";
        item.innerHTML = `
            <span>#${idx + 1} ${p.nome_comercial} ${tagEsp}</span>
            <span style="color:#90A4AE;">${d2.largura_x}x${d2.altura_y}</span>
        `;
        listaUI.appendChild(item);
        item.onclick = () => selecionarPecaParaPintura(p);
    });
}

function adicionarFitasBorda3D(grupoFitas, p, dx, dy, dz) {
    if (!p.fitas_borda) return;
    const matFita = new THREE.MeshBasicMaterial({ color: 0xFF1744 });
    const espFita = 1.4;

    if (p.orientacao_3d === "HORIZONTAL_XY") {
        if (p.fitas_borda.base) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(dx, dz, espFita), matFita);
            m.position.set(0, 0, dy / 2.0);
            grupoFitas.add(m);
        }
    } else if (p.orientacao_3d === "VERTICAL_YZ") {
        if (p.fitas_borda.esquerda) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(dx + 0.5, dz, espFita), matFita);
            m.position.set(0, 0, dy / 2.0);
            grupoFitas.add(m);
        }
        if (p.fitas_borda.topo) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(dx + 0.5, espFita, dy), matFita);
            m.position.set(0, dz / 2.0, 0);
            grupoFitas.add(m);
        }
    } else {
        if (p.fitas_borda.topo) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(dx, espFita, dy + 0.5), matFita);
            m.position.set(0, dz / 2.0, 0);
            grupoFitas.add(m);
        }
        if (p.fitas_borda.base) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(dx, espFita, dy + 0.5), matFita);
            m.position.set(0, -dz / 2.0, 0);
            grupoFitas.add(m);
        }
        if (p.fitas_borda.esquerda) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(espFita, dz, dy + 0.5), matFita);
            m.position.set(-dx / 2.0, 0, 0);
            grupoFitas.add(m);
        }
        if (p.fitas_borda.direita) {
            const m = new THREE.Mesh(new THREE.BoxGeometry(espFita, dz, dy + 0.5), matFita);
            m.position.set(dx / 2.0, 0, 0);
            grupoFitas.add(m);
        }
    }
}

function adicionarUsinagens3D(grupoUsinagens, p, centroPecaThree, profTotal) {
    (p.usinagens.rasgos || []).forEach(r => {
        if (!r.geometria_3d) return;
        const g = r.geometria_3d;
        const meshR = new THREE.Mesh(
            new THREE.BoxGeometry(g.dx + 0.4, g.dz + 0.4, g.dy + 0.4),
            new THREE.MeshBasicMaterial({ color: 0x4E342E })
        );
        const posGlobalR = cadParaThree(g.pos_x + g.dx / 2.0, g.pos_y + g.dy / 2.0, g.pos_z + g.dz / 2.0, profTotal);
        meshR.position.copy(posGlobalR.sub(centroPecaThree));
        grupoUsinagens.add(meshR);
    });

    (p.usinagens.furos || []).forEach(f => {
        if (!f.geometria_3d) return;
        const g = f.geometria_3d;
        const raio = Math.max(f.diametro / 2.0, 2.2);
        const altCilindro = p.dimensoes_2d_planificadas.espessura + 1.5;

        let corFuro = 0x00E5FF;
        if (f.diametro >= 30.0) corFuro = 0xFF9800;
        else if (f.diametro >= 14.0) corFuro = 0xE040FB;
        else if (f.diametro >= 7.5) corFuro = 0x7C4DFF;
        else if (f.diametro <= 3.5) corFuro = 0xFFEB3B;

        const meshF = new THREE.Mesh(
            new THREE.CylinderGeometry(raio, raio, altCilindro, 16),
            new THREE.MeshBasicMaterial({ color: corFuro })
        );
        if (g.eixo === "X") meshF.rotation.z = Math.PI / 2.0;
        else if (g.eixo === "Y") meshF.rotation.x = Math.PI / 2.0;

        const posGlobalF = cadParaThree(g.x, g.y, g.z, profTotal);
        meshF.position.copy(posGlobalF.sub(centroPecaThree));
        grupoUsinagens.add(meshF);
    });
}

function desenharNoEspacialRecursivo(no, profTotal, grupoMod) {
    if (no.eh_folha) {
        const g = no.geometria_3d;
        const geom = new THREE.BoxGeometry(g.largura - 4, g.altura - 4, g.profundidade - 4);
        const matFace = new THREE.MeshBasicMaterial({
            color: no.id_vao === vaoSelecionadoId ? 0x4CE660 : 0x00E5FF,
            transparent: true,
            opacity: no.id_vao === vaoSelecionadoId ? 0.22 : 0.08,
            depthWrite: false
        });
        const box = new THREE.Mesh(geom, matFace);
        box.position.copy(cadParaThree(g.x + g.largura / 2.0, g.y + g.profundidade / 2.0, g.z + g.altura / 2.0, profTotal));
        box.userData = { noEspacial: no, ehCaixaVao: true };
        box.visible = mostrarVaos;

        const edges = new THREE.EdgesGeometry(geom);
        box.add(new THREE.LineSegments(edges, new THREE.LineBasicMaterial({
            color: no.id_vao === vaoSelecionadoId ? 0x4CE660 : 0x00E5FF
        })));

        grupoMod.add(box);
        grupoVaos3D.children.push(box);
    }
    (no.filhos || []).forEach(f => desenharNoEspacialRecursivo(f, profTotal, grupoMod));
}

function atualizarCinematica3D() {
    const fatorExplosao = parseFloat(document.getElementById("rng_explosao").value);
    const pctAbertura = parseFloat(document.getElementById("rng_abertura").value) / 100.0;

    grupoAmbienteModulos.children.forEach(grupoMod => {
        grupoMod.children.forEach(container => {
            if (!container.userData || !container.userData.peca) return;
            const orig = container.userData.posOriginal;
            const dir = container.userData.vetorExplosao;
            const p = container.userData.peca;
            const cat = p.categoria_industrial;

            const baseX = orig.x + dir.x * fatorExplosao;
            const baseY = orig.y + dir.y * fatorExplosao;
            const baseZ = orig.z + dir.z * fatorExplosao;

            container.rotation.set(0, 0, 0);

            if (cat.includes("gaveta") || cat.includes("tempero") || cat.includes("sapateira")) {
                if (!cat.includes("engrosso")) {
                    container.position.set(baseX, baseY, baseZ + (pctAbertura * 340.0));
                } else {
                    container.position.set(baseX, baseY, baseZ);
                }
            } else if (cat.includes("porta_basculante")) {
                const meiaAlt = p.dimensoes.z / 2.0;
                const anguloBasc = pctAbertura * ((95.0 * Math.PI) / 180.0);
                const yDobradicaTopo = baseY + meiaAlt;
                const dyCentro = baseY - yDobradicaTopo;

                container.position.set(
                    baseX,
                    yDobradicaTopo + dyCentro * Math.cos(anguloBasc),
                    baseZ - dyCentro * Math.sin(anguloBasc)
                );
                container.rotation.x = -anguloBasc;
            } else if (cat.includes("porta_giro")) {
                const ehDireita = cat.includes("direita");
                const meiaLarg = p.dimensoes.x / 2.0;
                const angulo = pctAbertura * ((92.0 * Math.PI) / 180.0) * (ehDireita ? 1.0 : -1.0);
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
}

// =============================================================================
// 6. EVENTOS DE MOUSE (RAYCASTING 3D / PLANTA 2D) E ATALHOS DE TECLADO
// =============================================================================
function configurarEventosMouseETeclado() {
    const container = document.getElementById("canvas-container");
    let posDown = { x: 0, y: 0 };

    container.addEventListener("pointerdown", (e) => {
        posDown = { x: e.clientX, y: e.clientY };
    });

    container.addEventListener("pointerup", async (event) => {
        if (event.button !== 0) return;
        if (Math.hypot(event.clientX - posDown.x, event.clientY - posDown.y) > 6) return;

        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);

        if (modoCamera === "PLANTA_2D") {
            const ptIntersecao = new THREE.Vector3();
            raycaster.ray.intersectPlane(planoPiso, ptIntersecao);
            if (!ptIntersecao) return;

            const xGrid = Math.round(ptIntersecao.x / 50.0) * 50.0;
            const yGrid = Math.round(ptIntersecao.z / 50.0) * 50.0;

            if (!pontoInicialParede2D) {
                pontoInicialParede2D = { x: xGrid, y: yGrid };
                document.getElementById("status_desenho_2d").innerText =
                    `📍 Origem (${xGrid}, ${yGrid}). Clique no ponto final!`;
            } else {
                const dist = Math.hypot(xGrid - pontoInicialParede2D.x, yGrid - pontoInicialParede2D.y);
                if (dist >= 100) {
                    await fetch("/api/ambiente/parede/adicionar", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            x1: pontoInicialParede2D.x,
                            y1: pontoInicialParede2D.y,
                            x2: xGrid,
                            y2: yGrid,
                            pe_direito: parseFloat(document.getElementById("inp_pe_direito").value),
                            espessura: parseFloat(document.getElementById("inp_esp_parede").value)
                        })
                    });
                    pontoInicialParede2D = null;
                    document.getElementById("status_desenho_2d").innerText = "✅ Parede criada!";
                    await carregarEstadoAmbiente();
                }
            }
            return;
        }

        if (mostrarVaos && grupoVaos3D.children.length > 0) {
            const intVaos = raycaster.intersectObjects(grupoVaos3D.children, false);
            if (intVaos.length > 0) {
                const noClicado = intVaos[0].object.userData.noEspacial;
                vaoSelecionadoId = noClicado.id_vao;
                abrirPainelVao(noClicado);
                renderizarCenaCompleta();
                return;
            }
        }

        const malhasMdf = [];
        grupoAmbienteModulos.traverse(obj => {
            if (obj.isMesh && obj.name === "corpo_mdf") malhasMdf.push(obj);
        });

        const intMod = raycaster.intersectObjects(malhasMdf, false);
        if (intMod.length > 0) {
            const idModClicado = intMod[0].object.userData.idModulo;
            if (idModClicado) selecionarModuloDaFila(idModClicado, event.shiftKey);
        }
    });

    window.addEventListener("keydown", (e) => {
        if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;

        if (e.key === "Delete") {
            e.preventDefault();
            excluirSelecionados();
        } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            moverSelecionados(-1, 0, 0);
        } else if (e.key === "ArrowRight") {
            e.preventDefault();
            moverSelecionados(1, 0, 0);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            moverSelecionados(0, -1, 0);
        } else if (e.key === "ArrowDown") {
            e.preventDefault();
            moverSelecionados(0, 1, 0);
        } else if (e.key === "PageUp") {
            e.preventDefault();
            moverSelecionados(0, 0, 1);
        } else if (e.key === "PageDown") {
            e.preventDefault();
            moverSelecionados(0, 0, -1);
        } else if (e.key.toLowerCase() === "r") {
            e.preventDefault();
            girarSelecionados(45);
        }
    });
}

// =============================================================================
// 7. OPERAÇÕES DE PAREDES E DO MENU DE VÃO 3D
// =============================================================================
async function aplicarPresetParedes() {
    await fetch("/api/ambiente/preset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            formato: document.getElementById("sel_preset_parede").value,
            pe_direito: parseFloat(document.getElementById("inp_pe_direito").value),
            espessura: parseFloat(document.getElementById("inp_esp_parede").value)
        })
    });
    await carregarEstadoAmbiente();
}

async function adicionarSegmentoParedeUI() {
    await fetch("/api/ambiente/parede/adicionar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            comprimento: parseFloat(document.getElementById("inp_comp_nova_par").value),
            angulo_graus: parseFloat(document.getElementById("sel_ang_nova_par").value),
            pe_direito: parseFloat(document.getElementById("inp_pe_direito").value),
            espessura: parseFloat(document.getElementById("inp_esp_parede").value)
        })
    });
    await carregarEstadoAmbiente();
}

async function removerUltimaParedeUI() {
    await fetch("/api/ambiente/parede/remover_ultima", { method: "POST" });
    await carregarEstadoAmbiente();
}

async function limparTodasParedesUI() {
    await fetch("/api/ambiente/paredes/limpar", { method: "POST" });
    await carregarEstadoAmbiente();
}

// =============================================================================
// 8. MENU INTERATIVO DE EDIÇÃO DIRETA DO NÓ ESPACIAL (VÃO 3D)
// =============================================================================
function abrirPainelVao(no) {
    const g = no.geometria_3d;
    document.getElementById("painel_interacao_vao").style.display = "block";
    document.getElementById("titulo_vao_clicado").innerText = `📐 ${no.nome_vao} (${no.id_vao})`;
    document.getElementById("medidas_vao_clicado").innerHTML =
        `Vão Livre: <b>${g.largura} x ${g.altura} x ${g.profundidade}mm</b><br>` +
        `Status: <b>${no.ocupacao_interna || "Livre"}</b>`;
}

function fecharPainelVao() {
    vaoSelecionadoId = null;
    document.getElementById("painel_interacao_vao").style.display = "none";
    renderizarCenaCompleta();
}

async function aplicarOperacaoNoVao(tipoOp, extras = {}) {
    if (!moduloAtivo || !vaoSelecionadoId) return;
    let operacoesAtuais = moduloAtivo.operacoes_internas ? [...moduloAtivo.operacoes_internas] : [];

    // Substitui ocupações ou portas anteriores do mesmo sub-vão para evitar conflitos
    const tiposOcupacao = ["GAVETEIRO", "GAVETEIRO_INTERNO", "SAPATEIRA", "PORTA_TEMPERO"];
    const tiposPorta = ["PORTAS_GIRO", "PORTAS_BASCULANTES"];

    if (tiposOcupacao.includes(tipoOp)) {
        operacoesAtuais = operacoesAtuais.filter(
            op => !(op.id_vao === vaoSelecionadoId && tiposOcupacao.includes(op.tipo))
        );
    } else if (tiposPorta.includes(tipoOp)) {
        operacoesAtuais = operacoesAtuais.filter(
            op => !(op.id_vao === vaoSelecionadoId && tiposPorta.includes(op.tipo))
        );
    }

    operacoesAtuais.push({ tipo: tipoOp, id_vao: vaoSelecionadoId, ...extras });
    document.getElementById("inp_prompt").value = "";

    // Coleta todas as opções de caixaria e fábrica (incluindo Sem Travessa Traseira, Mão Amiga e Reforço)
    const overrides = coletarOverridesPerfilUI();

    const resp = await fetch("/api/fabricar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_modulo: moduloAtivo.id_modulo,
            familia: document.getElementById("sel_familia").value,
            largura_x: parseFloat(document.getElementById("inp_largura").value),
            altura_y: parseFloat(document.getElementById("inp_altura").value),
            profundidade_z: parseFloat(document.getElementById("inp_profundidade").value),
            material_caixaria: document.getElementById("sel_mat_caixa").value,
            material_frentes: document.getElementById("sel_mat_frentes").value,
            overrides_perfil: overrides,
            operacoes_internas: operacoesAtuais
        })
    });
    const dados = await resp.json();
    if (!dados.sucesso) {
        alert(dados.erro_engenharia || dados.erro_interno);
        return;
    }

    moduloAtivo = dados.modulo;
    fecharPainelVao();
    await carregarEstadoAmbiente();
}

// =============================================================================
// 9. ALTERNÂNCIA DE CAMADAS VISUAIS E LIMPEZA DE PROJETO
// =============================================================================
function alternarCamadaUsinagens() {
    mostrarUsinagens = !mostrarUsinagens;
    document.getElementById("btn_usinagens").classList.toggle("ativo", mostrarUsinagens);
    renderizarCenaCompleta();
}

function alternarCamadaFitas() {
    mostrarFitas = !mostrarFitas;
    document.getElementById("btn_fitas").classList.toggle("ativo", mostrarFitas);
    renderizarCenaCompleta();
}

function alternarVaosEspaciais() {
    mostrarVaos = !mostrarVaos;
    document.getElementById("btn_vaos").classList.toggle("ativo", mostrarVaos);
    renderizarCenaCompleta();
}

function alternarRaioX() {
    modoRaioX = !modoRaioX;
    document.getElementById("btn_raiox").classList.toggle("ativo", modoRaioX);
    renderizarCenaCompleta();
}

async function limparAmbiente() {
    await fetch("/api/modulos/limpar", { method: "POST" });
    idsSelecionados.clear();
    moduloAtivo = null;
    await carregarEstadoAmbiente();
}

window.onload = async () => {
    inicializarPalco3D();
    await carregarCatalogoMateriais();
    await carregarEstadoAmbiente();
};

// =============================================================================
// 10. CATÁLOGO MULTI-MARCAS, MATRIZ DE 8 ZONAS E PINTOR DE PEÇA INDIVIDUAL
// =============================================================================
let catalogoMateriaisCache = [];
let pecaIndividualSelecionada = null;

const MAPA_HEX_MATERIAIS = {
    "generico_branco_tx": 0xECEFF1,
    "duratex_carvalho_avela": 0xB68656,
    "duratex_carvalho_hanover": 0xC89D66,
    "duratex_grafite_trama": 0x373B3E,
    "duratex_gianduia_trama": 0x8D7B68,
    "arauco_louro_freijo": 0xA86B3E,
    "arauco_cinza_cristal": 0x9E9E9E,
    "guararapes_freijo_puro": 0x9C6236,
    "guararapes_azul_petroleo": 0x1B3B48,
    "generico_preto_tx": 0x212121,
    "mdf_cru": 0xD2B48C
};

async function carregarCatalogoMateriais() {
    const resp = await fetch("/api/catalogo_materiais");
    const dados = await resp.json();
    catalogoMateriaisCache = dados.materiais || [];

    document.querySelectorAll(".combo-mdf").forEach(select => {
        select.innerHTML = "";
        catalogoMateriaisCache.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.innerText = `[${m.marca}] ${m.nome}`;
            select.appendChild(opt);
        });
    });
}

function alternarPalcoAmplo() {
    document.body.classList.toggle("palco-amplo");
    const ativo = document.body.classList.contains("palco-amplo");
    document.getElementById("btn_palco_amplo").classList.toggle("ativo", ativo);
    setTimeout(() => window.dispatchEvent(new Event("resize")), 50);
}

function alternarMenuMateriais() {
    const modal = document.getElementById("painel_flutuante_materiais");
    const visivel = modal.style.display === "block";
    modal.style.display = visivel ? "none" : "block";
    document.getElementById("btn_menu_materiais").classList.toggle("ativo", !visivel);
    if (!visivel && moduloAtivo) sincronizarMenuMateriaisComModulo(moduloAtivo);
}

function sincronizarMenuMateriaisComModulo(mod) {
    document.getElementById("lbl_mod_mat").innerText = `#${mod.id_modulo}`;
    const z = (mod.parametros && mod.parametros.zonas_materiais) || {};
    const matC = mod.parametros.material_caixaria || "generico_branco_tx";
    const matF = mod.parametros.material_frentes || "generico_branco_tx";

    document.getElementById("mat_zona_caixaria").value = z.cor_caixaria || matC;
    document.getElementById("mat_zona_frentes").value = z.cor_frentes || matF;
    document.getElementById("mat_zona_internos").value = z.cor_internos || matC;
    document.getElementById("mat_zona_fgav").value = z.cor_fundo_gaveta || "generico_branco_tx";
    document.getElementById("mat_zona_fcosta").value = z.cor_fundo_costa || "generico_branco_tx";

    document.getElementById("fita_zona_caixaria").value = z.fita_frontal_caixaria || z.cor_caixaria || matC;
    document.getElementById("fita_zona_frentes").value = z.fita_frentes || z.cor_frentes || matF;
    document.getElementById("fita_zona_internos").value = z.fita_internos || z.cor_internos || matC;
}

function selecionarPecaParaPintura(pecaDict) {
    pecaIndividualSelecionada = pecaDict;
    document.getElementById("painel_flutuante_materiais").style.display = "block";
    document.getElementById("btn_menu_materiais").classList.add("ativo");

    document.getElementById("nome_peca_pintor").innerText =
        `🪵 ${pecaDict.nome_comercial} (${pecaDict.dimensoes_2d_planificadas.largura_x}x${pecaDict.dimensoes_2d_planificadas.altura_y}mm)`;
    document.getElementById("mat_peca_ind").value = pecaDict.material || "generico_branco_tx";
    document.getElementById("fita_peca_ind").value = pecaDict.cor_fita_borda || pecaDict.material || "generico_branco_tx";

    const fb = pecaDict.fitas_borda || {};
    document.getElementById("chk_fita_base").checked = !!fb.base;
    document.getElementById("chk_fita_topo").checked = !!fb.topo;
    document.getElementById("chk_fita_esq").checked = !!fb.esquerda;
    document.getElementById("chk_fita_dir").checked = !!fb.direita;
}

async function aplicarZonasMateriaisModulo() {
    if (!moduloAtivo) return;
    const zonas = {
        cor_caixaria: document.getElementById("mat_zona_caixaria").value,
        cor_frentes: document.getElementById("mat_zona_frentes").value,
        cor_internos: document.getElementById("mat_zona_internos").value,
        cor_fundo_gaveta: document.getElementById("mat_zona_fgav").value,
        cor_fundo_costa: document.getElementById("mat_zona_fcosta").value,
        fita_frontal_caixaria: document.getElementById("fita_zona_caixaria").value,
        fita_frentes: document.getElementById("fita_zona_frentes").value,
        fita_internos: document.getElementById("fita_zona_internos").value
    };

    const resp = await fetch("/api/modulo/pintar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_modulo: moduloAtivo.id_modulo, zonas_materiais: zonas })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        await carregarEstadoAmbiente();
    }
}

async function aplicarPinturaPecaIndividual() {
    if (!moduloAtivo || !pecaIndividualSelecionada) return;
    const overridePeca = {
        nome_comercial: pecaIndividualSelecionada.nome_comercial,
        material: document.getElementById("mat_peca_ind").value,
        cor_fita_borda: document.getElementById("fita_peca_ind").value,
        fitas_borda: {
            base: document.getElementById("chk_fita_base").checked,
            topo: document.getElementById("chk_fita_topo").checked,
            esquerda: document.getElementById("chk_fita_esq").checked,
            direita: document.getElementById("chk_fita_dir").checked
        }
    };

    const resp = await fetch("/api/modulo/pintar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_modulo: moduloAtivo.id_modulo, override_peca: overridePeca })
    });
    const dados = await resp.json();
    if (dados.sucesso) {
        moduloAtivo = dados.modulo;
        await carregarEstadoAmbiente();
    }
}

async function resetarPinturasIndividuais() {
    if (!moduloAtivo) return;
    await fetch("/api/modulo/pintar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_modulo: moduloAtivo.id_modulo, resetar_pecas_individuais: true })
    });
    await carregarEstadoAmbiente();
}