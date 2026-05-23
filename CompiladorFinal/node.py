# ===========================================================================
# NODOS DEL ÁRBOL DE SINTAXIS ABSTRACTA (AST)
# ===========================================================================
# Estructura: mi compilador (RAR) como base.
# Adiciones del inge (ZIP): NodoString, NodoIncremento, NodoEntrada,
#   NodoImprimir (printf/puts), optimizador algebraico en NodoOperacion.
# Traducciones disponibles: Python, Ruby, Rust.
# Generación de código: ensamblador NASM ELF32 (x87 FPU para floats).
# ===========================================================================

import os
import re
import codecs


ES_WIN64 = os.name == "nt"


def _base_pila():
    return "rbp" if ES_WIN64 else "ebp"


def _es_float_expr(nodo):
    return hasattr(nodo, "es_float") and callable(nodo.es_float) and nodo.es_float()


def _generar_float_operand(nodo):
    codigo = nodo.generarCodigo()
    if _es_float_expr(nodo):
        return codigo
    if ES_WIN64:
        return "\n".join([
            codigo,
            "    sub rsp, 8",
            "    mov dword [rsp], eax",
            "    fild dword [rsp]",
            "    add rsp, 8",
        ])
    return "\n".join([
        codigo,
        "    sub esp, 4",
        "    mov dword [esp], eax",
        "    fild dword [esp]",
        "    add esp, 4",
    ])


class NodoAST:
    """Clase base de todos los nodos del AST."""
    pass


# ---------------------------------------------------------------------------
# NodoPrograma
# ---------------------------------------------------------------------------

class NodoPrograma(NodoAST):
    def __init__(self, funciones, main):
        self.variables = []
        self.funciones = funciones   # lista de NodoFuncion (no-main)
        self.main = main             # NodoFuncion main (puede ser None)

    # ---- Generación de código ensamblador ----------------------------------

    def generarCodigo(self):
        data_text = [
            "section .data",
            '    fmt_int db "%d", 10, 0',
            '    fmt_float db "%f", 10, 0',
            '    fmt_str db "%s", 10, 0',
            '    fmt_scanf db "%d", 0',
            '    msg_div_zero db "Error de ejecucion: division por cero", 10, 0',
            '    __flt_zero dq 0.0',
            '    fmt_nl db 10, 0'
        ]
        data_bss  = ["section .bss", "    __float_print_tmp resq 1"]
        codigo    = ["extern printf", "extern scanf", "extern fflush", "section .text", "global main"]
        float_consts_vistas = set()

        def recolectar_datos(nodo):
            if isinstance(nodo, list):
                for n in nodo: recolectar_datos(n)
                return
            if not nodo: return
            if hasattr(nodo, 'obtenerDato') and callable(nodo.obtenerDato):
                dato = nodo.obtenerDato()
                if dato: data_text.append(dato)
            
            # Recorrer hijos
            if hasattr(nodo, 'cuerpo'): recolectar_datos(nodo.cuerpo)
            if hasattr(nodo, 'cuerpo_if'): recolectar_datos(nodo.cuerpo_if)
            if hasattr(nodo, 'cuerpo_else'): recolectar_datos(nodo.cuerpo_else)
            if hasattr(nodo, 'expresion'): recolectar_datos(nodo.expresion)
            if hasattr(nodo, 'argumentos'): recolectar_datos(nodo.argumentos)
            if hasattr(nodo, 'inicio'): recolectar_datos(nodo.inicio)
            if hasattr(nodo, 'condicion'): recolectar_datos(nodo.condicion)
            if hasattr(nodo, 'izquierda'): recolectar_datos(nodo.izquierda)
            if hasattr(nodo, 'derecha'): recolectar_datos(nodo.derecha)

        def extraer_float_consts(bloque_asm):
            """Mueve las directivas ; [FLOAT_CONST] etiqueta dq valor a .data."""
            lineas_limpias = []
            for linea in bloque_asm.split("\n"):
                m = re.match(r"\s*;\s*\[FLOAT_CONST\]\s+(\S+)\s+dq\s+(\S+)", linea)
                if m:
                    etiqueta, valor = m.group(1), m.group(2)
                    if etiqueta not in float_consts_vistas:
                        float_consts_vistas.add(etiqueta)
                        data_text.append(f"    {etiqueta} dq {valor}  ; constante float")
                else:
                    if linea.strip():
                        lineas_limpias.append(linea)
            return "\n".join(lineas_limpias)

        for funcion in self.funciones:
            bloque = funcion.generarCodigo()
            codigo.append(extraer_float_consts(bloque))
            recolectar_datos(funcion.cuerpo)

        if self.main:
            recolectar_datos(self.main.cuerpo)
            bloque_main = self.main.generarCodigo()
            codigo.append(extraer_float_consts(bloque_main))

        resultado  = "\n".join(data_text) + "\n"
        resultado += "\n".join(data_bss)  + "\n"
        resultado += "\n".join(codigo)
        return resultado

    # ---- Traducciones a otros lenguajes ------------------------------------

    def traducirRust(self):
        partes = [f.traducirRust() for f in self.funciones]
        if self.main:
            partes.append(self.main.traducirRust())
        return "\n\n".join(partes)

    def traducirPy(self):
        partes = [f.traducirPy() for f in self.funciones]
        if self.main:
            partes.append(self.main.traducirPy())
        return "\n\n".join(partes)

    def traducirRuby(self):
        partes = [f.traducirRuby() for f in self.funciones]
        if self.main:
            partes.append(self.main.traducirRuby())
        return "\n\n".join(partes)


