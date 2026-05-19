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
            }
        });
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
        
        try {
            const response = await fetch('/api/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ codigo: code })
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

            if (result.tabla) {
                let tablaStr = "=== FUNCIONES ===\n";
                result.tabla.funciones?.forEach(f => {
                    tablaStr += `- ${f.tipo_retorno || f.tipo} ${f.nombre}(${f.params || f.parametros || ''}) [Ámbito: ${f.ambito || 'global'}]\n`;
                });
                tablaStr += "\n=== VARIABLES ===\n";
                result.tabla.variables?.forEach(v => {
                    tablaStr += `- ${v.tipo} ${v.nombre} [Clase: ${v.clase}] (Ámbito: ${v.ambito}) ${v.usado ? '' : '[NO USADA]'}\n`;
                });
                document.getElementById('out-sym').textContent = tablaStr;
            } else {
                document.getElementById('out-sym').textContent = 'Error al generar Tabla de Símbolos';
            }

            let echoLog = '--- INICIO DE COMPILACIÓN ---\n' + (result.log || '');
            if (result.tokens && result.tokens.length > 0) {
                echoLog = '=== TOKENS ENCONTRADOS ===\n' + result.tokens.map(t => `(${t[0]}, '${t[1]}')`).join('\n') + '\n\n' + echoLog;
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
