import json
from node import (
    NodoPrograma, NodoFuncion, NodoParametro, NodoAsignacion,
    NodoOperacion, NodoRetorno, NodoIdent, NodoNumero, NodoString,
    NodoLlamadaFuncion, NodoInstruccion, NodoPrint, NodoImprimir,
    NodoWhile, NodoFor, NodoIf, NodoIncremento, NodoEntrada,
)
from lexico import identificar_tokens


class Parser:
    """
    Analizador sintáctico descendente-recursivo.
    Genera un AST a partir de la lista de tokens producida por el léxico.

    Gramática soportada (resumen):
        programa      → funcion*
        funcion       → KEYWORD IDENTIFIER '(' params? ')' '{' cuerpo '}'
        params        → (KEYWORD IDENTIFIER (',' KEYWORD IDENTIFIER)*)
        cuerpo        → instruccion*
        instruccion   → retorno | asignacion | if | while | for
                       | cout | print | println | printf | puts | scanf
                       | llamadaFuncion ';'
        asignacion    → KEYWORD IDENTIFIER '=' expresion ';'
        expresion     → termino (OPERATOR termino)*
        termino       → NUMBER | FLOAT | INTEGER | STRING | IDENTIFIER ('(' args ')')?
    """

    def __init__(self, tokens):
        self.tokens     = tokens
        self.pos        = 0
        # Tabla de tipos declarados: { nombre_var: "int" | "float" | "string" }
        # El parser la construye para inyectar el tipo en NodoIdent
        self.tabla_tipos = {}
        self.tiene_stdio = False

    # -----------------------------------------------------------------------
    # Utilidades de recorrido
    # -----------------------------------------------------------------------

    def obtener_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def coincidir(self, tipo_esperado):
        tok = self.obtener_token()
        if tok and tok[0] == tipo_esperado:
            self.pos += 1
            return tok
        if tok:
            raise SyntaxError(
                f"Línea {tok[2]}, Columna {tok[3]}: Se esperaba '{tipo_esperado}' pero se encontró '{tok[0]}': {tok[1]}"
            )
        raise SyntaxError(f"Se esperaba '{tipo_esperado}' pero el código terminó inesperadamente")

    def coincidir_numero(self):
        """Acepta INTEGER, FLOAT o NUMBER (compatibilidad con léxico viejo)."""
        tok = self.obtener_token()
        if tok and tok[0] in ("INTEGER", "FLOAT", "NUMBER"):
            self.pos += 1
            return tok
        if tok:
            raise SyntaxError(f"Línea {tok[2]}, Columna {tok[3]}: Se esperaba número pero se encontró '{tok[0]}': {tok[1]}")
        raise SyntaxError("Se esperaba número pero el código terminó inesperadamente")

    def coincidir_valor(self, valor):
        """Avanza si el token actual tiene el valor indicado."""
        tok = self.obtener_token()
        if tok and tok[1] == valor:
            self.pos += 1
            return tok
        if tok:
            raise SyntaxError(f"Línea {tok[2]}, Columna {tok[3]}: Se esperaba '{valor}' pero se encontró '{tok[1]}'")
        raise SyntaxError(f"Se esperaba '{valor}' pero el código terminó inesperadamente")

    # -----------------------------------------------------------------------
    # Punto de entrada
    # -----------------------------------------------------------------------

    def parsear(self):
        return self.construccion_programa()

    def construccion_programa(self):
        funciones  = []
        main_node  = None
        while self.obtener_token():
            if self.obtener_token()[0] == "INCLUDE":
                self.tiene_stdio = True
                self.pos += 1
                continue
            func = self.funcion()
            if func.nombre[1] == "main":
                main_node = func
            else:
                funciones.append(func)
        programa = NodoPrograma(funciones, main_node)
        programa.tiene_stdio = self.tiene_stdio
        return programa

    # -----------------------------------------------------------------------
    # Función
    # -----------------------------------------------------------------------

    def funcion(self):
        tipo_retorno   = self.coincidir("KEYWORD")
        nombre_funcion = self.coincidir("IDENTIFIER")
        self.coincidir("DELIMITER")   # (
        parametros = []
        if nombre_funcion[1] != "main":
            tok = self.obtener_token()
            if tok and tok[1] != ")":
                parametros = self.parametros()
        self.coincidir("DELIMITER")   # )
        self.coincidir("DELIMITER")   # {
        cuerpo = self.cuerpo()
        self.coincidir("DELIMITER")   # }
        return NodoFuncion(tipo_retorno, nombre_funcion, parametros, cuerpo)

    def parametros(self):
        lista = []
        tipo  = self.coincidir("KEYWORD")
        nombre = self.coincidir("IDENTIFIER")
        self.tabla_tipos[nombre[1]] = tipo[1]
        lista.append(NodoParametro(tipo, nombre))
        while self.obtener_token() and self.obtener_token()[1] == ",":
            self.coincidir("DELIMITER")
            tipo  = self.coincidir("KEYWORD")
            nombre = self.coincidir("IDENTIFIER")
            self.tabla_tipos[nombre[1]] = tipo[1]
            lista.append(NodoParametro(tipo, nombre))
        return lista

    # -----------------------------------------------------------------------
    # Cuerpo de función / bloque
    # -----------------------------------------------------------------------

    def cuerpo(self):
        instrucciones = []
        while self.obtener_token() and self.obtener_token()[1] != "}":
            tok = self.obtener_token()
            v   = tok[1]
            t   = tok[0]
            if   v == "return":                instrucciones.append(self.retorno())
            elif v == "cout":                  instrucciones.append(self.impresion_cout())
            elif v in ("print", "println"):    instrucciones.append(self.instruccion_print())
            elif v in ("printf", "puts"):      instrucciones.append(self.instruccion_printf())
            elif v == "scanf":                 instrucciones.append(self.instruccion_scanf())
            elif v == "while":                 instrucciones.append(self.instruccion_while())
            elif v == "for":                   instrucciones.append(self.instruccion_for())
            elif v == "if":                    instrucciones.append(self.instruccion_if())
            elif t == "IDENTIFIER":            instrucciones.append(self.reasignacion())
            else:                              instrucciones.append(self.asignacion())
        return instrucciones

    # -----------------------------------------------------------------------
    # Instrucciones
    # -----------------------------------------------------------------------

    def asignacion(self):
        tipo   = self.coincidir("KEYWORD")
        nombre = self.coincidir("IDENTIFIER")
        self.tabla_tipos[nombre[1]] = tipo[1]
        self.coincidir("OPERATOR")      # =
        expresion = self.expresion()
        self.coincidir("DELIMITER")     # ;
        nodo = NodoAsignacion(tipo, nombre, expresion)
        nodo.es_declaracion = True
        return nodo

    def reasignacion(self):
        """Reasignación sin declaración de tipo: variable = expresion;"""
        nombre = self.coincidir("IDENTIFIER")
        # Tipo inferido de la tabla
        tipo_str = self.tabla_tipos.get(nombre[1], "int")
        tipo_sintetico = ("KEYWORD", tipo_str)
        self.coincidir("OPERATOR")      # =
        expresion = self.expresion()
        self.coincidir("DELIMITER")     # ;
        nodo = NodoAsignacion(tipo_sintetico, nombre, expresion)
        nodo.es_declaracion = False
        return nodo

    def retorno(self):
        self.coincidir("KEYWORD")       # return
        expresion = self.expresion()
        self.coincidir("DELIMITER")     # ;
        return NodoRetorno(expresion)

    # --- cout << "texto"; (estilo C++ simplificado, mi compilador original) ---
    def impresion_cout(self):
        keyword = self.coincidir("KEYWORD")   # cout
        self.coincidir("OPERATOR")            # <<
        delim_ap = self.coincidir("DELIMITER")
        char_cierre = delim_ap[1]
        contenido = []
        while self.obtener_token() and self.obtener_token()[1] != char_cierre:
            contenido.append(self.obtener_token()[1])
            self.pos += 1
        self.coincidir("DELIMITER")           # cierre de comilla
        self.coincidir("DELIMITER")           # ;
        return NodoInstruccion(keyword, [" ".join(contenido)])

    def instruccion_print(self):
        keyword = self.coincidir("KEYWORD")   # print / println
        self.coincidir("DELIMITER")           # (

        tok = self.obtener_token()
        if tok and tok[0] == "STRING":
            # Variante moderna: STRING ya tokenizado
            texto = self.coincidir("STRING")[1].strip('"').strip("'")
            self.coincidir("DELIMITER")       # )
            self.coincidir("DELIMITER")       # ;
            return NodoPrint(keyword, [texto])
        elif tok and tok[0] == "IDENTIFIER":
            # Soporte para imprimir variables (nuevo)
            ident = self.coincidir("IDENTIFIER")
            self.coincidir("DELIMITER")       # )
            self.coincidir("DELIMITER")       # ;
            tipo_conocido = self.tabla_tipos.get(ident[1], None)
            return NodoImprimir(keyword, [NodoIdent(ident, tipo=tipo_conocido)])
        else:
            # Variante legado: comilla como DELIMITER, recolectar hasta cierre
            delim_ap = self.coincidir("DELIMITER")
            char_cierre = delim_ap[1]
            contenido = []
            while self.obtener_token() and self.obtener_token()[1] != char_cierre:
                contenido.append(self.obtener_token()[1])
                self.pos += 1
            self.coincidir("DELIMITER")       # cierre comilla
            self.coincidir("DELIMITER")       # )
            self.coincidir("DELIMITER")       # ;
            texto = " ".join(contenido)
            return NodoPrint(keyword, [texto])

    # --- printf(expr); / puts(expr); (estilo inge) ---
    def instruccion_printf(self):
        keyword = self.coincidir("KEYWORD")   # printf / puts
        self.coincidir("DELIMITER")           # (
        arg = self.termino()                  # NodoString o expresión
        self.coincidir("DELIMITER")           # )
        self.coincidir("DELIMITER")           # ;
        return NodoImprimir(keyword, [arg])

    # --- scanf("%d", variable); ---
    def instruccion_scanf(self):
        keyword = self.coincidir("KEYWORD")   # scanf
        self.coincidir("DELIMITER")           # (
        formato  = self.termino()             # NodoString con "%d" etc.
        self.coincidir("DELIMITER")           # ,
        variable = self.coincidir("IDENTIFIER")
        self.coincidir("DELIMITER")           # )
        self.coincidir("DELIMITER")           # ;
        return NodoEntrada(keyword, formato, variable)

    # --- while (cond) { cuerpo } ---
    def instruccion_while(self):
        self.coincidir("KEYWORD")             # while
        self.coincidir("DELIMITER")           # (
        condicion = self.expresion()
        self.coincidir("DELIMITER")           # )
        self.coincidir("DELIMITER")           # {
        cuerpo = self.cuerpo()
        self.coincidir("DELIMITER")           # }
        return NodoWhile(condicion, cuerpo)

    # --- for (tipo var = expr; cond; var++ / var--) { cuerpo } ---
    def instruccion_for(self):
        self.coincidir("KEYWORD")             # for
        self.coincidir("DELIMITER")           # (
        # Inicialización: tipo var = expr;
        tipo_init   = self.coincidir("KEYWORD")
        nombre_init = self.coincidir("IDENTIFIER")
        self.tabla_tipos[nombre_init[1]] = tipo_init[1]
        self.coincidir("OPERATOR")            # =
        expr_init   = self.expresion()
        self.coincidir("DELIMITER")           # ;
        inicio = NodoAsignacion(tipo_init, nombre_init, expr_init)
        # Condición
        condicion = self.expresion()
        self.coincidir("DELIMITER")           # ;
        # Incremento: var++ o var-- (estilo inge) o expresión legado
        tok = self.obtener_token()
        if tok and tok[0] == "IDENTIFIER":
            nombre_inc = self.coincidir("IDENTIFIER")
            op_tok     = self.obtener_token()
            if op_tok and op_tok[1] in ("++", "--"):
                self.coincidir("OPERATOR")
                incremento = NodoIncremento(nombre_inc, op_tok)
            else:
                # Legado: recolectar hasta ')'
                partes = [nombre_inc[1]]
                while self.obtener_token() and self.obtener_token()[1] != ")":
                    partes.append(self.obtener_token()[1])
                    self.pos += 1
                incremento = " ".join(partes)
        else:
            partes = []
            while self.obtener_token() and self.obtener_token()[1] != ")":
                partes.append(self.obtener_token()[1])
                self.pos += 1
            incremento = " ".join(partes)
        self.coincidir("DELIMITER")           # )
        self.coincidir("DELIMITER")           # {
        cuerpo = self.cuerpo()
        self.coincidir("DELIMITER")           # }
        return NodoFor(inicio, condicion, incremento, cuerpo)

    # --- if (cond) { ... } [else { ... }] ---
    def instruccion_if(self):
        self.coincidir("KEYWORD")             # if
        self.coincidir("DELIMITER")           # (
        condicion = self.expresion()
        self.coincidir("DELIMITER")           # )
        self.coincidir("DELIMITER")           # {
        cuerpo_if = self.cuerpo()
        self.coincidir("DELIMITER")           # }
        cuerpo_else = None
        if self.obtener_token() and self.obtener_token()[1] == "else":
            self.coincidir("KEYWORD")         # else
            self.coincidir("DELIMITER")       # {
            cuerpo_else = self.cuerpo()
            self.coincidir("DELIMITER")       # }
        return NodoIf(condicion, cuerpo_if, cuerpo_else)

    # -----------------------------------------------------------------------
    # Expresiones
    # -----------------------------------------------------------------------

    def expresion(self):
        izquierda = self.termino()
        while self.obtener_token() and self.obtener_token()[0] == "OPERATOR":
            operador  = self.coincidir("OPERATOR")
            derecha   = self.termino()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def termino(self):
        tok = self.obtener_token()
        if not tok:
            raise SyntaxError("Se esperaba un término pero el código terminó inesperadamente")

        # Literal numérico
        if tok[0] in ("INTEGER", "FLOAT", "NUMBER"):
            return NodoNumero(self.coincidir_numero())

        # Literal de cadena (para printf/puts/scanf)
        if tok[0] == "STRING":
            return NodoString(self.coincidir("STRING"))

        # Identificador (variable o llamada a función)
        if tok[0] == "IDENTIFIER":
            ident = self.coincidir("IDENTIFIER")
            if self.obtener_token() and self.obtener_token()[1] == "(":
                self.coincidir("DELIMITER")   # (
                argumentos = []
                if self.obtener_token() and self.obtener_token()[1] != ")":
                    argumentos = self._argumentos()
                self.coincidir("DELIMITER")   # )
                return NodoLlamadaFuncion(ident[1], argumentos)
            tipo_conocido = self.tabla_tipos.get(ident[1], None)
            return NodoIdent(ident, tipo=tipo_conocido)

        raise SyntaxError(f"Línea {tok[2]}, Columna {tok[3]}: Expresión no válida: {tok[1]}")

    def _argumentos(self):
        """Lista de argumentos en una llamada a función."""
        args  = []
        while True:
            tok = self.obtener_token()
            if not tok or tok[1] == ")":
                break
            if tok[0] in ("INTEGER", "FLOAT", "NUMBER"):
                args.append(NodoNumero(self.coincidir_numero()))
            elif tok[0] == "STRING":
                args.append(NodoString(self.coincidir("STRING")))
            elif tok[0] == "IDENTIFIER":
                ident = self.coincidir("IDENTIFIER")
                tipo_conocido = self.tabla_tipos.get(ident[1], None)
                args.append(NodoIdent(ident, tipo=tipo_conocido))
            else:
                raise SyntaxError(f"Línea {tok[2]}, Columna {tok[3]}: Argumento no válido: {tok[1]}")
            if self.obtener_token() and self.obtener_token()[1] == ",":
                self.coincidir("DELIMITER")
            else:
                break
        return args