# ---------------------------------------------------------------------------
# NodoFuncion
# ---------------------------------------------------------------------------

class NodoFuncion(NodoAST):
    def __init__(self, tipo, nombre, parametros, cuerpo):
        self.tipo       = tipo        # token KEYWORD (tipo de retorno)
        self.nombre     = nombre      # token IDENTIFIER
        self.parametros = parametros  # lista de NodoParametro
        self.cuerpo     = cuerpo      # lista de nodos instrucción

    def generarCodigo(self):
        local_bytes = getattr(self, 'local_bytes', 0)
        codigo  = f"\n{self.nombre[1]}:\n"
        if ES_WIN64:
            reserva = local_bytes + 32
            codigo += "    push rbp\n"
            codigo += "    mov rbp, rsp\n"
            codigo += f"    sub rsp, {reserva}  ; locales y shadow space Win64\n"
        else:
            codigo += "    push ebp\n"
            codigo += "    mov ebp, esp\n"
            if local_bytes > 0:
                codigo += f"    sub esp, {local_bytes}  ; reservar memoria local\n"
            
        codigo += "\n".join(c.generarCodigo() for c in self.cuerpo)
        if not any(isinstance(c, NodoRetorno) for c in self.cuerpo):
            codigo += "\n    xor eax, eax       ; valor de retorno 0"
        codigo += "\n    mov rsp, rbp" if ES_WIN64 else "\n    mov esp, ebp"
        codigo += "\n    pop rbp" if ES_WIN64 else "\n    pop ebp"
        codigo += "\n    ret\n"
        return codigo

    def traducirPy(self):
        params = ", ".join(p.traducirPy() for p in self.parametros)
        cuerpo = "\n  ".join(c.traducirPy() for c in self.cuerpo)
        return f"def {self.nombre[1]}({params}):\n  {cuerpo}"

    def traducirRuby(self):
        params = ", ".join(p.traducirRuby() for p in self.parametros)
        lineas = []
        for inst in self.cuerpo:
            for linea in inst.traducirRuby().split("\n"):
                lineas.append(f"  {linea}")
        cuerpo = "\n".join(lineas)
        return f"def {self.nombre[1]}({params})\n{cuerpo}\nend"

    def traducirRust(self):
        params   = ", ".join(p.traducirRust() for p in self.parametros)
        cuerpo   = "\n    ".join(c.traducirRust() for c in self.cuerpo)
        ret_type = " -> i32" if self.tipo[1] == "int" else ""
        return f"fn {self.nombre[1]}({params}){ret_type} {{\n    {cuerpo}\n}}"


# ---------------------------------------------------------------------------
# NodoParametro
# ---------------------------------------------------------------------------

class NodoParametro(NodoAST):
    def __init__(self, tipo, nombre):
        self.tipo   = tipo    # token KEYWORD
        self.nombre = nombre  # token IDENTIFIER

    def traducirPy(self):
        return self.nombre[1]

    def traducirRuby(self):
        return self.nombre[1]

    def traducirRust(self):
        rust_type = "i32" if self.tipo[1] == "int" else self.tipo[1]
        return f"{self.nombre[1]}: {rust_type}"


# ---------------------------------------------------------------------------
# NodoAsignacion
# ---------------------------------------------------------------------------

class NodoAsignacion(NodoAST):
    def __init__(self, tipo, nombre, expresion):
        self.tipo      = tipo       # token KEYWORD (int / float)
        self.nombre    = nombre     # token IDENTIFIER
        self.expresion = expresion  # nodo expresión

    def es_float(self):
        return self.tipo[1] == "float"

    def es_string(self):
        return self.tipo[1] == "string"

    def generarCodigo(self):
        expr_float = _es_float_expr(self.expresion)
        codigo = _generar_float_operand(self.expresion) if self.es_float() else self.expresion.generarCodigo()
        if hasattr(self, 'offset') and self.offset is not None:
            sign = "+" if self.offset > 0 else "-"
            op_str = f"{_base_pila()} {sign} {abs(self.offset)}"
            if self.es_float():
                codigo += f"\n    fstp qword [{op_str}]  ; guardar float en pila"
            elif self.es_string():
                tam = "qword" if ES_WIN64 else "dword"
                reg = "rax" if ES_WIN64 else "eax"
                codigo += f"\n    mov  {tam} [{op_str}], {reg}  ; guardar puntero string en pila"
            elif expr_float:
                codigo += f"\n    fistp dword [{op_str}]  ; convertir float a int"
            else:
                codigo += f"\n    mov  dword [{op_str}], eax  ; guardar int en pila"
        else:
            if self.es_float():
                codigo += f"\n    fstp qword [{self.nombre[1]}]  ; guardar float en variable"
            elif self.es_string():
                tam = "qword" if ES_WIN64 else "dword"
                reg = "rax" if ES_WIN64 else "eax"
                codigo += f"\n    mov  {tam} [{self.nombre[1]}], {reg}  ; guardar puntero string"
            elif expr_float:
                codigo += f"\n    fistp dword [{self.nombre[1]}]  ; convertir float a int"
            else:
                codigo += f"\n    mov  dword [{self.nombre[1]}], eax  ; guardar int en variable"
        return codigo

    def traducirPy(self):
        return f"{self.nombre[1]} = {self.expresion.traducirPy()}"

    def traducirRuby(self):
        return f"{self.nombre[1]} = {self.expresion.traducirRuby()}"

    def traducirRust(self):
        return f"let {self.nombre[1]} = {self.expresion.traducirRust()};"


