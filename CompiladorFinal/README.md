# Compilador — Proyecto Final

## Archivos

| Archivo | Descripción |
|---|---|
| `lexico.py` | Análisis léxico: tokeniza el código fuente |
| `sintactico.py` | Análisis sintáctico: construye el AST |
| `semantico.py` | Análisis semántico: tabla de símbolos, tipos, errores |
| `node.py` | Todos los nodos del AST + generación de código |
| `main.py` | Orquestador: función `compilar_codigo()` para la GUI |

## API para la interfaz gráfica

```python
from main import compilar_codigo

resultado = compilar_codigo(codigo_fuente)

resultado["tokens"]   # lista de (tipo, valor)
resultado["ast_json"] # AST serializado (dict)
resultado["tabla"]    # tabla de símbolos (dict)
resultado["errores"]  # errores semánticos (list[str])
resultado["avisos"]   # advertencias (list[str])
resultado["ruby"]     # traducción a Ruby (str)
resultado["python"]   # traducción a Python (str)
resultado["rust"]     # traducción a Rust (str)
resultado["asm"]      # código ensamblador NASM (str)
resultado["log"]      # log completo de compilación (str)
resultado["ok"]       # True si no hay errores semánticos
```

## Lenguaje soportado

- Tipos: `int`, `float`, `void`
- Funciones con parámetros y retorno
- Declaraciones y reasignaciones de variables
- Operadores: `+`, `-`, `*`, `/`, `=`, `<`, `>`, `<=`, `>=`, `==`, `!=`
- Control de flujo: `if/else`, `while`, `for` (con `i++` / `i--`)
- Salida: `println(...)`, `print(...)`, `cout <<`, `printf(...)`, `puts(...)`
- Entrada: `scanf("%d", variable)`
- Comentarios: `// línea` y `/* bloque */`

## Traducción y generación

- **Ruby**, **Python**, **Rust** — via `traducirRuby()`, `traducirPy()`, `traducirRust()`
- **Ensamblador NASM ELF32** — via `generarCodigo()`  
  Enteros: registros de propósito general (eax/ebx)  
  Floats: FPU x87 (ST0..ST7)  
  Printf: convención cdecl, linked con GCC + libc
