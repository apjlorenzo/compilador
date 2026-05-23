"""
main.py — Orquestador del compilador.

Expone la función compilar_codigo(codigo) que devuelve un diccionario
con todas las fases, listo para ser consumido por la interfaz gráfica:

    {
        "tokens"      : [(tipo, valor), ...],
        "ast_json"    : {...},           # AST serializado
        "tabla"       : {...},           # tabla de símbolos serializada
        "errores"     : [...],           # errores semánticos (str)
        "avisos"      : [...],           # advertencias semánticas (str)
        "ruby"        : "...",           # traducción a Ruby
        "python"      : "...",           # traducción a Python
        "rust"        : "...",           # traducción a Rust
        "asm"         : "...",           # código ensamblador NASM
        "log"         : "...",           # log completo de la compilación
        "ok"          : True | False,    # False si hay errores semánticos
    }

También se puede ejecutar directamente (python main.py) para ver
la salida completa en consola con el código de ejemplo.
"""

import json
import io
import subprocess
import os
import shutil
import re

from lexico    import identificar_tokens
from sintactico import Parser, imprimir_ast
from semantico  import AnalizadorSemantico, imprimir_resultado_semantico
from node import (
    NodoAsignacion, NodoPrint, NodoImprimir, NodoWhile, NodoFor, NodoIf,
    NodoLlamadaFuncion, NodoRetorno,
)


def optimizar_ast(ast):
    """Aplica optimizaciones locales al AST y devuelve cuantas expresiones cambio."""
    cambios = 0

    def opt_expr(expr):
        nonlocal cambios
        if hasattr(expr, "optimizar"):
            nuevo = expr.optimizar()
            if nuevo is not expr:
                cambios += 1
            return nuevo
        return expr

    def opt_bloque(instrucciones):
        for inst in instrucciones or []:
            if hasattr(inst, "expresion"):
                inst.expresion = opt_expr(inst.expresion)
            if isinstance(inst, NodoRetorno):
                inst.expresion = opt_expr(inst.expresion)
            if isinstance(inst, NodoImprimir):
                inst.argumentos = [opt_expr(arg) for arg in inst.argumentos]
            if isinstance(inst, (NodoWhile, NodoIf)) and hasattr(inst, "condicion"):
                inst.condicion = opt_expr(inst.condicion)
            if isinstance(inst, NodoFor):
                if hasattr(inst, "inicio") and isinstance(inst.inicio, NodoAsignacion):
                    inst.inicio.expresion = opt_expr(inst.inicio.expresion)
                if hasattr(inst, "condicion"):
                    inst.condicion = opt_expr(inst.condicion)
                if hasattr(inst, "incremento") and hasattr(inst.incremento, "expresion"):
                    inst.incremento.expresion = opt_expr(inst.incremento.expresion)
            if hasattr(inst, "cuerpo"):
                opt_bloque(inst.cuerpo)
            if hasattr(inst, "cuerpo_if"):
                opt_bloque(inst.cuerpo_if)
            if hasattr(inst, "cuerpo_else"):
                opt_bloque(inst.cuerpo_else)

    for funcion in getattr(ast, "funciones", []):
        opt_bloque(funcion.cuerpo)
    if getattr(ast, "main", None):
        opt_bloque(ast.main.cuerpo)
    return cambios


# ===========================================================================
# TABLA DE SÍMBOLOS AUXILIAR  (para la GUI — complementa la del semántico)
# ===========================================================================

