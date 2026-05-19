"""
semantico.py — Análisis semántico del compilador.

Mantiene la estructura completa de mi compilador (RAR) con:
  - TablaSimbolos con soporte de ámbitos anidados (pila de scopes)
  - AnalizadorSemantico con inferencia de tipos, detección de errores y avisos
  - Soporte para NodoImprimir, NodoIncremento y NodoEntrada (del inge)
"""

from node import (
    NodoPrograma, NodoFuncion, NodoParametro, NodoAsignacion,
    NodoOperacion, NodoRetorno, NodoIdent, NodoNumero, NodoString,
    NodoLlamadaFuncion, NodoInstruccion, NodoPrint, NodoImprimir,
    NodoWhile, NodoFor, NodoIf, NodoIncremento, NodoEntrada,
)


# ===========================================================================
# TABLA DE SÍMBOLOS
# ===========================================================================

class Simbolo:
    """Una entrada en la tabla de símbolos."""

    def __init__(self, nombre, tipo, clase, ambito):
        self.nombre = nombre   # str
        self.tipo   = tipo     # "int" | "float" | "void" | "int|params…"
        self.clase  = clase    # "funcion" | "parametro" | "variable_local" | "variable_control"
        self.ambito = ambito   # nombre de la función contenedora
        self.usado  = False    # se marca True cuando la variable es leída
        self.offset = None     # offset respecto a EBP (positivo para params, negativo para locales)


class TablaSimbolos:
    """
    Tabla de símbolos con soporte de ámbitos anidados (pila de scopes).

    _pila    : lista de dicts { nombre -> Simbolo }, uno por ámbito abierto.
    _global  : dict de funciones declaradas (ámbito global).
    _historial: lista plana con todos los símbolos en orden de inserción.
    """

    def __init__(self):
        self._pila      = []
        self._global    = {}
        self._historial = []

    # --- Ámbitos -----------------------------------------------------------

    def entrar_ambito(self, nombre):
        self._pila.append({"__nombre__": nombre})

    def salir_ambito(self):
        if self._pila:
            self._pila.pop()

    @property
    def ambito_actual(self):
        return self._pila[-1]["__nombre__"] if self._pila else "global"

    # --- Inserción ---------------------------------------------------------

    def insertar(self, simbolo):
        """Devuelve False si el símbolo ya existe en el ámbito actual."""
        if simbolo.clase == "funcion":
            if simbolo.nombre in self._global:
                return False
            self._global[simbolo.nombre] = simbolo
        else:
            scope = self._pila[-1] if self._pila else self._global
            if simbolo.nombre in scope:
                return False
            scope[simbolo.nombre] = simbolo
        self._historial.append(simbolo)
        return True

    # --- Búsqueda ----------------------------------------------------------

    def buscar(self, nombre):
        """Busca desde el scope más interno hacia el global."""
        for scope in reversed(self._pila):
            if nombre in scope:
                return scope[nombre]
        return self._global.get(nombre, None)

    def buscar_funcion(self, nombre):
        return self._global.get(nombre, None)

    # --- Presentación ------------------------------------------------------

    def imprimir(self):
        ancho = 74
        print("=" * ancho)
        print(" TABLA DE SÍMBOLOS ".center(ancho))
        print("=" * ancho)

        print("\n[ FUNCIONES ]")
        print(f"  {'Nombre':<20} {'Tipo retorno':<14} {'Parámetros'}")
        print("  " + "-" * (ancho - 2))
        funciones = [s for s in self._historial if s.clase == "funcion"]
        if funciones:
            for s in funciones:
                partes   = s.tipo.split("|")
                tipo_ret = partes[0]
                params   = partes[1] if len(partes) > 1 else "(ninguno)"
                print(f"  {s.nombre:<20} {tipo_ret:<14} {params}")
        else:
            print("  (sin funciones declaradas)")

        print("\n[ VARIABLES Y PARÁMETROS ]")
        print(f"  {'Nombre':<18} {'Tipo':<8} {'Clase':<22} {'Ámbito':<16} {'Usado'}")
        print("  " + "-" * (ancho - 2))
        vars_ = [s for s in self._historial if s.clase != "funcion"]
        if vars_:
            for s in vars_:
                print(f"  {s.nombre:<18} {s.tipo:<8} {s.clase:<22} {s.ambito:<16} {'sí' if s.usado else 'no'}")
        else:
            print("  (sin variables declaradas)")

        print("\n" + "=" * ancho)

    def como_dict(self):
        """Serializa la tabla a un diccionario (útil para la GUI)."""
        return {
            "funciones": [
                {
                    "nombre"  : s.nombre,
                    "tipo"    : s.tipo.split("|")[0],
                    "params"  : s.tipo.split("|")[1] if "|" in s.tipo else "",
                    "ambito"  : s.ambito,
                }
                for s in self._historial if s.clase == "funcion"
            ],
            "variables": [
                {
                    "nombre": s.nombre,
                    "tipo"  : s.tipo,
                    "clase" : s.clase,
                    "ambito": s.ambito,
                    "usado" : s.usado,
                }
                for s in self._historial if s.clase != "funcion"
            ],
        }