# ---------------------------------------------------------------------------
# NodoOperacion
# ---------------------------------------------------------------------------

class NodoOperacion(NodoAST):
    _div_guard_counter = 0

    def __init__(self, izquierda, operador, derecha):
        self.izquierda = izquierda
        self.derecha   = derecha
        self.operador  = operador   # token OPERATOR

    @classmethod
    def _nuevo_div_guard(cls):
        cls._div_guard_counter += 1
        return f"div_ok_{cls._div_guard_counter}", f"div_zero_{cls._div_guard_counter}", f"div_fin_{cls._div_guard_counter}"

    def es_float(self):
        if self.operador[1] in ("<", ">", "<=", ">=", "==", "!="):
            return False
        def _es(nodo):
            if isinstance(nodo, NodoNumero):   return nodo.es_float()
            if isinstance(nodo, NodoIdent):    return nodo.es_float()
            if isinstance(nodo, NodoOperacion): return nodo.es_float()
            return False
        return _es(self.izquierda) or _es(self.derecha)

    def generarCodigo(self):
        codigo = []
        op = self.operador[1]
        if op in ("<", ">", "<=", ">=", "==", "!="):
            if _es_float_expr(self.izquierda) or _es_float_expr(self.derecha):
                codigo.append(_generar_float_operand(self.derecha))
                codigo.append(_generar_float_operand(self.izquierda))
                codigo.append("    fcomip st0, st1")
                codigo.append("    fstp st0")
                salto = {
                    "<": "setb",
                    ">": "seta",
                    "<=": "setbe",
                    ">=": "setae",
                    "==": "sete",
                    "!=": "setne",
                }[op]
                codigo.append(f"    {salto}  al")
                codigo.append("    movzx  eax, al")
                return "\n".join(codigo)
            codigo.append(self.izquierda.generarCodigo())
            codigo.append("    push   rax" if ES_WIN64 else "    push   eax")
            codigo.append(self.derecha.generarCodigo())
            codigo.append("    mov    r10d, eax" if ES_WIN64 else "    mov    ebx, eax")
            codigo.append("    pop    rax" if ES_WIN64 else "    pop    eax")
            codigo.append("    cmp    eax, r10d" if ES_WIN64 else "    cmp    eax, ebx")
            salto = {
                "<": "setl",
                ">": "setg",
                "<=": "setle",
                ">=": "setge",
                "==": "sete",
                "!=": "setne",
            }[op]
            codigo.append(f"    {salto}  al")
            codigo.append("    movzx  eax, al")
            return "\n".join(codigo)

        if self.es_float():
            codigo.append(_generar_float_operand(self.izquierda))
            codigo.append(_generar_float_operand(self.derecha))
            if op == "+": codigo.append("    faddp               ; ST(1)+ST(0), pop")
            elif op == "-": codigo.append("    fsubp               ; ST(1)-ST(0), pop")
            elif op == "*": codigo.append("    fmulp               ; ST(1)*ST(0), pop")
            elif op == "/":
                ok_lbl, zero_lbl, fin_lbl = self._nuevo_div_guard()
                codigo += [
                    "    fldz",
                    "    fcomip st0, st1",
                    f"    jne {ok_lbl}",
                    f"{zero_lbl}:",
                    "    fstp st0",
                    "    fstp st0",
                    "    lea rcx, [rel msg_div_zero]" if ES_WIN64 else "    push msg_div_zero",
                    "    call printf",
                    "    xor ecx, ecx" if ES_WIN64 else "    add esp, 4",
                    "    call fflush" if ES_WIN64 else "    push 0",
                    "    fldz" if ES_WIN64 else "    call fflush",
                    f"    jmp {fin_lbl}" if ES_WIN64 else "    add esp, 4",
                ]
                if not ES_WIN64:
                    codigo += ["    fldz", f"    jmp {fin_lbl}"]
                codigo += [f"{ok_lbl}:", "    fdivp               ; ST(1)/ST(0), pop", f"{fin_lbl}:"]
        else:
            codigo.append(self.izquierda.generarCodigo())
            codigo.append("    push   rax" if ES_WIN64 else "    push   eax")
            codigo.append(self.derecha.generarCodigo())
            codigo.append("    mov    r10d, eax" if ES_WIN64 else "    mov    ebx, eax")
            codigo.append("    pop    rax" if ES_WIN64 else "    pop    eax")
            derecha = "r10d" if ES_WIN64 else "ebx"
            if op == "+":   codigo.append(f"    add    eax, {derecha}")
            elif op == "-": codigo.append(f"    sub    eax, {derecha}")
            elif op == "*": codigo.append(f"    imul   eax, {derecha}")
            elif op == "/":
                ok_lbl, zero_lbl, fin_lbl = self._nuevo_div_guard()
                codigo.append(f"    cmp    {derecha}, 0")
                codigo.append(f"    jne    {ok_lbl}")
                codigo.append(f"{zero_lbl}:")
                if ES_WIN64:
                    codigo.append("    lea rcx, [rel msg_div_zero]")
                    codigo.append("    call printf")
                    codigo.append("    xor ecx, ecx")
                    codigo.append("    call fflush")
                else:
                    codigo.append("    push msg_div_zero")
                    codigo.append("    call printf")
                    codigo.append("    add esp, 4")
                    codigo.append("    push 0")
                    codigo.append("    call fflush")
                    codigo.append("    add esp, 4")
                codigo.append("    xor    eax, eax")
                codigo.append(f"    jmp    {fin_lbl}")
                codigo.append(f"{ok_lbl}:")
                codigo.append("    cdq")
                codigo.append(f"    idiv   {derecha}")
                codigo.append(f"{fin_lbl}:")
        return "\n".join(codigo)

    def optimizar(self):
        """
        Simplificación algebraica en tiempo de compilación (del inge).
        Retorna un nodo simplificado o self si no aplica.
        """
        izq = self.izquierda.optimizar() if isinstance(self.izquierda, NodoOperacion) else self.izquierda
        der = self.derecha.optimizar()   if isinstance(self.derecha,   NodoOperacion) else self.derecha

        if isinstance(izq, NodoNumero) and isinstance(der, NodoNumero):
            v_izq = float(izq.valor[1])
            v_der = float(der.valor[1])
            op    = self.operador[1]
            if   op == "+": v = v_izq + v_der
            elif op == "-": v = v_izq - v_der
            elif op == "*": v = v_izq * v_der
            elif op == "/":
                if v_der == 0:
                    raise Exception("Error: división por cero en tiempo de compilación")
                v = v_izq / v_der
            else:
                return NodoOperacion(izq, self.operador, der)
            ambos_enteros = not izq.es_float() and not der.es_float()
            tok = "INTEGER" if ambos_enteros and op != "/" and float(v).is_integer() else "FLOAT"
            return NodoNumero((tok, str(int(v) if tok == "INTEGER" else v)))

        op = self.operador[1]
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "/":
            raise Exception("Division por cero detectada en tiempo de compilacion")
        # Multiplicar por 1
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 1 and op == "*": return izq
        if isinstance(izq, NodoNumero) and float(izq.valor[1]) == 1 and op == "*": return der
        # Sumar 0
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "+": return izq
        if isinstance(izq, NodoNumero) and float(izq.valor[1]) == 0 and op == "+": return der
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "-": return izq
        if isinstance(izq, NodoNumero) and float(izq.valor[1]) == 0 and op == "*": return izq
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "*": return der
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 1 and op == "/": return izq
        # División por cero
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "/":
            raise Exception("Error: división por cero en tiempo de compilación")

        if izq is self.izquierda and der is self.derecha:
            return self
        return NodoOperacion(izq, self.operador, der)

    def traducirPy(self):
        return f"{self.izquierda.traducirPy()} {self.operador[1]} {self.derecha.traducirPy()}"

    def traducirRuby(self):
        return f"{self.izquierda.traducirRuby()} {self.operador[1]} {self.derecha.traducirRuby()}"

    def traducirRust(self):
        return f"{self.izquierda.traducirRust()} {self.operador[1]} {self.derecha.traducirRust()}"