def construir_tabla_simbolos(ast):
    """
    Recorre el AST y construye la tabla de símbolos del programa.
    Retorna un diccionario con tres secciones:
      - funciones : funciones declaradas (nombre, tipo retorno, parámetros)
      - variables : variables locales y parámetros (nombre, tipo, ámbito, clase)
      - strings   : literales de texto usados en print/println/printf/puts
    """
    tabla = {"funciones": [], "variables": [], "strings": []}

    def recorrer(instrucciones, ambito):
        for inst in instrucciones:
            if isinstance(inst, NodoAsignacion):
                tabla["variables"].append({
                    "nombre": inst.nombre[1],
                    "tipo"  : inst.tipo[1],
                    "ambito": ambito,
                    "clase" : "variable local",
                })
            elif isinstance(inst, NodoPrint):
                texto = inst.argumentos[0] if inst.argumentos else ""
                tabla["strings"].append({
                    "etiqueta": inst.etiqueta,
                    "valor"   : texto,
                    "tipo"    : inst.tipo_print[1],
                    "ambito"  : ambito,
                })
            elif isinstance(inst, NodoImprimir):
                from node import NodoString
                for arg in inst.argumentos:
                    if isinstance(arg, NodoString):
                        tabla["strings"].append({
                            "etiqueta": inst.etiqueta,
                            "valor"   : arg.valor[1].strip('"'),
                            "tipo"    : inst.tipo[1],
                            "ambito"  : ambito,
                        })
            elif isinstance(inst, NodoWhile):
                recorrer(inst.cuerpo, ambito)
            elif isinstance(inst, NodoFor):
                if isinstance(inst.inicio, NodoAsignacion):
                    tabla["variables"].append({
                        "nombre": inst.inicio.nombre[1],
                        "tipo"  : inst.inicio.tipo[1],
                        "ambito": ambito,
                        "clase" : "variable de control (for)",
                    })
                recorrer(inst.cuerpo, ambito)
            elif isinstance(inst, NodoIf):
                recorrer(inst.cuerpo_if, ambito)
                if inst.cuerpo_else:
                    recorrer(inst.cuerpo_else, ambito)

    if ast.main:
        tabla["funciones"].append({
            "nombre"      : "main",
            "tipo_retorno": "int",
            "parametros"  : [],
            "clase"       : "función principal",
        })
        recorrer(ast.main.cuerpo, "main")

    for funcion in ast.funciones:
        params = [{"nombre": p.nombre[1], "tipo": p.tipo[1]} for p in funcion.parametros]
        tabla["funciones"].append({
            "nombre"      : funcion.nombre[1],
            "tipo_retorno": funcion.tipo[1],
            "parametros"  : params,
            "clase"       : "función",
        })
        for p in funcion.parametros:
            tabla["variables"].append({
                "nombre": p.nombre[1],
                "tipo"  : p.tipo[1],
                "ambito": funcion.nombre[1],
                "clase" : "parámetro",
            })
        recorrer(funcion.cuerpo, funcion.nombre[1])

    return tabla


def imprimir_tabla_simbolos(tabla):
    ancho = 70
    print("=" * ancho)
    print(" TABLA DE SÍMBOLOS ".center(ancho))
    print("=" * ancho)

    print("\n[ FUNCIONES ]")
    print(f"  {'Nombre':<20} {'Tipo retorno':<14} {'Clase':<22} {'Parámetros'}")
    print("  " + "-" * (ancho - 2))
    if tabla["funciones"]:
        for f in tabla["funciones"]:
            params_str = ", ".join(f"{p['tipo']} {p['nombre']}" for p in f["parametros"]) or "(ninguno)"
            print(f"  {f['nombre']:<20} {f['tipo_retorno']:<14} {f['clase']:<22} {params_str}")
    else:
        print("  (sin funciones declaradas)")

    print("\n[ VARIABLES ]")
    print(f"  {'Nombre':<20} {'Tipo':<10} {'Ámbito':<16} {'Clase'}")
    print("  " + "-" * (ancho - 2))
    if tabla["variables"]:
        for v in tabla["variables"]:
            print(f"  {v['nombre']:<20} {v['tipo']:<10} {v['ambito']:<16} {v['clase']}")
    else:
        print("  (sin variables declaradas)")

    print("\n[ LITERALES DE CADENA ]")
    print(f"  {'Etiqueta':<12} {'Tipo':<10} {'Ámbito':<16} {'Valor'}")
    print("  " + "-" * (ancho - 2))
    if tabla["strings"]:
        for s in tabla["strings"]:
            print(f"  {s['etiqueta']:<12} {s['tipo']:<10} {s['ambito']:<16} \"{s['valor']}\"")
    else:
        print("  (sin literales de cadena)")

    print("\n" + "=" * ancho)


# ===========================================================================
# COMPILACIÓN  (nasm + gcc con libc para printf)
# ===========================================================================