# ---------------------------------------------------------------------------
# Utilidad: serializar el AST a un diccionario (para JSON / debug)
# ---------------------------------------------------------------------------

def imprimir_ast(nodo):
    if nodo is None:
        return None
    if isinstance(nodo, NodoPrograma):
        return {
            "programa" : "Noname",
            "funciones": [imprimir_ast(f) for f in nodo.funciones],
            "main"     : imprimir_ast(nodo.main),
        }
    if isinstance(nodo, NodoFuncion):
        return {
            "funcion"   : nodo.nombre[1],
            "tipo"      : nodo.tipo[1],
            "parametros": [imprimir_ast(p) for p in nodo.parametros],
            "cuerpo"    : [imprimir_ast(c) for c in nodo.cuerpo],
        }
    if isinstance(nodo, NodoParametro):
        return {"id": nodo.nombre[1], "tipo": nodo.tipo[1]}
    if isinstance(nodo, NodoAsignacion):
        return {
            "tipo"    : "asignacion",
            "varTipo" : nodo.tipo[1],
            "variable": nodo.nombre[1],
            "expresion": imprimir_ast(nodo.expresion),
        }
    if isinstance(nodo, NodoOperacion):
        return {
            "op" : nodo.operador[1],
            "izq": imprimir_ast(nodo.izquierda),
            "der": imprimir_ast(nodo.derecha),
        }
    if isinstance(nodo, NodoRetorno):
        return {"tipo": "return", "valor": imprimir_ast(nodo.expresion)}
    if isinstance(nodo, NodoIdent):
        return nodo.nombre[1]
    if isinstance(nodo, NodoNumero):
        v = nodo.valor[1]
        return float(v) if "." in v else int(v)
    if isinstance(nodo, NodoString):
        return {"tipo": "string", "valor": nodo.valor[1]}
    if isinstance(nodo, NodoLlamadaFuncion):
        return {
            "tipo"     : "llamada",
            "nombre"   : nodo.nombre_funcion,
            "argumentos": [imprimir_ast(a) for a in nodo.argumentos],
        }
    if isinstance(nodo, NodoInstruccion):
        return {"tipo": nodo.tipo_instruccion[1], "args": nodo.argumentos_instruccion}
    if isinstance(nodo, NodoPrint):
        return {"tipo": nodo.tipo_print[1], "texto": nodo.argumentos}
    if isinstance(nodo, NodoImprimir):
        return {"tipo": nodo.tipo[1], "args": [imprimir_ast(a) for a in nodo.argumentos]}
    if isinstance(nodo, NodoWhile):
        return {
            "tipo"    : "while",
            "condicion": imprimir_ast(nodo.condicion),
            "cuerpo"  : [imprimir_ast(c) for c in nodo.cuerpo],
        }
    if isinstance(nodo, NodoFor):
        return {
            "tipo"      : "for",
            "inicio"    : imprimir_ast(nodo.inicio),
            "condicion" : imprimir_ast(nodo.condicion),
            "incremento": (imprimir_ast(nodo.incremento)
                           if isinstance(nodo.incremento, NodoAST)
                           else nodo.incremento),
            "cuerpo"    : [imprimir_ast(c) for c in nodo.cuerpo],
        }
    if isinstance(nodo, NodoIf):
        resultado = {
            "tipo"     : "if",
            "condicion": imprimir_ast(nodo.condicion),
            "cuerpo_if": [imprimir_ast(c) for c in nodo.cuerpo_if],
        }
        if nodo.cuerpo_else:
            resultado["cuerpo_else"] = [imprimir_ast(c) for c in nodo.cuerpo_else]
        return resultado
    if isinstance(nodo, NodoIncremento):
        return {"tipo": "incremento", "variable": nodo.nombre[1], "op": nodo.operador[1]}
    if isinstance(nodo, NodoEntrada):
        return {"tipo": nodo.tipo[1], "variable": nodo.variable[1]}
    return None


# Re-exportar NodoAST base para que imprimir_ast lo encuentre
from node import NodoAST
