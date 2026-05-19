document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('code-editor');
    const compileBtn = document.getElementById('btn-compile');
    const statusInd = document.getElementById('compile-status');
    const canvas = document.getElementById('canvas');
    let draggedType = null;
    
    // Setup View Tabs
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.view-pane').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.view + '-view').classList.add('active');
            
            if (btn.dataset.view === 'code') {
                const hasBlocks = document.querySelectorAll('.flow-block:not(.start)').length > 0;
                if (hasBlocks) {
                    generateCodeFromCanvas();
                }
            } else if (btn.dataset.view === 'visual') {
                generateCanvasFromCode();
            }
        });
    });

    // Zoom and Pan Logic
    let zoomLevel = 1;
    let isDragging = false;
    let startX, startY;
    let translateX = 0;
    let translateY = 0;
    const canvasWrapper = document.getElementById('canvas-wrapper');

    const updateTransform = () => {
        if (!canvas) return;
        canvas.style.transform = `translate(${translateX}px, ${translateY}px) scale(${zoomLevel})`;
        const zl = document.getElementById('zoom-level');
        if (zl) zl.textContent = Math.round(zoomLevel * 100) + '%';
    };

    document.getElementById('zoom-in')?.addEventListener('click', () => { zoomLevel = Math.min(zoomLevel + 0.1, 2); updateTransform(); });
    document.getElementById('zoom-out')?.addEventListener('click', () => { zoomLevel = Math.max(zoomLevel - 0.1, 0.5); updateTransform(); });
    document.getElementById('zoom-reset')?.addEventListener('click', () => { zoomLevel = 1; translateX = 0; translateY = 0; updateTransform(); });

    canvasWrapper?.addEventListener('wheel', (e) => {
        if (e.ctrlKey) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            zoomLevel = Math.max(0.5, Math.min(zoomLevel + delta, 2));
            updateTransform();
        }
    });

    canvasWrapper?.addEventListener('mousedown', (e) => {
        if (e.target === canvasWrapper || e.target === canvas) {
            isDragging = true;
            startX = e.clientX - translateX;
            startY = e.clientY - translateY;
            canvasWrapper.style.cursor = 'grabbing';
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        updateTransform();
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
        if (canvasWrapper) canvasWrapper.style.cursor = 'grab';
    });

    // File buttons Logic
    document.getElementById('btn-load')?.addEventListener('click', () => {
        document.getElementById('file-upload').click();
    });

    document.getElementById('file-upload')?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            editor.value = ev.target.result;
            document.querySelector('[data-view="code"]').click(); // switch to code view
        };
        reader.readAsText(file);
    });

    document.getElementById('btn-clean')?.addEventListener('click', () => {
        editor.value = 'int main() {\n    \n    return 0;\n}';
        canvas.innerHTML = '<div class="empty-msg">Arrastra bloques aquí para armar tu programa...</div>';
        document.querySelectorAll('.tab-pane pre code, .table-container').forEach(el => el.innerHTML = 'Esperando compilación...');
        statusInd.textContent = 'Listo';
        statusInd.className = 'status-indicator';
        document.getElementById('out-filename').value = '';
        document.getElementById('out-directory').value = '';
        zoomLevel = 1; translateX = 0; translateY = 0; updateTransform();
    });

    document.getElementById('btn-save')?.addEventListener('click', () => {
        let content = "=== RESULTADOS DE COMPILACIÓN ===\n\n";
        content += "[ASM]\n" + document.getElementById('out-asm').textContent + "\n\n";
        content += "[AST]\n" + document.getElementById('out-ast').textContent + "\n\n";
        content += "[LOG]\n" + document.getElementById('out-echo').textContent + "\n\n";
        
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (document.getElementById('out-filename').value || 'noname') + '_resultados.txt';
        a.click();
        URL.revokeObjectURL(url);
    });

    // Results Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });

    // Drag and Drop Logic
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('dragstart', (e) => {
            draggedType = btn.dataset.type;
        });
    });

    canvas.addEventListener('dragover', (e) => {
        e.preventDefault();
        canvas.style.background = 'rgba(0, 0, 0, 0.4)';
    });

    canvas.addEventListener('dragleave', () => {
        canvas.style.background = 'rgba(0, 0, 0, 0.2)';
    });

    canvas.addEventListener('drop', (e) => {
        e.preventDefault();
        canvas.style.background = 'rgba(0, 0, 0, 0.2)';
        if (!draggedType) return;

        const emptyMsg = canvas.querySelector('.empty-msg');
        if (emptyMsg) emptyMsg.remove();

        const block = createBlock(draggedType);
        canvas.appendChild(block);
        draggedType = null;
        generateCodeFromCanvas();
    });

    function createBlock(type) {
        const block = document.createElement('div');
        block.className = `flow-block ${type}`;
        block.dataset.type = type;

        let title = '';
        let bodyHTML = '';

        switch(type) {
            case 'start':
                title = 'Inicio / Fin';
                bodyHTML = `<div style="text-align:center;font-size:0.8rem;opacity:0.7">Contenedor Principal</div>`;
                break;
            case 'assign':
                title = 'Asignación';
                bodyHTML = `
                    <div class="block-body">
                        <select class="block-input short" name="tipo">
                            <option value="int">int</option>
                            <option value="float">float</option>
                            <option value="">(ninguno)</option>
                        </select>
                        <input type="text" class="block-input short" placeholder="var" name="var">
                        =
                        <input type="text" class="block-input" placeholder="expresión" name="exp">
                    </div>`;
                break;
            case 'if':
                title = 'Decisión (Si)';
                bodyHTML = `
                    <div class="block-body">
                        Si <input type="text" class="block-input" placeholder="condición" name="cond">
                    </div>`;
                break;
            case 'while':
                title = 'Bucle (Mientras)';
                bodyHTML = `
                    <div class="block-body">
                        Mientras <input type="text" class="block-input" placeholder="condición" name="cond">
                    </div>`;
                break;
            case 'print':
                title = 'Salida (Imprimir)';
                bodyHTML = `
                    <div class="block-body">
                        <select class="block-input short" name="func">
                            <option value="println" selected>println</option>
                            <option value="print">print</option>
                            <option value="printf">printf</option>
                        </select>
                        <input type="text" class="block-input" placeholder='"Hola"' name="val">
                    </div>`;
                break;
            case 'input':
                title = 'Entrada (Leer)';
                bodyHTML = `
                    <div class="block-body">
                        scanf("%d", <input type="text" class="block-input short" placeholder="var" name="var">);
                    </div>`;
                break;
        }

        block.innerHTML = `
            <div class="shape-bg"></div>
            <div class="block-content">
                <div class="block-header">
                    ${title} <button class="delete-btn">✖</button>
                </div>
                ${bodyHTML}
            </div>
        `;

        block.querySelector('.delete-btn').addEventListener('click', () => {
            block.remove();
            generateCodeFromCanvas();
        });

        block.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('input', generateCodeFromCanvas);
        });

        return block;
    }

    function generateCodeFromCanvas() {
        let code = 'int main() {\n';
        let indent = '    ';
        let openBlocks = [];

        document.querySelectorAll('.flow-block').forEach(block => {
            const type = block.dataset.type;
            
            if (type === 'start') {
                // Ignore start block for code gen inside main
                return;
            }

            if (type === 'assign') {
                const tipo = block.querySelector('[name="tipo"]').value;
                const v = block.querySelector('[name="var"]').value || 'temp';
                const exp = block.querySelector('[name="exp"]').value || '0';
                code += `${indent}${tipo ? tipo + ' ' : ''}${v} = ${exp};\n`;
            }
            else if (type === 'print') {
                const func = block.querySelector('[name="func"]').value;
                const val = block.querySelector('[name="val"]').value || '""';
                code += `${indent}${func}(${val});\n`;
            }
            else if (type === 'input') {
                const v = block.querySelector('[name="var"]').value || 'temp';
                code += `${indent}scanf("%d", ${v});\n`;
            }
            else if (type === 'if') {
                const cond = block.querySelector('[name="cond"]').value || '1';
                code += `${indent}if (${cond}) {\n`;
                openBlocks.push('if');
                indent += '    ';
            }
            else if (type === 'while') {
                const cond = block.querySelector('[name="cond"]').value || '1';
                code += `${indent}while (${cond}) {\n`;
                openBlocks.push('while');
                indent += '    ';
            }
        });

        // Close any open blocks (simplification: visual blocks apply sequentially for this demo)
        // In a real flowchart, IFs would have "true/false" branches. For now we auto-close blocks at the end.
        while (openBlocks.length > 0) {
            indent = indent.slice(0, -4);
            code += `${indent}}\n`;
            openBlocks.pop();
        }

        code += '    return 0;\n}';
        editor.value = code;
    }

    function generateCanvasFromCode() {
        const code = editor.value;
        const mainMatch = code.match(/int\s+main\s*\(\)\s*\{([\s\S]*?)return\s+0;/);
        if (!mainMatch) return;
        
        let body = mainMatch[1];
        
        // Limpiar canvas
        canvas.innerHTML = '';
        canvas.appendChild(createBlock('start'));
        
        // Regex simplificado para las lineas
        const lines = body.split('\n').map(l => l.trim()).filter(l => l);
        
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];
            if (line === '}' || line === '') continue;
            
            if (line.startsWith('if')) {
                const match = line.match(/if\s*\((.*?)\)/);
                if (match) {
                    const block = createBlock('if');
                    block.querySelector('[name="cond"]').value = match[1];
                    canvas.appendChild(block);
                }
            } else if (line.startsWith('while')) {
                const match = line.match(/while\s*\((.*?)\)/);
                if (match) {
                    const block = createBlock('while');
                    block.querySelector('[name="cond"]').value = match[1];
                    canvas.appendChild(block);
                }
            } else if (line.startsWith('println') || line.startsWith('print') || line.startsWith('printf')) {
                const match = line.match(/(println|print|printf)\s*\((.*?)\)/);
                if (match) {
                    const block = createBlock('print');
                    block.querySelector('[name="func"]').value = match[1];
                    block.querySelector('[name="val"]').value = match[2];
                    canvas.appendChild(block);
                }
            } else if (line.startsWith('scanf')) {
                const match = line.match(/scanf\s*\(\s*".*?"\s*,\s*(.*?)\)/);
                if (match) {
                    const block = createBlock('input');
                    block.querySelector('[name="var"]').value = match[1];
                    canvas.appendChild(block);
                }
            } else {
                // Asignacion
                const assignMatch = line.match(/^(?:(int|float)\s+)?([a-zA-Z_]\w*)\s*=\s*(.*?);$/);
                if (assignMatch) {
                    const block = createBlock('assign');
                    if (assignMatch[1]) block.querySelector('[name="tipo"]').value = assignMatch[1];
                    else block.querySelector('[name="tipo"]').value = '';
                    block.querySelector('[name="var"]').value = assignMatch[2];
                    block.querySelector('[name="exp"]').value = assignMatch[3];
                    canvas.appendChild(block);
                }
            }
        }
    }

    // Compile action
    compileBtn.addEventListener('click', async () => {
        const activeView = document.querySelector('.view-btn.active').dataset.view;
        const hasBlocks = document.querySelectorAll('.flow-block:not(.start)').length > 0;
        
        if (activeView === 'visual' && hasBlocks) {
            generateCodeFromCanvas(); // Solo sincronizar si estamos armando bloques
        }
        
        const code = editor.value;
        if (!code.trim()) return;
        
        compileBtn.innerHTML = '⏳ Compilando...';
        compileBtn.disabled = true;
        statusInd.textContent = 'Compilando...';
        statusInd.className = 'status-indicator';
        
        const filename = document.getElementById('out-filename')?.value || 'noname';
        const directory = document.getElementById('out-directory')?.value || './';
        
        try {
            const response = await fetch('/api/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ codigo: code, filename, directory })
            });
            
            const result = await response.json();
            
            if (result.ok) {
                statusInd.textContent = 'Éxito';
                statusInd.className = 'status-indicator success';
            } else {
                statusInd.textContent = 'Errores';
                statusInd.className = 'status-indicator error';
            }
            
            // Populate results
            document.getElementById('out-asm').textContent = result.asm || 'Sin salida NASM';
            document.getElementById('out-ruby').textContent = result.ruby || 'Sin traducción a Ruby';
            document.getElementById('out-py').textContent = result.python || 'Sin traducción a Python';
            document.getElementById('out-rust').textContent = result.rust || 'Sin traducción a Rust';
            
            if (result.ast_json) {
                document.getElementById('out-ast').textContent = JSON.stringify(result.ast_json, null, 2);
            } else {
                document.getElementById('out-ast').textContent = 'Error al generar AST';
            }

            if (result.tokens) {
                let tokTable = `<table class="data-table"><thead><tr><th>Tipo</th><th>Valor</th></tr></thead><tbody>`;
                result.tokens.forEach(t => {
                    tokTable += `<tr><td>${t[0]}</td><td>${t[1]}</td></tr>`;
                });
                tokTable += `</tbody></table>`;
                document.getElementById('out-tokens').innerHTML = tokTable;
            } else {
                document.getElementById('out-tokens').innerHTML = 'Error al generar Tokens';
            }

            if (result.tabla) {
                // Table visual representation
                let tablaHTML = `<div class="table-title">Funciones</div><table class="data-table"><thead><tr><th>Nombre</th><th>Tipo Retorno</th><th>Clase</th><th>Parámetros</th></tr></thead><tbody>`;
                result.tabla.funciones?.forEach(f => {
                    const params = (f.parametros || []).map(p => `${p.tipo} ${p.nombre}`).join(', ') || '(ninguno)';
                    tablaHTML += `<tr><td>${f.nombre}</td><td>${f.tipo_retorno || f.tipo}</td><td>${f.clase || '-'}</td><td>${params}</td></tr>`;
                });
                tablaHTML += `</tbody></table><br><div class="table-title">Variables</div><table class="data-table"><thead><tr><th>Nombre</th><th>Tipo</th><th>Ámbito</th><th>Clase</th></tr></thead><tbody>`;
                result.tabla.variables?.forEach(v => {
                    tablaHTML += `<tr><td>${v.nombre}</td><td>${v.tipo}</td><td>${v.ambito}</td><td>${v.clase}</td></tr>`;
                });
                tablaHTML += `</tbody></table>`;
                document.getElementById('out-sym').innerHTML = tablaHTML;
                
                // Echo log representation
                let tablaStr = "=== FUNCIONES ===\n";
                result.tabla.funciones?.forEach(f => {
                    tablaStr += `- ${f.tipo_retorno || f.tipo} ${f.nombre}(${f.params || f.parametros || ''}) [Ámbito: ${f.ambito || 'global'}]\n`;
                });
                tablaStr += "\n=== VARIABLES ===\n";
                result.tabla.variables?.forEach(v => {
                    tablaStr += `- ${v.tipo} ${v.nombre} [Clase: ${v.clase}] (Ámbito: ${v.ambito}) ${v.usado ? '' : '[NO USADA]'}\n`;
                });
                // we'll append tablaStr to Echo Log below
                result._tablaStr = tablaStr;
            } else {
                document.getElementById('out-sym').innerHTML = 'Error al generar Tabla de Símbolos';
            }

            let echoLog = '--- INICIO DE COMPILACIÓN ---\n' + (result.log || '');
            if (result.tokens && result.tokens.length > 0) {
                echoLog = '=== TOKENS ENCONTRADOS ===\n' + result.tokens.map(t => `(${t[0]}, '${t[1]}')`).join('\n') + '\n\n' + echoLog;
            }
            if (result._tablaStr) {
                echoLog += '\n\n' + result._tablaStr;
            }

            if (!result.ok && result.errores?.length > 0) {
                echoLog += '\n\n--- ERRORES SEMÁNTICOS ---\n' + result.errores.join('\n');
            }
            document.getElementById('out-echo').textContent = echoLog;
            
        } catch (error) {
            console.error(error);
            statusInd.textContent = 'Error Servidor';
            statusInd.className = 'status-indicator error';
            document.getElementById('out-echo').textContent = 'Error: ' + error.message;
        } finally {
            compileBtn.innerHTML = '🚀 Compilar y Ejecutar';
            compileBtn.disabled = false;
        }
    });
});