# ---------------------------------------------------------------------------
# NodoRetorno
# ---------------------------------------------------------------------------

class NodoRetorno(NodoAST):
    def __init__(self, expresion):
        self.expresion = expresion

    def generarCodigo(self):
        return self.expresion.generarCodigo() + "  ; valor de retorno en eax"

    def traducirPy(self):
        return f"return {self.expresion.traducirPy()}"

    def traducirRuby(self):
        return f"return {self.expresion.traducirRuby()}"

    def traducirRust(self):
        return f"return {self.expresion.traducirRust()};"


# ---------------------------------------------------------------------------
# NodoIdent
# ---------------------------------------------------------------------------

class NodoIdent(NodoAST):
    def __init__(self, nombre, tipo=None):
        self.nombre = nombre   # token IDENTIFIER
        self._tipo  = tipo     # "int" | "float" | None (inyectado por el parser)

    def es_float(self):
        return self._tipo == "float"

    def generarCodigo(self):
        if hasattr(self, 'offset') and self.offset is not None:
            sign = "+" if self.offset > 0 else "-"
            op_str = f"{_base_pila()} {sign} {abs(self.offset)}"
            if self.es_float():
                return f"\n    fld  qword [{op_str}]  ; float -> ST(0)"
            if ES_WIN64 and self._tipo == "string":
                return f"\n    mov rax, [{op_str}]"
            return f"\n    mov eax, [{op_str}]"
        else:
            if self.es_float():
                return f"\n    fld  qword [{self.nombre[1]}]  ; float {self.nombre[1]} → ST(0)"
            return f"\n    mov eax, [{self.nombre[1]}]"

    def traducirPy(self):   return self.nombre[1]
    def traducirRuby(self): return self.nombre[1]
    def traducirRust(self): return self.nombre[1]


# ---------------------------------------------------------------------------
# NodoNumero
# ---------------------------------------------------------------------------

