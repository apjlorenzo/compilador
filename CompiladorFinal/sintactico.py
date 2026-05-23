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
    Analizador sintÃ¡ctico descendente-recursivo.
    Genera un AST a partir de la lista de tokens producida por el lÃ©xico.

    GramÃ¡tica soportada (resumen):
        programa      â†’ funcion*
        funcion       â†’ KEYWORD IDENTIFIER '(' params? ')' '{' cuerpo '}'
        params        â†’ (KEYWORD IDENTIFIER (',' KEYWORD IDENTIFIER)*)
        cuerpo        â†’ instruccion*
        instruccion   â†’ retorno | asignacion | if | while | for
                       | cout | print | println | printf | puts | scanf
                       | llamadaFuncion ';'
        asignacion    â†’ KEYWORD IDENTIFIER '=' expresion ';'
        expresion     â†’ termino (OPERATOR termino)*
        termino       â†’ NUMBER | FLOAT | INTEGER | STRING | IDENTIFIER ('(' args ')')?
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
                f"Linea {tok[2]}: se esperaba {self._nombre_tipo(tipo_esperado)}, pero se encontro '{tok[1]}'"
            )
        raise SyntaxError(f"El codigo termino inesperadamente. Se esperaba {self._nombre_tipo(tipo_esperado)}")

    def _nombre_tipo(self, tipo):
        return {
            "KEYWORD": "una palabra reservada como int, float, while o for",
            "IDENTIFIER": "un identificador de variable",
            "OPERATOR": "un operador",
            "DELIMITER": "un simbolo como (, ), {, } o ;",
            "STRING": "una cadena de texto",
            "INTEGER": "un numero entero",
            "FLOAT": "un numero decimal",
            "NUMBER": "un numero",
        }.get(tipo, tipo)

    def coincidir_numero(self):
        """Acepta INTEGER, FLOAT o NUMBER (compatibilidad con lÃ©xico viejo)."""
        tok = self.obtener_token()
        if tok and tok[0] in ("INTEGER", "FLOAT", "NUMBER"):
            self.pos += 1
            return tok
        if tok:
            raise SyntaxError(f"Linea {tok[2]}: se esperaba un numero, pero se encontro '{tok[1]}'")
        raise SyntaxError("El codigo termino inesperadamente. Se esperaba un numero")

    def coincidir_valor(self, valor):
        """Avanza si el token actual tiene el valor indicado."""
        tok = self.obtener_token()
        if tok and tok[1] == valor:
            self.pos += 1
            return tok
        previo = self.tokens[self.pos - 1] if self.pos > 0 else None
        if tok and valor == ";" and previo and previo[2] < tok[2]:
            columna = previo[3] + len(str(previo[1]))
            raise SyntaxError(
                f"Linea {previo[2]}: falta ';' al final de la instruccion"
            )
        if tok:
            raise SyntaxError(f"Linea {tok[2]}: se esperaba '{valor}', pero se encontro '{tok[1]}'")
        raise SyntaxError(f"El codigo termino inesperadamente. Se esperaba '{valor}'")

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
    # FunciÃ³n
    # -----------------------------------------------------------------------

    def funcion(self):
        tipo_retorno   = self.coincidir("KEYWORD")
        nombre_funcion = self.coincidir("IDENTIFIER")
        self.coincidir_valor("(")
        parametros = []
        if nombre_funcion[1] != "main":
            tok = self.obtener_token()
            if tok and tok[1] != ")":
                parametros = self.parametros()
        self.coincidir_valor(")")
        self.coincidir_valor("{")
        cuerpo = self.cuerpo()
        self.coincidir_valor("}")
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
    # Cuerpo de funciÃ³n / bloque
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
            elif t == "IDENTIFIER":
                sig = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                if sig and sig[0] == "OPERATOR" and sig[1] in ("++", "--"):
                    instrucciones.append(self.instruccion_incremento())
                elif sig and sig[0] == "OPERATOR" and sig[1] in ("+", "-"):
                    raise SyntaxError(f"Linea {tok[2]}: incremento incompleto. Usa {tok[1]}++ o {tok[1]}--")
                else:
                    instrucciones.append(self.reasignacion())
            else:                              instrucciones.append(self.asignacion())
        return instrucciones

    # -----------------------------------------------------------------------
    # Instrucciones
    # -----------------------------------------------------------------------

    def asignacion(self):
        tipo   = self.coincidir("KEYWORD")
        nombre = self.coincidir("IDENTIFIER")
        self.tabla_tipos[nombre[1]] = tipo[1]
        if self.obtener_token() and self.obtener_token()[1] == ";":
            expresion = self._valor_default(tipo, nombre)
        else:
            self.coincidir_valor("=")
            expresion = self.expresion()
        self.coincidir_valor(";")
        nodo = NodoAsignacion(tipo, nombre, expresion)
        nodo.es_declaracion = True
        return nodo

    def _valor_default(self, tipo, nombre):
        if tipo[1] == "float":
            return NodoNumero(("FLOAT", "0.0", nombre[2], nombre[3]))
        if tipo[1] == "string":
            return NodoString(("STRING", '""', nombre[2], nombre[3]))
        return NodoNumero(("INTEGER", "0", nombre[2], nombre[3]))

    def reasignacion(self):
        """ReasignaciÃ³n sin declaraciÃ³n de tipo: variable = expresion;"""
        nombre = self.coincidir("IDENTIFIER")
        # Tipo inferido de la tabla
        tipo_str = self.tabla_tipos.get(nombre[1], "int")
        tipo_sintetico = ("KEYWORD", tipo_str)
        self.coincidir_valor("=")
        expresion = self.expresion()
        self.coincidir_valor(";")
        nodo = NodoAsignacion(tipo_sintetico, nombre, expresion)
        nodo.es_declaracion = False
        return nodo

    def instruccion_incremento(self):
        nombre = self.coincidir("IDENTIFIER")
        operador = self.coincidir("OPERATOR")
        self.coincidir_valor(";")
        return NodoIncremento(nombre, operador)

    def retorno(self):
        self.coincidir("KEYWORD")       # return
        expresion = self.expresion()
        self.coincidir_valor(";")
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
        self.coincidir_valor(";")
        return NodoInstruccion(keyword, [" ".join(contenido)])

    def instruccion_print(self):
        keyword = self.coincidir("KEYWORD")   # print / println
        self.coincidir_valor("(")

        tok = self.obtener_token()
        if tok and tok[0] == "STRING":
            # Variante moderna: STRING ya tokenizado
            texto = self.coincidir("STRING")[1].strip('"').strip("'")
            self.coincidir_valor(")")
            self.coincidir_valor(";")
            return NodoPrint(keyword, [texto])
        elif tok and tok[0] in ("IDENTIFIER", "INTEGER", "FLOAT", "NUMBER"):
            # Soporte para imprimir variables y expresiones numericas
            expresion = self.expresion()
            self.coincidir_valor(")")
            self.coincidir_valor(";")
            return NodoImprimir(keyword, [expresion])
        else:
            # Variante legado: comilla como DELIMITER, recolectar hasta cierre
            delim_ap = self.coincidir("DELIMITER")
            char_cierre = delim_ap[1]
            contenido = []
            while self.obtener_token() and self.obtener_token()[1] != char_cierre:
                contenido.append(self.obtener_token()[1])
                self.pos += 1
            self.coincidir("DELIMITER")       # cierre comilla
            self.coincidir_valor(")")
            self.coincidir_valor(";")
            texto = " ".join(contenido)
            return NodoPrint(keyword, [texto])

    # --- printf(expr); / puts(expr); (estilo inge) ---
    def instruccion_printf(self):
        keyword = self.coincidir("KEYWORD")   # printf / puts
        self.coincidir_valor("(")
        argumentos = [self.expresion()]       # printf(expr) o printf("%d", expr)
        if self.obtener_token() and self.obtener_token()[1] == ",":
            self.coincidir_valor(",")
            argumentos.append(self.expresion())
        self.coincidir_valor(")")
        self.coincidir_valor(";")
        return NodoImprimir(keyword, argumentos)

    # --- scanf("%d", variable); ---
    def instruccion_scanf(self):
        keyword = self.coincidir("KEYWORD")   # scanf
        self.coincidir_valor("(")
        formato  = self.termino()             # NodoString con "%d" etc.
        self.coincidir_valor(",")
        variable = self.coincidir("IDENTIFIER")
        self.coincidir_valor(")")
        self.coincidir_valor(";")
        return NodoEntrada(keyword, formato, variable)

    # --- while (cond) { cuerpo } ---
    def instruccion_while(self):
        self.coincidir("KEYWORD")             # while
        self.coincidir_valor("(")
        if self.obtener_token() and self.obtener_token()[1] == ")":
            tok = self.obtener_token()
            raise SyntaxError(f"Linea {tok[2]}: while necesita una condicion, por ejemplo while (i <= 5)")
        condicion = self.expresion()
        self.coincidir_valor(")")
        self.coincidir_valor("{")
        cuerpo = self.cuerpo()
        self.coincidir_valor("}")
        return NodoWhile(condicion, cuerpo)

    # --- for (tipo var = expr; cond; var++ / var--) { cuerpo } ---
    def instruccion_for(self):
        self.coincidir("KEYWORD")             # for
        self.coincidir_valor("(")

        tok = self.obtener_token()
        if not tok:
            raise SyntaxError("El codigo termino inesperadamente dentro del for")
        if tok[1] == ";":
            raise SyntaxError(f"Linea {tok[2]}: for necesita inicializacion, por ejemplo int i = 0 o i = 0")
        if tok[0] == "KEYWORD":
            inicio = self.asignacion()
        elif tok[0] == "IDENTIFIER":
            inicio = self.reasignacion()
        else:
            raise SyntaxError(f"Linea {tok[2]}: inicializacion invalida en for. Usa int i = 0 o i = 0")

        if self.obtener_token() and self.obtener_token()[1] == ";":
            tok = self.obtener_token()
            raise SyntaxError(f"Linea {tok[2]}: for necesita una condicion, por ejemplo i <= 10")
        condicion = self.expresion()
        self.coincidir_valor(";")

        incremento = self._incremento_for()
        self.coincidir_valor(")")
        self.coincidir_valor("{")
        cuerpo = self.cuerpo()
        self.coincidir_valor("}")
        return NodoFor(inicio, condicion, incremento, cuerpo)

    def _incremento_for(self):
        tok = self.obtener_token()
        if not tok:
            raise SyntaxError("El codigo termino inesperadamente en el incremento del for")
        if tok[1] == ")":
            raise SyntaxError(f"Linea {tok[2]}: for necesita incremento, por ejemplo i++ o i--")
        if tok[0] != "IDENTIFIER":
            raise SyntaxError(f"Linea {tok[2]}: incremento invalido en for. Usa i++ o i--")
        nombre_inc = self.coincidir("IDENTIFIER")
        op_tok = self.obtener_token()
        if not op_tok or op_tok[0] != "OPERATOR":
            raise SyntaxError(f"Linea {nombre_inc[2]}: incremento invalido. Usa {nombre_inc[1]}++ o {nombre_inc[1]}--")
        if op_tok[1] in ("++", "--"):
            self.coincidir("OPERATOR")
            return NodoIncremento(nombre_inc, op_tok)
        if op_tok[1] in ("+", "-"):
            raise SyntaxError(f"Linea {op_tok[2]}: incremento incompleto. Usa {nombre_inc[1]}++ o {nombre_inc[1]}--")
        raise SyntaxError(f"Linea {op_tok[2]}: incremento invalido. Usa {nombre_inc[1]}++ o {nombre_inc[1]}--")

    # --- if (cond) { ... } [else { ... }] ---
    def instruccion_if(self):
        self.coincidir("KEYWORD")             # if
        self.coincidir_valor("(")
        condicion = self.expresion()
        self.coincidir_valor(")")
        self.coincidir_valor("{")
        cuerpo_if = self.cuerpo()
        self.coincidir_valor("}")
        cuerpo_else = None
        if self.obtener_token() and self.obtener_token()[1] == "else":
            self.coincidir("KEYWORD")         # else
            self.coincidir_valor("{")
            cuerpo_else = self.cuerpo()
            self.coincidir_valor("}")
        return NodoIf(condicion, cuerpo_if, cuerpo_else)

    # -----------------------------------------------------------------------
    # Expresiones
    # -----------------------------------------------------------------------

    def expresion(self):
        izquierda = self.expresion_aditiva()
        while (self.obtener_token()
               and self.obtener_token()[0] == "OPERATOR"
               and self.obtener_token()[1] in ("<", ">", "<=", ">=", "==", "!=")):
            operador  = self.coincidir("OPERATOR")
            derecha   = self.expresion_aditiva()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def expresion_aditiva(self):
        izquierda = self.expresion_multiplicativa()
        while (self.obtener_token()
               and self.obtener_token()[0] == "OPERATOR"
               and self.obtener_token()[1] in ("+", "-")):
            operador = self.coincidir("OPERATOR")
            derecha = self.expresion_multiplicativa()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def expresion_multiplicativa(self):
        izquierda = self.termino()
        while (self.obtener_token()
               and self.obtener_token()[0] == "OPERATOR"
               and self.obtener_token()[1] in ("*", "/")):
            operador = self.coincidir("OPERATOR")
            derecha = self.termino()
            izquierda = NodoOperacion(izquierda, operador, derecha)
        return izquierda

    def termino(self):
        tok = self.obtener_token()
        if not tok:
            raise SyntaxError("Se esperaba un tÃ©rmino pero el cÃ³digo terminÃ³ inesperadamente")

        if tok[0] == "OPERATOR" and tok[1] == "-":
            operador = self.coincidir("OPERATOR")
            derecha = self.termino()
            return NodoOperacion(NodoNumero(("INTEGER", "0", tok[2], tok[3])), operador, derecha)

        # Literal numÃ©rico
        if tok[0] in ("INTEGER", "FLOAT", "NUMBER"):
            return NodoNumero(self.coincidir_numero())

        # Literal de cadena (para printf/puts/scanf)
        if tok[0] == "STRING":
            return NodoString(self.coincidir("STRING"))

        if tok[0] == "DELIMITER" and tok[1] == "(":
            self.coincidir_valor("(")
            expr = self.expresion()
            self.coincidir_valor(")")
            return expr

        # Identificador (variable o llamada a funciÃ³n)
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

        raise SyntaxError(f"LÃ­nea {tok[2]}, Columna {tok[3]}: ExpresiÃ³n no vÃ¡lida: {tok[1]}")

    def _argumentos(self):
        """Lista de argumentos en una llamada a funciÃ³n."""
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
                raise SyntaxError(f"LÃ­nea {tok[2]}, Columna {tok[3]}: Argumento no vÃ¡lido: {tok[1]}")
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
            "programa" : getattr(nodo, "nombre_programa", "noname"),
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
