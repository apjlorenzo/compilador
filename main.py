from lexico import identificar_tokens
from sintactico import Parser, imprimir_ast
import json
import subprocess
import os

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
    #         -m32    → produce ejecutable de 32 bits
    #         -no-pie → deshabilita PIE para compatibilidad con código asm simple
    resultado_ld = subprocess.run(
        ["gcc", "-m32", "-no-pie", archivo_obj, "-o", nombre],
        capture_output=True, text=True
    )
    if resultado_ld.returncode != 0:
        print("Error en gcc (enlazado):")
        print(resultado_ld.stderr)
        return
    print(f"Compilado exitosamente: {nombre}")

def main():
    codigo = """
    int main() {
        print("Hola mundo");
        println("Bienvenido al compilador");
        println("Fin del programa");
        return 0;
    }
    """

    tokens = identificar_tokens(codigo)
    parser = Parser(tokens)
    ast = parser.parsear()

    print("=== AST ===")
    print(json.dumps(imprimir_ast(ast), indent=2, ensure_ascii=False))

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

    ## print("\n=== COMPILANDO CON NASM Y LD ===")
    ##compilar("salida.asm")

main()