class NodoNumero(NodoAST):
    def __init__(self, valor):
        # valor: tuple (tipo_token, valor_str)
        # tipo_token: "FLOAT" | "INTEGER" | "NUMBER" (compat. inge)
        self.valor = valor

    def es_float(self):
        tok = self.valor[0]
        return tok == "FLOAT" or (tok == "NUMBER" and "." in self.valor[1])

    def optimizar(self):
        return self

    def generarCodigo(self):
        if self.es_float():
            safe    = self.valor[1].replace(".", "_")
            etq     = f"__flt_{safe}"
            ref     = f"rel {etq}" if ES_WIN64 else etq
            lineas  = [
                f"    ; [FLOAT_CONST] {etq} dq {self.valor[1]}",
                f"    fld  qword [{ref}]  ; carga {self.valor[1]} en ST(0)",
            ]
            return "\n".join(lineas)
        return f"\n    mov eax, {self.valor[1]}"

    def traducirPy(self):   return self.valor[1]
    def traducirRuby(self): return self.valor[1]
    def traducirRust(self): return self.valor[1]


# ---------------------------------------------------------------------------
# NodoString  (nuevo — del inge, para printf/puts con literales)
# ---------------------------------------------------------------------------

class NodoString(NodoAST):
    _contador = 0

    def __init__(self, valor):
        # valor: token STRING, e.g. (STRING, '"Hola mundo"')
        self.valor = valor
        NodoString._contador += 1
        self.etiqueta = f"str_lit_{NodoString._contador}"

    def generarCodigo(self):
        if ES_WIN64:
            return f"\n    lea rax, [rel {self.etiqueta}]"
        return f"\n    mov eax, {self.etiqueta}"

    def obtenerDato(self):
        texto = self.valor[1].strip('"').strip("'")
        texto = codecs.decode(texto, "unicode_escape")
        partes = []
        actual = []
        for ch in texto:
            if ch == "\n":
                if actual:
                    partes.append('"' + "".join(actual).replace('"', '\\"') + '"')
                    actual = []
                partes.append("10")
            elif ch == "\t":
                if actual:
                    partes.append('"' + "".join(actual).replace('"', '\\"') + '"')
                    actual = []
                partes.append("9")
            elif ch == "\r":
                if actual:
                    partes.append('"' + "".join(actual).replace('"', '\\"') + '"')
                    actual = []
                partes.append("13")
            else:
                actual.append(ch)
        if actual:
            partes.append('"' + "".join(actual).replace('"', '\\"') + '"')
        if not partes:
            partes.append('""')
        return f"    {self.etiqueta} db {', '.join(partes)}, 0"

    def traducirPy(self):
        return self.valor[1]   # ya tiene las comillas

    def traducirRuby(self):
        return self.valor[1]

    def traducirRust(self):
        return self.valor[1]


# ---------------------------------------------------------------------------
# NodoLlamadaFuncion
# ---------------------------------------------------------------------------

class NodoLlamadaFuncion(NodoAST):
    def __init__(self, nombref, argumentos):
        self.nombre_funcion = nombref    # str
        self.argumentos     = argumentos # lista de nodos

    def generarCodigo(self):
        codigo = []
        for arg in reversed(self.argumentos):
            codigo.append(arg.generarCodigo())
            codigo.append("    push eax   ; pasar argumento a la pila")
        codigo.append(f"    call {self.nombre_funcion}")
        codigo.append(f"    add esp, {len(self.argumentos) * 4}  ; limpiar pila")
        return "\n".join(codigo)

    def traducirPy(self):
        args = ", ".join(a.traducirPy() for a in self.argumentos)
        return f"{self.nombre_funcion}({args})"

    def traducirRuby(self):
        args = ", ".join(a.traducirRuby() for a in self.argumentos)
        return f"{self.nombre_funcion}({args})"

    def traducirRust(self):
        args = ", ".join(a.traducirRust() for a in self.argumentos)
        return f"{self.nombre_funcion}({args})"


# ---------------------------------------------------------------------------
# NodoInstruccion  (cout — estilo mi compilador original)
# ---------------------------------------------------------------------------

class NodoInstruccion(NodoAST):
    def __init__(self, tipo, argumentos):
        self.tipo_instruccion       = tipo       # token KEYWORD (cout)
        self.argumentos_instruccion = argumentos # lista de strings

    def traducirPy(self):
        if self.tipo_instruccion[1] == "cout":
            args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirPy()
                             for a in self.argumentos_instruccion)
            return f"print({args})"
        return ""

    def traducirRuby(self):
        if self.tipo_instruccion[1] == "cout":
            args = " ".join(a if isinstance(a, str) else a.traducirRuby()
                            for a in self.argumentos_instruccion)
            return f'puts "{args}"'
        return ""

    def traducirRust(self):
        if self.tipo_instruccion[1] == "cout":
            args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirRust()
                             for a in self.argumentos_instruccion)
            return f'println!("{{}}", {args});'
        return ""

    def generarCodigo(self):
        # cout no genera código asm en esta versión; se usa NodoPrint para println/print
        return ""


# ---------------------------------------------------------------------------
# NodoPrint  (print / println — estilo mi compilador original)
# ---------------------------------------------------------------------------