def compilar_asm(asm_path):
    """
    Ensambla con NASM y enlaza con GCC usando Win64 en Windows y ELF32 fuera de Windows.
    Retorna (exito: bool, log: str).
    """
    log = []
    try:
        if not shutil.which("nasm"):
            return False, "[NASM ERROR] No se encontro 'nasm' en el PATH. Instala NASM o agrega nasm.exe al PATH para generar el ejecutable."
        if not shutil.which("gcc"):
            return False, "[GCC ERROR] No se encontro 'gcc' en el PATH. Se requiere GCC para enlazar el objeto generado por NASM."

        asm_path = os.path.abspath(asm_path)
        out_dir = os.path.dirname(asm_path)
        asm_name = os.path.basename(asm_path)
        base_name = os.path.splitext(asm_name)[0]
        obj_name = f"{base_name}.o"
        exe_name = f"{base_name}.exe" if os.name == "nt" else base_name
        executable_path = os.path.join(out_dir, exe_name)
        # Asumimos ELF32 para NASM (Linux) pero en Windows se suele usar -f win32 o -f elf
        # Ojo: si estás en Windows, MinGW puede enlazar -f elf32 sin problema.
        nasm_format = "win64" if os.name == "nt" else "elf32"
        nasm_cmd = ["nasm", "-f", nasm_format, asm_name, "-o", obj_name]
        res_nasm = subprocess.run(nasm_cmd, capture_output=True, text=True, cwd=out_dir)
        log.append(f"[NASM] {' '.join(nasm_cmd)}")
        log.append(f"[NASM] Codigo de salida: {res_nasm.returncode}")
        if res_nasm.stdout: log.append(res_nasm.stdout)
        if res_nasm.stderr: log.append(res_nasm.stderr)
        
        if res_nasm.returncode != 0:
            return False, "\n".join(log)

        gcc_cmd = ["gcc", obj_name, "-o", exe_name] if os.name == "nt" else ["gcc", "-m32", obj_name, "-o", exe_name]
        res_gcc = subprocess.run(gcc_cmd, capture_output=True, text=True, cwd=out_dir)
        log.append(f"[GCC]  {' '.join(gcc_cmd)}")
        log.append(f"[GCC]  Codigo de salida: {res_gcc.returncode}")
        if res_gcc.stdout: log.append(res_gcc.stdout)
        if res_gcc.stderr: log.append(res_gcc.stderr)
        if res_gcc.returncode != 0:
            return False, "\n".join(log)
        
        log.append(f"[OK] Ejecutable generado: {executable_path}")
        return True, "\n".join(log)
            
    except Exception as e:
        log.append(f"[ERROR COMPILACIÓN C/ASM] {e}")
        return False, "\n".join(log)

# ===========================================================================
# API PRINCIPAL  (para la interfaz gráfica)
# ===========================================================================

def _linea_fuente(codigo, linea):
    if not isinstance(linea, int) or linea < 1:
        return ""
    lineas = codigo.splitlines()
    return lineas[linea - 1].strip() if linea <= len(lineas) else ""


def _diagnostico(codigo, fase, mensaje, severidad="error", linea=None, columna=None):
    if linea is None or columna is None:
        match = re.search(r"L(?:i|í|Ã­)nea\s+(\d+)(?:,\s*Columna\s+(\d+))?", str(mensaje))
        if match:
            linea = linea or int(match.group(1))
            columna = columna or (int(match.group(2)) if match.group(2) else None)
    return {
        "fase": fase,
        "severidad": severidad,
        "linea": linea,
        "columna": columna,
        "mensaje": str(mensaje).strip(),
        "fuente": _linea_fuente(codigo, linea),
    }


def _diagnostico_semantico(codigo, item, severidad):
    linea = item.linea if isinstance(item.linea, int) else None
    etiquetas_claras = {
        "DIVISION_CERO": "Division por cero",
        "VAR_NO_DECLARADA": "Variable no declarada",
        "VAR_YA_DECLARADA": "Variable ya declarada",
        "TIPO_INCOMPATIBLE": "Tipo incompatible",
        "FUNC_NO_DECLARADA": "Funcion no declarada",
        "FUNC_YA_DECLARADA": "Funcion ya declarada",
        "RETORNO_TIPO": "Retorno incompatible",
        "VAR_NO_USADA": "Variable no usada",
    }
    etiqueta = etiquetas_claras.get(getattr(item, "codigo", ""), "")
    mensaje = f"{etiqueta}: {item.mensaje}" if etiqueta else item.mensaje
    return _diagnostico(codigo, "semantico", mensaje, severidad, linea)


