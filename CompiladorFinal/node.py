# ===========================================================================
# NODOS DEL ÁRBOL DE SINTAXIS ABSTRACTA (AST)
# ===========================================================================
# Estructura: mi compilador (RAR) como base.
# Adiciones del inge (ZIP): NodoString, NodoIncremento, NodoEntrada,
#   NodoImprimir (printf/puts), optimizador algebraico en NodoOperacion.
# Traducciones disponibles: Python, Ruby, Rust.
# Generación de código: ensamblador NASM ELF32 (x87 FPU para floats).
# ===========================================================================

import re


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
            '    fmt_scanf db "%d", 0'
        ]
        data_bss  = ["section .bss"]
        codigo    = ["extern printf", "extern scanf", "section .text", "global main"]
        float_consts_vistas = set()

        def recolectar_prints(instrucciones):
            for inst in instrucciones:
                if isinstance(inst, NodoPrint):
                    data_text.append(inst.obtenerDato())
                elif isinstance(inst, NodoImprimir):
                    data_text.append(inst.obtenerDato())
                elif isinstance(inst, NodoWhile):
                    recolectar_prints(inst.cuerpo)
                elif isinstance(inst, NodoFor):
                    recolectar_prints(inst.cuerpo)
                elif isinstance(inst, NodoIf):
                    recolectar_prints(inst.cuerpo_if)
                    if inst.cuerpo_else:
                        recolectar_prints(inst.cuerpo_else)

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
            recolectar_prints(funcion.cuerpo)

        if self.main:
            recolectar_prints(self.main.cuerpo)
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
        codigo += "    push ebp\n"
        codigo += "    mov ebp, esp\n"
        if local_bytes > 0:
            codigo += f"    sub esp, {local_bytes}  ; reservar memoria local\n"
            
        codigo += "\n".join(c.generarCodigo() for c in self.cuerpo)
        codigo += "\n    xor eax, eax       ; valor de retorno 0"
        codigo += "\n    mov esp, ebp"
        codigo += "\n    pop ebp"
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

    def generarCodigo(self):
        codigo = self.expresion.generarCodigo()
        if hasattr(self, 'offset') and self.offset is not None:
            sign = "+" if self.offset > 0 else "-"
            op_str = f"ebp {sign} {abs(self.offset)}"
            if self.es_float():
                codigo += f"\n    fstp qword [{op_str}]  ; guardar float en pila"
            else:
                codigo += f"\n    mov  dword [{op_str}], eax  ; guardar int en pila"
        else:
            if self.es_float():
                codigo += f"\n    fstp qword [{self.nombre[1]}]  ; guardar float en variable"
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
    def __init__(self, izquierda, operador, derecha):
        self.izquierda = izquierda
        self.derecha   = derecha
        self.operador  = operador   # token OPERATOR

    def es_float(self):
        def _es(nodo):
            if isinstance(nodo, NodoNumero):   return nodo.es_float()
            if isinstance(nodo, NodoIdent):    return nodo.es_float()
            if isinstance(nodo, NodoOperacion): return nodo.es_float()
            return False
        return _es(self.izquierda) or _es(self.derecha)

    def generarCodigo(self):
        codigo = []
        if self.es_float():
            codigo.append(self.izquierda.generarCodigo())
            codigo.append(self.derecha.generarCodigo())
            op = self.operador[1]
            if op == "+": codigo.append("    faddp               ; ST(1)+ST(0), pop")
            elif op == "-": codigo.append("    fsubrp              ; ST(1)-ST(0), pop")
            elif op == "*": codigo.append("    fmulp               ; ST(1)*ST(0), pop")
            elif op == "/": codigo.append("    fdivrp              ; ST(1)/ST(0), pop")
        else:
            codigo.append(self.izquierda.generarCodigo())
            codigo.append("    push   eax")
            codigo.append(self.derecha.generarCodigo())
            codigo.append("    mov    ebx, eax")
            codigo.append("    pop    eax")
            op = self.operador[1]
            if op == "+":   codigo.append("    add    eax, ebx")
            elif op == "-": codigo.append("    sub    eax, ebx")
            elif op == "*": codigo.append("    imul   eax, ebx")
            elif op == "/":
                codigo.append("    xor    edx, edx")
                codigo.append("    idiv   ebx")
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
            tok = "FLOAT" if "." in str(v) else "INTEGER"
            return NodoNumero((tok, str(int(v) if tok == "INTEGER" else v)))

        op = self.operador[1]
        # Multiplicar por 1
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 1 and op == "*": return izq
        if isinstance(izq, NodoNumero) and float(izq.valor[1]) == 1 and op == "*": return der
        # Sumar 0
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "+": return izq
        if isinstance(izq, NodoNumero) and float(izq.valor[1]) == 0 and op == "+": return der
        # División por cero
        if isinstance(der, NodoNumero) and float(der.valor[1]) == 0 and op == "/":
            raise Exception("Error: división por cero en tiempo de compilación")

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
            op_str = f"ebp {sign} {abs(self.offset)}"
            if self.es_float():
                return f"\n    fld  qword [{op_str}]  ; float -> ST(0)"
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
            lineas  = [
                f"    ; [FLOAT_CONST] {etq} dq {self.valor[1]}",
                f"    fld  qword [{etq}]  ; carga {self.valor[1]} en ST(0)",
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
    def __init__(self, valor):
        # valor: token STRING, e.g. (STRING, '"Hola mundo"')
        self.valor = valor

    def traducirPy(self):
        return self.valor[1]   # ya tiene las comillas

    def traducirRuby(self):
        return self.valor[1]

    def traducirRust(self):
        return self.valor[1]

    def generarCodigo(self):
        raise NotImplementedError("NodoString: usa NodoImprimir para generar código asm")


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
        codigo = [
            f"    push {self.etiqueta}   ; puntero al string",
            f"    call printf",
            f"    add esp, 4             ; cdecl: caller limpia",
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
    _contador = 0

    def __init__(self, tipo, argumentos):
        self.tipo       = tipo        # token KEYWORD (printf / puts)
        self.argumentos = argumentos  # lista de nodos (normalmente 1)
        NodoImprimir._contador += 1
        self.etiqueta = f"fmt_{NodoImprimir._contador}"

    def generarCodigo(self):
        # Si el argumento es un NodoString, empujamos la dirección del string
        arg = self.argumentos[0] if self.argumentos else None
        if isinstance(arg, NodoString):
            # La etiqueta se declara en .data
            codigo = [
                f"    push {self.etiqueta}",
                f"    call printf",
                f"    add esp, 4",
            ]
        else:
            # Expresión numérica: printf("%d\n", valor)
            codigo = []
            if arg:
                codigo.append(arg.generarCodigo())
                codigo.append("    push eax")
            codigo.append(f"    push fmt_int")
            codigo.append(f"    call printf")
            codigo.append(f"    add esp, {8 if arg else 4}")
        return "\n".join(codigo)

    def obtenerDato(self):
        """Para NodoString emite la etiqueta en .data."""
        arg = self.argumentos[0] if self.argumentos else None
        if isinstance(arg, NodoString):
            texto = arg.valor[1].strip('"')
            nl    = ", 10" if self.tipo[1] == "puts" else ""
            return f'    {self.etiqueta} db "{texto}"{nl}, 0'
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
            op_str = f"ebp {sign} {abs(self.offset)}"
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
        if hasattr(self, 'offset') and self.offset is not None:
            sign = "+" if self.offset > 0 else "-"
            op_str = f"ebp {sign} {abs(self.offset)}"
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