class NodoPrint(NodoAST):
    _contador = 0

    def __init__(self, tipo_print, argumentos):
        self.tipo_print = tipo_print   # token KEYWORD (print / println)
        self.argumentos = argumentos   # lista de strings o nodos
        NodoPrint._contador += 1
        self.etiqueta = f"msg_{NodoPrint._contador}"

    def generarCodigo(self):
        if ES_WIN64:
            return "\n".join([
                f"    lea rcx, [rel {self.etiqueta}]",
                "    call printf",
                "    xor ecx, ecx",
                "    call fflush",
            ])
        codigo = [
            f"    push {self.etiqueta}   ; puntero al string",
            f"    call printf",
            f"    add esp, 4             ; cdecl: caller limpia",
            f"    push 0                 ; flush all streams",
            f"    call fflush",
            f"    add esp, 4",
        ]
        return "\n".join(codigo)

    def obtenerDato(self):
        texto = self.argumentos[0] if self.argumentos else ""
        if self.tipo_print[1] == "println":
            return f'    {self.etiqueta} db "{texto}", 10, 0'
        return f'    {self.etiqueta} db "{texto}", 0'

    def traducirPy(self):
        args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirPy()
                         for a in self.argumentos)
        return f"print({args})" if self.tipo_print[1] == "println" else f"print({args}, end='')"

    def traducirRuby(self):
        args = " ".join(a if isinstance(a, str) else a.traducirRuby() for a in self.argumentos)
        return f'puts "{args}"' if self.tipo_print[1] == "println" else f'print "{args}"'

    def traducirRust(self):
        args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirRust()
                         for a in self.argumentos)
        return (f'println!("{{}}", {args});' if self.tipo_print[1] == "println"
                else f'print!("{{}}", {args});')


# ---------------------------------------------------------------------------
# NodoImprimir  (printf / puts — estilo inge, acepta NodoString o expresión)
# ---------------------------------------------------------------------------

class NodoImprimir(NodoAST):
    def __init__(self, tipo, argumentos):
        self.tipo       = tipo        # token KEYWORD (printf / puts)
        self.argumentos = argumentos  # lista de nodos (normalmente 1)

    def generarCodigo(self):
        arg = self.argumentos[0] if self.argumentos else None
        valor_arg = self.argumentos[1] if len(self.argumentos) > 1 else arg
        formato_arg = arg if len(self.argumentos) > 1 and isinstance(arg, NodoString) else None
        codigo = []
        if ES_WIN64:
            if formato_arg and valor_arg:
                codigo.append(valor_arg.generarCodigo())
                if _es_float_expr(valor_arg):
                    codigo.append("    fstp qword [rel __float_print_tmp]")
                    codigo.append("    movsd xmm1, qword [rel __float_print_tmp]")
                    codigo.append("    mov rdx, [rel __float_print_tmp]")
                elif getattr(valor_arg, '_tipo', None) == "string":
                    codigo.append("    mov rdx, rax")
                else:
                    codigo.append("    mov edx, eax")
                codigo.append(f"    lea rcx, [rel {formato_arg.etiqueta}]")
            elif isinstance(arg, NodoString):
                codigo.append(f"    lea rcx, [rel {arg.etiqueta}]")
            elif arg:
                codigo.append(arg.generarCodigo())
                if _es_float_expr(arg):
                    codigo.append("    fstp qword [rel __float_print_tmp]")
                    codigo.append("    movsd xmm1, qword [rel __float_print_tmp]")
                    codigo.append("    mov rdx, [rel __float_print_tmp]")
                    codigo.append("    lea rcx, [rel fmt_float]")
                elif getattr(arg, '_tipo', None) == "string":
                    codigo.append("    mov rdx, rax")
                    codigo.append("    lea rcx, [rel fmt_str]")
                else:
                    codigo.append("    mov edx, eax")
                    codigo.append("    lea rcx, [rel fmt_int]")
            else:
                codigo.append("    lea rcx, [rel fmt_int]")
            codigo.append("    call printf")
            if self.tipo[1] == "puts":
                codigo.append("    lea rcx, [rel fmt_nl]")
                codigo.append("    call printf")
            codigo.append("    xor ecx, ecx")
            codigo.append("    call fflush")
            return "\n".join(codigo)

        if formato_arg and valor_arg:
            codigo.append(valor_arg.generarCodigo())
            if _es_float_expr(valor_arg):
                codigo.append("    fstp qword [__float_print_tmp]")
                codigo.append("    push dword [__float_print_tmp + 4]")
                codigo.append("    push dword [__float_print_tmp]")
            else:
                codigo.append("    push eax")
            codigo.append(f"    push {formato_arg.etiqueta}")
            codigo.append(f"    call printf")
            codigo.append(f"    add esp, {12 if _es_float_expr(valor_arg) else 8}")
        elif isinstance(arg, NodoString):
            codigo.append(f"    push {arg.etiqueta}")
            codigo.append(f"    call printf")
            codigo.append(f"    add esp, 4")
        else:
            if arg:
                codigo.append(arg.generarCodigo())
                if _es_float_expr(arg):
                    codigo.append("    fstp qword [__float_print_tmp]")
                    codigo.append("    push dword [__float_print_tmp + 4]")
                    codigo.append("    push dword [__float_print_tmp]")
                else:
                    codigo.append("    push eax")
            
            tipo_arg = getattr(arg, '_tipo', None)
            if _es_float_expr(arg):
                codigo.append(f"    push fmt_float")
            elif tipo_arg == "string":
                codigo.append(f"    push fmt_str")
            else:
                codigo.append(f"    push fmt_int")
                
            codigo.append(f"    call printf")
            codigo.append(f"    add esp, {12 if _es_float_expr(arg) else (8 if arg else 4)}")
            
        if self.tipo[1] == "puts":
            codigo.append(f"    push fmt_nl")
            codigo.append(f"    call printf")
            codigo.append(f"    add esp, 4")
            
        codigo.append(f"    push 0")
        codigo.append(f"    call fflush")
        codigo.append(f"    add esp, 4")
            
        return "\n".join(codigo)

    def obtenerDato(self):
        return ""

    def traducirPy(self):
        args = ", ".join(a.traducirPy() for a in self.argumentos)
        return f"print({args})"

    def traducirRuby(self):
        args = " ".join(a.traducirRuby() for a in self.argumentos)
        return f"puts {args}"

    def traducirRust(self):
        args = ", ".join(a.traducirRust() for a in self.argumentos)
        return f'println!("{{}}", {args});'