def compilar_codigo(codigo: str, archivo_asm: str = "salida.asm", nombre_programa: str = None) -> dict:
    """
    Ejecuta todas las fases del compilador sobre *codigo* y devuelve
    un diccionario con los resultados de cada fase.

    Parámetros:
        codigo     -- código fuente en el lenguaje del compilador
        archivo_asm -- ruta donde guardar el .asm generado

    Retorna un dict con las claves:
        tokens, ast_json, tabla, errores, avisos,
        ruby, python, rust, asm, log, ok
    """
    log_lines = []
    resultado = {
        "tokens"  : [],
        "ast_json": None,
        "tabla"   : None,
        "errores" : [],
        "avisos"  : [],
        "diagnosticos": [],
        "ruby"    : "",
        "python"  : "",
        "rust"    : "",
        "asm"     : "",
        "log"     : "",
        "ok"      : False,
    }

    # ------------------------------------------------------------------
    # FASE 1: Análisis léxico
    # ------------------------------------------------------------------
    try:
        tokens = identificar_tokens(codigo)
        resultado["tokens"] = tokens
        # log_lines.append(f"[LÉXICO] {len(tokens)} tokens encontrados.")
    except Exception as e:
        log_lines.append(f"[LÉXICO ERROR] {e}")
        resultado["errores"].append(str(e))
        resultado["diagnosticos"].append(_diagnostico(codigo, "lexico", e))
        resultado["log"] = "\n".join(log_lines)
        return resultado

    # ------------------------------------------------------------------
    # FASE 2: Análisis sintáctico
    # ------------------------------------------------------------------
    try:
        parser  = Parser(tokens)
        ast     = parser.parsear()
        ast.nombre_programa = nombre_programa or os.path.splitext(os.path.basename(archivo_asm))[0]
        if ast.main is None:
            raise SyntaxError("El programa debe declarar la funcion principal 'int main() { ... }'")
        ast_dict = imprimir_ast(ast)
        resultado["ast_json"] = ast_dict
        log_lines.append("[SINTACTICO] AST construido correctamente.")
    except SyntaxError as e:
        log_lines.append(f"[SINTACTICO ERROR] {e}")
        resultado["errores"].append(str(e))
        resultado["diagnosticos"].append(_diagnostico(codigo, "sintactico", e))
        resultado["log"] = "\n".join(log_lines)
        return resultado

    # ------------------------------------------------------------------
    # FASE 3: Análisis semántico
    # ------------------------------------------------------------------
    try:
        semantico = AnalizadorSemantico()
        tabla_sem, errores, avisos = semantico.analizar(ast)

        resultado["tabla"]   = tabla_sem.como_dict()
        resultado["errores"] = [str(e) for e in errores]
        resultado["avisos"]  = [str(a) for a in avisos]
        resultado["diagnosticos"] = (
            [_diagnostico_semantico(codigo, e, "error") for e in errores]
            + [_diagnostico_semantico(codigo, a, "aviso") for a in avisos]
        )

        if errores:
            log_lines.append(f"[SEMANTICO] {len(errores)} error(es) encontrado(s).")
            for e in errores:
                log_lines.append(str(e))
        else:
            log_lines.append("[SEMANTICO] Sin errores.")

        if avisos:
            log_lines.append(f"[SEMANTICO] {len(avisos)} advertencia(s).")
            for a in avisos:
                log_lines.append(str(a))

        if errores:
            resultado["log"] = "\n".join(log_lines)
            return resultado

    except Exception as e:
        log_lines.append(f"[SEMANTICO ERROR] {e}")
        resultado["errores"].append(str(e))
        resultado["diagnosticos"].append(_diagnostico(codigo, "semantico", e))
        resultado["log"] = "\n".join(log_lines)
        return resultado

    # ------------------------------------------------------------------
    # FASE 4: Optimizacion del AST
    # ------------------------------------------------------------------
    try:
        cambios_opt = optimizar_ast(ast)
        if cambios_opt:
            resultado["ast_json"] = imprimir_ast(ast)
            log_lines.append(f"[OPTIMIZACION] {cambios_opt} expresion(es) simplificada(s).")
        else:
            log_lines.append("[OPTIMIZACION] No se encontraron simplificaciones aplicables.")
    except Exception as e:
        mensaje = f"No se pudo optimizar el programa: {e}"
        log_lines.append(f"[OPTIMIZACION ERROR] {e}")
        resultado["errores"].append(mensaje)
        resultado["diagnosticos"].append(_diagnostico(codigo, "optimizacion", mensaje))
        resultado["log"] = "\n".join(log_lines)
        return resultado

    # ------------------------------------------------------------------
    # FASE 5: Traducciones
    # ------------------------------------------------------------------
    try:
        resultado["ruby"]   = ast.traducirRuby()   if hasattr(ast, "traducirRuby")   else ""
        resultado["python"] = ast.traducirPy()     if hasattr(ast, "traducirPy")     else ""
        resultado["rust"]   = ast.traducirRust()   if hasattr(ast, "traducirRust")   else ""
        log_lines.append("[TRADUCCIONES] Ruby, Python y Rust generados.")
    except Exception as e:
        log_lines.append(f"[TRADUCCIONES ERROR] {e}")

    # ------------------------------------------------------------------
    # FASE 5: Generación de código ensamblador
    # ------------------------------------------------------------------
    try:
        asm = ast.generarCodigo()
        resultado["asm"] = asm
        with open(archivo_asm, "w", encoding="utf-8") as f:
            f.write(asm)
        log_lines.append(f"[ASM] Codigo ensamblador guardado en '{archivo_asm}'.")
    except Exception as e:
        log_lines.append(f"[ASM ERROR] {e}")
        resultado["errores"].append(str(e))
        resultado["diagnosticos"].append(_diagnostico(codigo, "asm", f"No se pudo generar assembler: {e}"))

    resultado["ok"]  = len(resultado["errores"]) == 0
    resultado["log"] = "\n".join(log_lines)
    return resultado