# ===========================================================================
# ERRORES Y ADVERTENCIAS
# ===========================================================================

class ErrorSemantico:
    ETIQUETAS = {
        "VAR_NO_DECLARADA"  : "Variable no declarada",
        "VAR_YA_DECLARADA"  : "Variable ya declarada en este ámbito",
        "FUNC_NO_DECLARADA" : "Función no declarada",
        "FUNC_YA_DECLARADA" : "Función ya declarada",
        "TIPO_INCOMPATIBLE" : "Tipos incompatibles",
        "DIVISION_CERO"     : "División por cero",
        "RETORNO_TIPO"      : "Tipo de retorno incompatible",
    }

    def __init__(self, codigo, mensaje, ambito):
        self.codigo  = codigo
        self.mensaje = mensaje
        self.ambito  = ambito

    def __str__(self):
        etq = self.ETIQUETAS.get(self.codigo, self.codigo)
        return f"  [ERROR]  {etq:<30} | {self.mensaje}  (ámbito: {self.ambito})"


class AdvertenciaSemantica:
    def __init__(self, codigo, mensaje, ambito):
        self.codigo  = codigo
        self.mensaje = mensaje
        self.ambito  = ambito

    def __str__(self):
        return f"  [AVISO]  {'Advertencia':<30} | {self.mensaje}  (ámbito: {self.ambito})"


# ===========================================================================
# ANALIZADOR SEMÁNTICO
# ===========================================================================