# ---------------------------------------------------------------------------
# NodoWhile
# ---------------------------------------------------------------------------

class NodoWhile(NodoAST):
    def __init__(self, condicion, cuerpo):
        self.condicion = condicion
        self.cuerpo    = cuerpo

    _lbl_count = 0

    def generarCodigo(self):
        NodoWhile._lbl_count += 1
        n    = NodoWhile._lbl_count
        ini  = f"while_ini_{n}"
        fin  = f"while_fin_{n}"
        lineas = [
            f"{ini}:",
            self.condicion.generarCodigo(),
            "    cmp eax, 0",
            f"    je  {fin}",
        ]
        lineas += [c.generarCodigo() for c in self.cuerpo]
        lineas += [f"    jmp {ini}", f"{fin}:"]
        return "\n".join(lineas)

    def traducirPy(self):
        cond  = self.condicion.traducirPy()
        cuerpo = "\n    ".join(c.traducirPy() for c in self.cuerpo)
        return f"while {cond}:\n    {cuerpo}"

    def traducirRuby(self):
        cond  = self.condicion.traducirRuby()
        cuerpo = "\n  ".join(c.traducirRuby() for c in self.cuerpo)
        return f"while {cond}\n  {cuerpo}\nend"

    def traducirRust(self):
        cond  = self.condicion.traducirRust()
        cuerpo = "\n    ".join(c.traducirRust() for c in self.cuerpo)
        return f"while {cond} {{\n    {cuerpo}\n}}"


# ---------------------------------------------------------------------------
# NodoFor
# ---------------------------------------------------------------------------

class NodoFor(NodoAST):
    def __init__(self, inicio, condicion, incremento, cuerpo):
        self.inicio     = inicio      # NodoAsignacion
        self.condicion  = condicion   # nodo expresión
        self.incremento = incremento  # NodoIncremento o str (legado)
        self.cuerpo     = cuerpo      # lista de nodos

    _lbl_count = 0

    def generarCodigo(self):
        NodoFor._lbl_count += 1
        n   = NodoFor._lbl_count
        ini = f"for_ini_{n}"
        fin = f"for_fin_{n}"
        lineas = [self.inicio.generarCodigo(), f"{ini}:"]
        lineas.append(self.condicion.generarCodigo())
        lineas += ["    cmp eax, 0", f"    je  {fin}"]
        lineas += [c.generarCodigo() for c in self.cuerpo]
        # Incremento
        if isinstance(self.incremento, NodoIncremento):
            lineas.append(self.incremento.generarCodigo())
        elif isinstance(self.incremento, str):
            lineas.append(f"    ; inc/dec manual: {self.incremento}")
        lineas += [f"    jmp {ini}", f"{fin}:"]
        return "\n".join(lineas)

    def traducirPy(self):
        inicio    = self.inicio.traducirPy()
        cond      = self.condicion.traducirPy()
        inc       = (self.incremento.traducirPy() if isinstance(self.incremento, NodoIncremento)
                     else self.incremento)
        cuerpo    = "\n    ".join(c.traducirPy() for c in self.cuerpo)
        return f"{inicio}\nwhile {cond}:\n    {cuerpo}\n    {inc}"

    def traducirRuby(self):
        inicio = self.inicio.traducirRuby()
        cond   = self.condicion.traducirRuby()
        inc    = (self.incremento.traducirRuby() if isinstance(self.incremento, NodoIncremento)
                  else self.incremento)
        cuerpo = "\n  ".join(c.traducirRuby() for c in self.cuerpo)
        return f"{inicio}\nwhile {cond}\n  {cuerpo}\n  {inc}\nend"

    def traducirRust(self):
        inicio = self.inicio.traducirRust()
        cond   = self.condicion.traducirRust()
        inc    = (self.incremento.traducirRust() if isinstance(self.incremento, NodoIncremento)
                  else f"{self.incremento};")
        cuerpo = "\n    ".join(c.traducirRust() for c in self.cuerpo)
        return f"{inicio}\nwhile {cond} {{\n    {cuerpo}\n    {inc}\n}}"


# ---------------------------------------------------------------------------
# NodoIncremento  (nuevo — del inge: i++ / i--)
# ---------------------------------------------------------------------------