# ===========================================================================
# EJECUCIÓN DIRECTA (demo en consola)
# ===========================================================================

def main():
    codigo = """
    int suma(int a, int b) {
        int resultado = a + b;
        return resultado;
    }

    int main() {
        int x = 10;
        int y = 3;
        float pi = 3.14;
        float radio = 2.5;
        float area = pi * radio;
        int total = suma(x, y);
        println("Resultado de la suma:");
        int i = 0;
        while (i < 3) {
            int paso = i + 1;
            i = paso;
        }
        if (total > 10) {
            int grande = 1;
        } else {
            int chico = 0;
        }
        return 0;
    }
    """

    res = compilar_codigo(codigo)

    print("=== TOKENS ===")
    for tok in res["tokens"]:
        print(f"  {tok}")

    print("\n=== AST ===")
    print(json.dumps(res["ast_json"], indent=2, ensure_ascii=False))

    print("\n=== TABLA DE SÍMBOLOS (semántico) ===")
    t = res["tabla"]
    if t:
        print("Funciones:", t["funciones"])
        print("Variables:", t["variables"])

    print("\n=== ERRORES SEMÁNTICOS ===")
    for e in res["errores"]:
        print(e)
    if not res["errores"]:
        print("  Sin errores.")

    print("\n=== ADVERTENCIAS ===")
    for a in res["avisos"]:
        print(a)
    if not res["avisos"]:
        print("  Sin advertencias.")

    print("\n=== TRADUCCIÓN A RUBY ===")
    print(res["ruby"])

    print("\n=== TRADUCCIÓN A PYTHON ===")
    print(res["python"])

    print("\n=== TRADUCCIÓN A RUST ===")
    print(res["rust"])

    print("\n=== CÓDIGO ENSAMBLADOR ===")
    print(res["asm"])

    print("\n=== LOG DE COMPILACIÓN ===")
    print(res["log"])


if __name__ == "__main__":
    main()