class AnalizadorSemantico:
    """
    Recorre el AST y aplica:
      1. Declaración antes de uso
      2. Redeclaración en el mismo ámbito
      3. Compatibilidad de tipos (int + float → aviso de promoción)
      4. División por cero literal
      5. Variables declaradas y no usadas → aviso
      6. Llamadas a funciones no declaradas
      7. Tipo de retorno incompatible
      8. Soporte para NodoImprimir (printf/puts), NodoIncremento, NodoEntrada
    """

    def __init__(self):
        self.tabla        = TablaSimbolos()
        self.errores      = []
        self.avisos       = []
        self._func_actual = None
        self.offset_local = 0
        self.offset_param = 8

    # --- Punto de entrada --------------------------------------------------

    def analizar(self, ast):
        self._registrar_funciones(ast)
        for funcion in ast.funciones:
            self._analizar_funcion(funcion)
        if ast.main:
            self._analizar_funcion(ast.main)
        self._verificar_no_usadas()
        return self.tabla, self.errores, self.avisos

    # --- Paso 1: registrar cabeceras (permite llamadas adelantadas) ---------

    def _registrar_funciones(self, ast):
        todas = list(ast.funciones) + ([ast.main] if ast.main else [])
        for fn in todas:
            nombre   = fn.nombre[1]
            tipo_ret = fn.tipo[1]
            params   = ", ".join(f"{p.tipo[1]} {p.nombre[1]}" for p in fn.parametros) or "ninguno"
            sim = Simbolo(nombre, f"{tipo_ret}|{params}", "funcion", "global")
            if not self.tabla.insertar(sim):
                self._err("FUNC_YA_DECLARADA", f"Función '{nombre}' ya declarada", "global")

    # --- Análisis de función -----------------------------------------------

    def _analizar_funcion(self, nodo):
        nombre = nodo.nombre[1]
        self._func_actual = nodo
        self.tabla.entrar_ambito(nombre)
        
        self.offset_local = 0
        self.offset_param = 8
        
        for p in nodo.parametros:
            sim = Simbolo(p.nombre[1], p.tipo[1], "parametro", nombre)
            size = 8 if p.tipo[1] == "float" else 4
            sim.offset = self.offset_param
            self.offset_param += size
            
            if not self.tabla.insertar(sim):
                self._err("VAR_YA_DECLARADA",
                           f"Parámetro '{p.nombre[1]}' duplicado en '{nombre}'", nombre)
                           
        self._analizar_cuerpo(nodo.cuerpo, nombre)
        self.tabla.salir_ambito()
        self._func_actual = None
        
        # Guardar en el nodo los bytes necesarios para locales (alineado a 16)
        nodo.local_bytes = (self.offset_local + 15) & ~15

    # --- Análisis de lista de instrucciones --------------------------------

    def _analizar_cuerpo(self, instrucciones, ambito):
        for inst in instrucciones:
            self._analizar_inst(inst, ambito)

    def _analizar_inst(self, inst, ambito):
        if isinstance(inst, NodoAsignacion):
            self._analizar_asignacion(inst, ambito)

        elif isinstance(inst, NodoRetorno):
            tipo_expr = self._tipo_expr(inst.expresion, ambito)
            if self._func_actual and tipo_expr:
                tipo_fn = self._func_actual.tipo[1]
                if tipo_fn != "void" and tipo_fn != tipo_expr:
                    if set([tipo_fn, tipo_expr]) == {"int", "float"}:
                        self._avi("RETORNO_TIPO",
                                   f"Retorno '{tipo_expr}' en función '{tipo_fn}' (conversión implícita)",
                                   ambito)
                    else:
                        self._err("RETORNO_TIPO",
                                   f"Retorno '{tipo_expr}' incompatible con '{tipo_fn}'", ambito)

        elif isinstance(inst, NodoWhile):
            self._tipo_expr(inst.condicion, ambito)
            self.tabla.entrar_ambito(f"{ambito}::while")
            self._analizar_cuerpo(inst.cuerpo, ambito)
            self.tabla.salir_ambito()

        elif isinstance(inst, NodoFor):
            self.tabla.entrar_ambito(f"{ambito}::for")
            if isinstance(inst.inicio, NodoAsignacion):
                self._analizar_asignacion(inst.inicio, ambito, "variable_control")
            self._tipo_expr(inst.condicion, ambito)
            # Verificar variable del incremento
            if isinstance(inst.incremento, NodoIncremento):
                sim = self.tabla.buscar(inst.incremento.nombre[1])
                if sim:
                    sim.usado = True
                    inst.incremento.sim_clase = sim.clase
                    inst.incremento.offset = sim.offset
            self._analizar_cuerpo(inst.cuerpo, ambito)
            self.tabla.salir_ambito()

        elif isinstance(inst, NodoIf):
            self._tipo_expr(inst.condicion, ambito)
            self.tabla.entrar_ambito(f"{ambito}::if")
            self._analizar_cuerpo(inst.cuerpo_if, ambito)
            self.tabla.salir_ambito()
            if inst.cuerpo_else:
                self.tabla.entrar_ambito(f"{ambito}::else")
                self._analizar_cuerpo(inst.cuerpo_else, ambito)
                self.tabla.salir_ambito()

        elif isinstance(inst, NodoLlamadaFuncion):
            self._verificar_llamada(inst, ambito)

        elif isinstance(inst, NodoImprimir):
            for arg in inst.argumentos:
                if not isinstance(arg, NodoString):
                    self._tipo_expr(arg, ambito)

        elif isinstance(inst, NodoEntrada):
            sim = self.tabla.buscar(inst.variable[1])
            if sim is None:
                self._err("VAR_NO_DECLARADA",
                           f"Variable '{inst.variable[1]}' usada en scanf sin declarar", ambito)
            else:
                sim.usado = True
                inst.sim_clase = sim.clase
                inst.offset = sim.offset

    # --- Asignación --------------------------------------------------------

    def _analizar_asignacion(self, nodo, ambito, clase="variable_local"):
        nombre    = nodo.nombre[1]
        tipo_decl = nodo.tipo[1]
        sim = Simbolo(nombre, tipo_decl, clase, ambito)
        
        # Calcular offset si no está declarado
        existente = self.tabla.buscar(nombre)
        if existente and existente.ambito == ambito:
            sim = existente
        else:
            size = 8 if tipo_decl == "float" else 4
            self.offset_local += size
            sim.offset = -self.offset_local
        
        nodo.sim_clase = sim.clase
        nodo.offset = sim.offset
        
        if not self.tabla.insertar(sim):
            self._err("VAR_YA_DECLARADA",
                       f"Variable '{nombre}' ya declarada en '{ambito}'", ambito)
        tipo_expr = self._tipo_expr(nodo.expresion, ambito)
        if tipo_expr and tipo_decl != tipo_expr:
            if set([tipo_decl, tipo_expr]) == {"int", "float"}:
                self._avi("TIPO_INCOMPATIBLE",
                           f"Asignación de '{tipo_expr}' a '{tipo_decl} {nombre}' (conversión implícita)",
                           ambito)
            else:
                self._err("TIPO_INCOMPATIBLE",
                           f"No se puede asignar '{tipo_expr}' a '{tipo_decl} {nombre}'", ambito)

    # --- Inferencia de tipo ------------------------------------------------

    def _tipo_expr(self, nodo, ambito):
        if nodo is None:
            return None

        if isinstance(nodo, NodoNumero):
            tok = nodo.valor[0]
            return "float" if (tok == "FLOAT" or
                               (tok == "NUMBER" and "." in nodo.valor[1])) else "int"

        if isinstance(nodo, NodoString):
            return "string"

        if isinstance(nodo, NodoIdent):
            sim = self.tabla.buscar(nodo.nombre[1])
            if sim is None:
                self._err("VAR_NO_DECLARADA",
                           f"Variable '{nodo.nombre[1]}' usada sin declarar", ambito)
                return None
            sim.usado = True
            nodo.sim_clase = sim.clase
            nodo.offset = sim.offset
            return sim.tipo

        if isinstance(nodo, NodoOperacion):
            ti = self._tipo_expr(nodo.izquierda, ambito)
            td = self._tipo_expr(nodo.derecha,   ambito)
            if nodo.operador[1] == "/" and isinstance(nodo.derecha, NodoNumero):
                if float(nodo.derecha.valor[1]) == 0.0:
                    self._err("DIVISION_CERO", "División por cero detectada", ambito)
            if ti is None or td is None:
                return None
            if ti == td:
                return ti
            if set([ti, td]) == {"int", "float"}:
                self._avi("TIPO_INCOMPATIBLE",
                           f"Operación 'int {nodo.operador[1]} float' — se promueve a float",
                           ambito)
                return "float"
            return ti

        if isinstance(nodo, NodoLlamadaFuncion):
            return self._verificar_llamada(nodo, ambito)

        return None

    # --- Llamadas a función ------------------------------------------------

    def _verificar_llamada(self, nodo, ambito):
        sim = self.tabla.buscar_funcion(nodo.nombre_funcion)
        if sim is None:
            self._err("FUNC_NO_DECLARADA",
                       f"Llamada a función no declarada '{nodo.nombre_funcion}'", ambito)
            return None
        sim.usado = True
        for arg in nodo.argumentos:
            self._tipo_expr(arg, ambito)
        return sim.tipo.split("|")[0]

    # --- Variables no usadas -----------------------------------------------

    def _verificar_no_usadas(self):
        for sim in self.tabla._historial:
            if sim.clase in ("variable_local", "parametro") and not sim.usado:
                self._avi("VAR_NO_USADA",
                           f"'{sim.tipo} {sim.nombre}' declarada pero nunca usada",
                           sim.ambito)

    # --- Helpers -----------------------------------------------------------

    def _err(self, codigo, mensaje, ambito):
        self.errores.append(ErrorSemantico(codigo, mensaje, ambito))

    def _avi(self, codigo, mensaje, ambito):
        self.avisos.append(AdvertenciaSemantica(codigo, mensaje, ambito))


# ===========================================================================
# PRESENTACIÓN DE RESULTADOS
# ===========================================================================

def imprimir_resultado_semantico(errores, avisos):
    ancho = 74
    print("=" * ancho)
    print(" ANÁLISIS SEMÁNTICO ".center(ancho))
    print("=" * ancho)

    if errores:
        print(f"\n[ ERRORES ({len(errores)}) ]")
        for e in errores:
            print(e)
    else:
        print("\n[ ERRORES ]")
        print("  Sin errores semánticos. ✓")

    if avisos:
        print(f"\n[ ADVERTENCIAS ({len(avisos)}) ]")
        for a in avisos:
            print(a)
    else:
        print("\n[ ADVERTENCIAS ]")
        print("  Sin advertencias.")

    print("\n" + "=" * ancho)

    if errores:
        raise SystemExit(
            f"\nAnálisis semántico fallido — {len(errores)} error(es) encontrado(s)."
        )
    print("\nAnálisis semántico completado sin errores.")
