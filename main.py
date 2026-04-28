from lexico import identificar_tokens
from sintactico import Parser, imprimir_ast
from semantico import AnalizadorSemantico, imprimir_resultado_semantico
from node import (NodoAsignacion, NodoPrint, NodoWhile, NodoFor, NodoIf,
                  NodoLlamadaFuncion, NodoRetorno)
import json
import subprocess
import os


# ===========================================================================
# TABLA DE SÍMBOLOS
# ===========================================================================

def construir_tabla_simbolos(ast):
    """
    Recorre el AST y construye la tabla de símbolos del programa.
    Retorna un diccionario con tres secciones:
      - funciones : funciones declaradas (nombre, tipo retorno, parámetros)
      - variables : variables locales y parámetros (nombre, tipo, ámbito)
      - strings   : literales de texto usados en print/println
    """
    tabla = {
        "funciones": [],
        "variables": [],
        "strings"  : [],
    }

    def recorrer_instrucciones(instrucciones, ambito):
        for inst in instrucciones:
            if isinstance(inst, NodoAsignacion):
                tabla["variables"].append({
                    "nombre" : inst.nombre[1],
                    "tipo"   : inst.tipo[1],
                    "ambito" : ambito,
                    "clase"  : "variable local",
                })
            elif isinstance(inst, NodoPrint):
                texto = inst.argumentos[0] if inst.argumentos else ""
                tabla["strings"].append({
                    "etiqueta" : inst.etiqueta,
                    "valor"    : texto,
                    "tipo"     : inst.tipo_print[1],  # print / println
                    "ambito"   : ambito,
                })
            elif isinstance(inst, NodoWhile):
                recorrer_instrucciones(inst.cuerpo, ambito)
            elif isinstance(inst, NodoFor):
                if isinstance(inst.inicio, NodoAsignacion):
                    tabla["variables"].append({
                        "nombre" : inst.inicio.nombre[1],
                        "tipo"   : inst.inicio.tipo[1],
                        "ambito" : ambito,
                        "clase"  : "variable de control (for)",
                    })
                recorrer_instrucciones(inst.cuerpo, ambito)
            elif isinstance(inst, NodoIf):
                recorrer_instrucciones(inst.cuerpo_if, ambito)
                if inst.cuerpo_else:
                    recorrer_instrucciones(inst.cuerpo_else, ambito)

    # Registrar función main
    if ast.main:
        tabla["funciones"].append({
            "nombre"      : "main",
            "tipo_retorno": "int",
            "parametros"  : [],
            "clase"       : "función principal",
        })
        recorrer_instrucciones(ast.main.cuerpo, "main")

    # Registrar demás funciones declaradas
    for funcion in ast.funciones:
        params = [
            {"nombre": p.nombre[1], "tipo": p.tipo[1]}
            for p in funcion.parametros
        ]
        tabla["funciones"].append({
            "nombre"      : funcion.nombre[1],
            "tipo_retorno": funcion.tipo[1],
            "parametros"  : params,
            "clase"       : "función",
        })
        # Parámetros también se registran como variables
        for p in funcion.parametros:
            tabla["variables"].append({
                "nombre" : p.nombre[1],
                "tipo"   : p.tipo[1],
                "ambito" : funcion.nombre[1],
                "clase"  : "parámetro",
            })
        recorrer_instrucciones(funcion.cuerpo, funcion.nombre[1])

    return tabla


def imprimir_tabla_simbolos(tabla):
    ancho = 70
    print("=" * ancho)
    print(" TABLA DE SÍMBOLOS ".center(ancho))
    print("=" * ancho)

    # --- Funciones ---
    print("\n[ FUNCIONES ]")
    print(f"  {'Nombre':<20} {'Tipo retorno':<14} {'Clase':<22} {'Parámetros'}")
    print("  " + "-" * (ancho - 2))
    if tabla["funciones"]:
        for f in tabla["funciones"]:
            params_str = ", ".join(
                f"{p['tipo']} {p['nombre']}" for p in f["parametros"]
            ) or "(ninguno)"
            print(f"  {f['nombre']:<20} {f['tipo_retorno']:<14} {f['clase']:<22} {params_str}")
    else:
        print("  (sin funciones declaradas)")

    # --- Variables ---
    print("\n[ VARIABLES ]")
    print(f"  {'Nombre':<20} {'Tipo':<10} {'Ámbito':<16} {'Clase'}")
    print("  " + "-" * (ancho - 2))
    if tabla["variables"]:
        for v in tabla["variables"]:
            print(f"  {v['nombre']:<20} {v['tipo']:<10} {v['ambito']:<16} {v['clase']}")
    else:
        print("  (sin variables declaradas)")

    # --- Literales de cadena ---
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
# COMPILACIÓN (nasm + gcc con libc para printf)
# ===========================================================================

def compilar(archivo_asm):
    nombre = archivo_asm.replace(".asm", "")
    archivo_obj = nombre + ".o"
    # Paso 1: Ensamblar con NASM en formato ELF32
    resultado_nasm = subprocess.run(
        ["nasm", "-f", "elf32", archivo_asm, "-o", archivo_obj],
        capture_output=True, text=True
    )
    if resultado_nasm.returncode != 0:
        print("Error en nasm:")
        print(resultado_nasm.stderr)
        return
    # Paso 2: Enlazar con gcc para incluir libc (necesario para printf)
    #         -m32    -> produce ejecutable de 32 bits
    #         -no-pie -> deshabilita PIE para compatibilidad con codigo asm simple
    resultado_ld = subprocess.run(
        ["gcc", "-m32", "-no-pie", archivo_obj, "-o", nombre],
        capture_output=True, text=True
    )
    if resultado_ld.returncode != 0:
        print("Error en gcc (enlazado):")
        print(resultado_ld.stderr)
        return
    print(f"Compilado exitosamente: {nombre}")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    codigo = """
    int main() {
        int a = 10;
        int b = 3;
        int c = a + b;
        float x = 3.14;
        float y = 2.5;
        float z = x + y;
        float w = x * y;
        float d = x - y;
        float q = x / y;
        println("Operaciones con floats listas");
        return 0;
    }
    """

    tokens = identificar_tokens(codigo)
    parser = Parser(tokens)
    ast = parser.parsear()

    print("=== AST ===")
    print(json.dumps(imprimir_ast(ast), indent=2, ensure_ascii=False))

    print("\n=== ANÁLISIS SEMÁNTICO Y TABLA DE SÍMBOLOS ===")
    semantico = AnalizadorSemantico()
    tabla, errores, avisos = semantico.analizar(ast)
    tabla.imprimir()
    imprimir_resultado_semantico(errores, avisos)

    print("\n=== TABLA DE SIMBOLOS ===")
    tabla = construir_tabla_simbolos(ast)
    imprimir_tabla_simbolos(tabla)

    print("\n=== TRADUCCION A RUBY ===")
    for func in ast.funciones:
        print(func.traducirRuby())
    if ast.main:
        print(ast.main.traducirRuby())

    print("\n=== CODIGO ENSAMBLADOR ===")
    asm = ast.generarCodigo()
    print(asm)

    with open("salida.asm", "w") as f:
        f.write(asm)

    # print("\n=== COMPILANDO CON NASM Y LD ===")
    # compilar("salida.asm")

    # import subprocess as sp
    # print("\n=== EJECUCION DEL BINARIO ===")
    # resultado = sp.run(["./salida"], capture_output=True, text=True)
    # print("Salida:", resultado.stdout)
    # if resultado.stderr:
    #     print("Stderr:", resultado.stderr)
    # print("Código de salida:", resultado.returncode)

main()