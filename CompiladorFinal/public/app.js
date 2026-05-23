document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('code-editor');
    const compileBtn = document.getElementById('btn-compile');
    const statusInd = document.getElementById('compile-status');
    const canvas = document.getElementById('canvas');
    const lineNumbers = document.getElementById('code-line-numbers');
    let draggedType = null;

    const saveSourceButton = document.getElementById('btn-save');
    if (saveSourceButton) {
        saveSourceButton.textContent = 'Guardar Codigo';
        saveSourceButton.title = 'Guardar codigo fuente';
    }

    const updateLineNumbers = () => {
        if (!editor || !lineNumbers) return;
        const count = Math.max(1, editor.value.split('\n').length);
        lineNumbers.textContent = Array.from({ length: count }, (_, index) => index + 1).join('\n');
        lineNumbers.scrollTop = editor.scrollTop;
    };

    editor?.addEventListener('input', updateLineNumbers);
    editor?.addEventListener('scroll', () => {
        if (lineNumbers) lineNumbers.scrollTop = editor.scrollTop;
    });

    const insertEditorText = (text) => {
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.slice(0, start) + text + editor.value.slice(end);
        editor.selectionStart = editor.selectionEnd = start + text.length;
        updateLineNumbers();
    };

    editor?.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            e.preventDefault();
            insertEditorText('    ');
            return;
        }
        if (e.key === 'Enter') {
            e.preventDefault();
            const beforeCursor = editor.value.slice(0, editor.selectionStart);
            const currentLine = beforeCursor.split('\n').pop() || '';
            const baseIndent = (currentLine.match(/^\s*/) || [''])[0];
            const extraIndent = /\{\s*$/.test(currentLine) ? '    ' : '';
            insertEditorText('\n' + baseIndent + extraIndent);
        }
    });

    document.querySelectorAll('.tool-btn').forEach(btn => {
        const icon = btn.querySelector('.icon');
        if (icon) {
            icon.textContent = '';
            icon.className = `tool-shape ${btn.dataset.type}-preview`;
        }
    });
    
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

    const resizeCanvasToContent = () => {
        if (!canvas || !canvasWrapper) return;
        const blocks = [...canvas.querySelectorAll('.flow-block')];
        const height = Math.max(canvasWrapper.clientHeight, blocks.length * 150 + 180);
        const width = Math.max(canvasWrapper.clientWidth, ...blocks.map(b => b.scrollWidth + 180), 760);
        canvas.style.minHeight = `${height}px`;
        canvas.style.minWidth = `${width}px`;
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
            document.getElementById('out-filename').value = file.name.replace(/\.c$/i, '');
            updateLineNumbers();
            document.querySelector('[data-view="code"]').click(); // switch to code view
        };
        reader.readAsText(file);
    });

    document.getElementById('btn-clean')?.addEventListener('click', () => {
        editor.value = 'int main() {\n    \n    return 0;\n}';
        updateLineNumbers();
        canvas.innerHTML = '<div class="empty-msg">Arrastra bloques aquí para armar tu programa...</div>';
        document.querySelectorAll('.tab-pane pre code, .table-container').forEach(el => el.innerHTML = 'Esperando compilación...');
        statusInd.textContent = 'Listo';
        statusInd.className = 'status-indicator';
        document.getElementById('out-filename').value = '';
        document.getElementById('out-directory').value = '';
        zoomLevel = 1; translateX = 0; translateY = 0; updateTransform();
    });

    document.getElementById('btn-save')?.addEventListener('click', (event) => {
        event.stopImmediatePropagation();
        const blob = new Blob([editor.value], { type: 'text/x-csrc' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const filename = (document.getElementById('out-filename').value || 'noname').replace(/\.c$/i, '');
        a.download = filename + '.c';
        a.click();
        URL.revokeObjectURL(url);
        /*
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
        */
    });

    // Interactive Terminal
    let termInterval = null;
    async function startTerminalPoll(ejecutable) {
        if(termInterval) clearInterval(termInterval);
        
        const termOut = document.getElementById('term-output');
        const termInRow = document.getElementById('term-input-row');
        termOut.textContent = 'Iniciando proceso...\n';
        termInRow.style.display = 'none';

        try {
            const runResponse = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ejecutable })
            });
            if (!runResponse.ok) {
                const runError = await runResponse.json().catch(() => ({}));
                throw new Error(runError.error || 'No se pudo iniciar el ejecutable.');
            }
            termInRow.style.display = 'flex';
            document.getElementById('term-input').focus();
            
            termInterval = setInterval(async () => {
                try {
                    const res = await fetch('/api/stdout');
                    const data = await res.json();
                    if(data.salida) {
                        termOut.textContent += data.salida;
                        termOut.scrollTop = termOut.scrollHeight;
                    }
                    if(data.estado === 'finished' || data.estado === 'idle') {
                        clearInterval(termInterval);
                        termInRow.style.display = 'none';
                        termOut.textContent += data.estado === 'idle'
                            ? '\n\n[No hay proceso en ejecucion]'
                            : '\n\n[Proceso finalizado]';
                        termOut.scrollTop = termOut.scrollHeight;
                    }
                } catch(e) {}
            }, 300); // Polling rapido
        } catch(e) {
            termOut.textContent += '\nError al iniciar: ' + e;
        }
    }

    document.getElementById('term-input')?.addEventListener('keypress', async (e) => {
        if(e.key === 'Enter') {
            const text = e.target.value;
            e.target.value = '';
            try {
                await fetch('/api/stdin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ texto: text })
                });
            } catch(e) {}
        }
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
        resizeCanvasToContent();
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
                title = 'Asignar';
                bodyHTML = `
                    <div class="block-body">
                        <select class="block-input short" name="tipo">
                            <option value="int">int</option>
                            <option value="float">float</option>
                            <option value="string">string</option>
                            <option value="">(none)</option>
                        </select>
                        <input type="text" class="block-input short" placeholder="A" name="var">
                        &lt;-
                        <input type="text" class="block-input" placeholder="B+i" name="exp">
                    </div>`;
                break;
            case 'if':
                title = 'if';
                bodyHTML = `
                    <div class="block-body">
                        <input type="text" class="block-input" placeholder="A>B" name="cond">
                    </div>`;
                break;
            case 'while':
                title = 'while';
                bodyHTML = `
                    <div class="block-body">
                        <input type="text" class="block-input" placeholder="N<10" name="cond">
                    </div>`;
                break;
            case 'for':
                title = 'for';
                bodyHTML = `
                    <div class="block-body" style="display:flex; flex-direction:column; gap:4px;">
                        <div>Init: <input type="text" class="block-input" placeholder="int i = 0" name="init"></div>
                        <div>Cond: <input type="text" class="block-input" placeholder="i < 10" name="cond"></div>
                        <div>Inc: <input type="text" class="block-input" placeholder="i++" name="inc"></div>
                    </div>`;
                break;
            case 'print':
                title = 'print';
                bodyHTML = `
                    <div class="block-body">
                        <input type="text" class="block-input" placeholder="'Hola !'" name="val">
                    </div>`;
                break;
            case 'input':
                title = 'Leer';
                bodyHTML = `
                    <div class="block-body">
                        <input type="text" class="block-input short" placeholder="Dato1" name="var">
                    </div>`;
                break;
            case 'else':
                title = 'Si No (Else)';
                bodyHTML = `<div style="text-align:center;font-size:0.8rem;opacity:0.7">Rama Falsa</div>`;
                break;
            case 'end':
                title = 'Fin Bloque';
                bodyHTML = `<div style="text-align:center;font-size:0.8rem;opacity:0.7">Cierra if/while/for anterior</div>`;
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
            resizeCanvasToContent();
            generateCodeFromCanvas();
        });

        block.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('input', generateCodeFromCanvas);
        });

        return block;
    }

    function generateCodeFromCanvas() {
        let code = '#include <stdio.h>\nint main() {\n';
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
                const val = block.querySelector('[name="val"]').value || '""';
                code += `${indent}println(${val});\n`;
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
            else if (type === 'for') {
                const init = block.querySelector('[name="init"]').value || 'int i = 0';
                const cond = block.querySelector('[name="cond"]').value || 'i < 1';
                const inc = block.querySelector('[name="inc"]').value || 'i++';
                code += `${indent}for (${init}; ${cond}; ${inc}) {\n`;
                openBlocks.push('for');
                indent += '    ';
            }
            else if (type === 'else') {
                if (openBlocks.length > 0 && openBlocks[openBlocks.length - 1] === 'if') {
                    indent = indent.slice(0, -4);
                    code += `${indent}} else {\n`;
                    indent += '    ';
                    openBlocks[openBlocks.length - 1] = 'else';
                }
            }
            else if (type === 'end') {
                if (openBlocks.length > 0) {
                    indent = indent.slice(0, -4);
                    code += `${indent}}\n`;
                    openBlocks.pop();
                }
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
        updateLineNumbers();
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
            } else if (line.startsWith('for')) {
                const match = line.match(/for\s*\((.*?);(.*?);(.*?)\)/);
                if (match) {
                    const block = createBlock('for');
                    block.querySelector('[name="init"]').value = match[1].trim();
                    block.querySelector('[name="cond"]').value = match[2].trim();
                    block.querySelector('[name="inc"]').value = match[3].trim();
                    canvas.appendChild(block);
                }
            } else if (line.startsWith('println') || line.startsWith('print') || line.startsWith('printf')) {
                const match = line.match(/(println|print|printf)\s*\((.*?)\)/);
                if (match) {
                    const block = createBlock('print');
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
                const assignMatch = line.match(/^(?:(int|float|string)\s+)?([a-zA-Z_]\w*)\s*=\s*(.*?);$/);
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
        resizeCanvasToContent();
    }

    resizeCanvasToContent();
    updateLineNumbers();

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
                
                /*
                let tablaStr = "";
                result.tabla.funciones?.forEach(f => {
                    tablaStr += `- ${f.tipo_retorno || f.tipo} ${f.nombre}(${f.params || f.parametros || ''}) [Ámbito: ${f.ambito || 'global'}]\n`;
                });
                tablaStr += "\n=== VARIABLES ===\n";
                result.tabla.variables?.forEach(v => {
                    tablaStr += `- ${v.tipo} ${v.nombre} [Clase: ${v.clase}] (Ámbito: ${v.ambito}) ${v.usado ? '' : '[NO USADA]'}\n`;
                });
                // we'll append tablaStr to Echo Log below
                result._tablaStr = tablaStr;
                */
            } else {
                document.getElementById('out-sym').innerHTML = 'Error al generar Tabla de Símbolos';
            }

            let echoLog = buildCompilationLog(result);
            /*
            if (false) {
                echoLog += '\n\n' + result._tablaStr;
            }

            if (!result.ok && result.errores?.length > 0) {
                echoLog += '\n\n--- ERRORES SEMÁNTICOS ---\n' + result.errores.join('\n');
            }
            */
            document.getElementById('out-echo').textContent = echoLog;
            
            // Si la compilacion y ensamblado fue exitosa, correr en terminal interactiva
            if (result.ejecutable) {
                startTerminalPoll(result.ejecutable);
            } else {
                document.getElementById('term-output').textContent = result.ok
                    ? 'Compilacion finalizada, pero no se recibio ruta de ejecutable.'
                    : buildUserDiagnostics(result);
            }
            
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

    function buildCompilationLog(result) {
        const lines = [];
        lines.push('=== COMPILACION ===');
        lines.push(`Estado: ${result.ok ? 'Correcta' : 'Con errores'}`);
        lines.push('');

        if (result.diagnosticos?.length) {
            lines.push(buildUserDiagnostics(result));
            lines.push('');
        } else {
            lines.push('Errores: ninguno');
            lines.push('');
        }

        if (result.avisos?.length) {
            lines.push(`Advertencias (${result.avisos.length}):`);
            result.avisos.forEach((aviso, index) => lines.push(`${index + 1}. ${aviso}`));
            lines.push('');
        }

        if (result.ejecutable) {
            lines.push(`Ejecutable: ${result.ejecutable}`);
            lines.push('');
        }

        lines.push('=== FASES / NASM ===');
        lines.push(result.log || 'Sin mensajes de compilacion.');
        return lines.join('\n');
    }

    function buildUserDiagnostics(result) {
        const diagnosticos = result.diagnosticos || [];
        if (!diagnosticos.length) {
            return (result.errores || []).length
                ? `Errores:\n${result.errores.join('\n')}`
                : 'No hay diagnosticos para mostrar.';
        }

        const lines = ['=== DIAGNOSTICOS ==='];
        diagnosticos.forEach((item, index) => {
            const ubicacion = item.linea
                ? `Linea ${item.linea}`
                : 'Sin linea';
            lines.push(`${index + 1}. ${ubicacion}: ${item.mensaje}`);
            if (item.fuente) lines.push(`   > ${item.fuente}`);
        });
        return lines.join('\n');
    }
});