class NodoIncremento(NodoAST):
    def __init__(self, nombre, operador):
        self.nombre   = nombre    # token IDENTIFIER
        self.operador = operador  # token OPERATOR (++ o --)

    def generarCodigo(self):
        if hasattr(self, 'offset') and self.offset is not None:
            sign = "+" if self.offset > 0 else "-"
            op_str = f"{_base_pila()} {sign} {abs(self.offset)}"
            if self.operador[1] == "++":
                return f"    inc dword [{op_str}]"
            elif self.operador[1] == "--":
                return f"    dec dword [{op_str}]"
        else:
            var = self.nombre[1]
            if self.operador[1] == "++":
                return f"    inc dword [{var}]"
            elif self.operador[1] == "--":
                return f"    dec dword [{var}]"
        return ""

    def traducirPy(self):
        v = self.nombre[1]
        return f"{v} += 1" if self.operador[1] == "++" else f"{v} -= 1"

    def traducirRuby(self):
        v = self.nombre[1]
        return f"{v} += 1" if self.operador[1] == "++" else f"{v} -= 1"

    def traducirRust(self):
        v = self.nombre[1]
        return f"{v} += 1;" if self.operador[1] == "++" else f"{v} -= 1;"


# ---------------------------------------------------------------------------
# NodoIf
# ---------------------------------------------------------------------------

class NodoIf(NodoAST):
    def __init__(self, condicion, cuerpo_if, cuerpo_else=None):
        self.condicion   = condicion
        self.cuerpo_if   = cuerpo_if
        self.cuerpo_else = cuerpo_else  # None si no hay else

    _lbl_count = 0

    def generarCodigo(self):
        NodoIf._lbl_count += 1
        n   = NodoIf._lbl_count
        els = f"if_else_{n}"
        fin = f"if_fin_{n}"
        lineas = [self.condicion.generarCodigo(), "    cmp eax, 0"]
        if self.cuerpo_else:
            lineas.append(f"    je  {els}")
            lineas += [c.generarCodigo() for c in self.cuerpo_if]
            lineas += [f"    jmp {fin}", f"{els}:"]
            lineas += [c.generarCodigo() for c in self.cuerpo_else]
        else:
            lineas.append(f"    je  {fin}")
            lineas += [c.generarCodigo() for c in self.cuerpo_if]
        lineas.append(f"{fin}:")
        return "\n".join(lineas)

    def traducirPy(self):
        cond = self.condicion.traducirPy()
        ci   = "\n    ".join(c.traducirPy() for c in self.cuerpo_if)
        res  = f"if {cond}:\n    {ci}"
        if self.cuerpo_else:
            ce = "\n    ".join(c.traducirPy() for c in self.cuerpo_else)
            res += f"\nelse:\n    {ce}"
        return res

    def traducirRuby(self):
        cond = self.condicion.traducirRuby()
        ci   = "\n  ".join(c.traducirRuby() for c in self.cuerpo_if)
        res  = f"if {cond}\n  {ci}"
        if self.cuerpo_else:
            ce = "\n  ".join(c.traducirRuby() for c in self.cuerpo_else)
            res += f"\nelse\n  {ce}"
        res += "\nend"
        return res

    def traducirRust(self):
        cond = self.condicion.traducirRust()
        ci   = "\n    ".join(c.traducirRust() for c in self.cuerpo_if)
        res  = f"if {cond} {{\n    {ci}\n}}"
        if self.cuerpo_else:
            ce = "\n    ".join(c.traducirRust() for c in self.cuerpo_else)
            res += f" else {{\n    {ce}\n}}"
        return res


# ---------------------------------------------------------------------------
# NodoEntrada  (nuevo — del inge: scanf)
# ---------------------------------------------------------------------------

class NodoEntrada(NodoAST):
    def __init__(self, tipo, formato, variable):
        self.tipo     = tipo      # token KEYWORD (scanf)
        self.formato  = formato   # NodoString con el formato, e.g. "%d"
        self.variable = variable  # token IDENTIFIER

    def generarCodigo(self):
        if ES_WIN64:
            if hasattr(self, 'offset') and self.offset is not None:
                sign = "+" if self.offset > 0 else "-"
                op_str = f"{_base_pila()} {sign} {abs(self.offset)}"
                destino = f"[{op_str}]"
            else:
                destino = f"[rel {self.variable[1]}]"
            return (
                f"    lea  rdx, {destino}\n"
                f"    lea  rcx, [rel fmt_scanf]\n"
                f"    call scanf"
            )

        if hasattr(self, 'offset') and self.offset is not None:
            sign = "+" if self.offset > 0 else "-"
            op_str = f"{_base_pila()} {sign} {abs(self.offset)}"
            return (
                f"    lea  eax, [{op_str}]\n"
                f"    push eax\n"
                f"    push fmt_scanf\n"
                f"    call scanf\n"
                f"    add  esp, 8"
            )
        else:
            var = self.variable[1]
            return (
                f"    lea  eax, [{var}]\n"
                f"    push eax\n"
                f"    push fmt_scanf\n"
                f"    call scanf\n"
                f"    add  esp, 8"
            )

    def traducirPy(self):
        return f"{self.variable[1]} = int(input())"

    def traducirRuby(self):
        return f"{self.variable[1]} = gets.chomp.to_i"

    def traducirRust(self):
        v = self.variable[1]
        return (
            f"let mut {v}_str = String::new();\n"
            f"    std::io::stdin().read_line(&mut {v}_str).unwrap();\n"
            f"    let {v}: i32 = {v}_str.trim().parse().unwrap();"
        )
