"""
semantico.py â€” AnÃ¡lisis semÃ¡ntico del compilador.

Mantiene la estructura completa de mi compilador (RAR) con:
  - TablaSimbolos con soporte de Ã¡mbitos anidados (pila de scopes)
  - AnalizadorSemantico con inferencia de tipos, detecciÃ³n de errores y avisos
  - Soporte para NodoImprimir, NodoIncremento y NodoEntrada (del inge)
"""

import re

from node import (
    NodoPrograma, NodoFuncion, NodoParametro, NodoAsignacion,
    NodoOperacion, NodoRetorno, NodoIdent, NodoNumero, NodoString,
    NodoLlamadaFuncion, NodoInstruccion, NodoPrint, NodoImprimir,
    NodoWhile, NodoFor, NodoIf, NodoIncremento, NodoEntrada,
)


# ===========================================================================
# TABLA DE SÃMBOLOS
# ===========================================================================

class Simbolo:
    """Una entrada en la tabla de sÃ­mbolos."""

    def __init__(self, nombre, tipo, clase, ambito):
        self.nombre = nombre   # str
        self.tipo   = tipo     # "int" | "float" | "void" | "int|paramsâ€¦"
        self.clase  = clase    # "funcion" | "parametro" | "variable_local" | "variable_control"
        self.ambito = ambito   # nombre de la funciÃ³n contenedora
        self.usado  = False    # se marca True cuando la variable es leÃ­da
        self.offset = None     # offset respecto a EBP (positivo para params, negativo para locales)
        self.const_value = None # valor constante conocido en compilacion, si aplica


class TablaSimbolos:
    """
    Tabla de sÃ­mbolos con soporte de Ã¡mbitos anidados (pila de scopes).

    _pila    : lista de dicts { nombre -> Simbolo }, uno por Ã¡mbito abierto.
    _global  : dict de funciones declaradas (Ã¡mbito global).
    _historial: lista plana con todos los sÃ­mbolos en orden de inserciÃ³n.
    """

    def __init__(self):
        self._pila      = []
        self._global    = {}
        self._historial = []

    # --- Ãmbitos -----------------------------------------------------------

    def entrar_ambito(self, nombre):
        self._pila.append({"__nombre__": nombre})

    def salir_ambito(self):
        if self._pila:
            self._pila.pop()

    @property
    def ambito_actual(self):
        return self._pila[-1]["__nombre__"] if self._pila else "global"

    # --- InserciÃ³n ---------------------------------------------------------

    def insertar(self, simbolo):
        """Devuelve False si el sÃ­mbolo ya existe en el Ã¡mbito actual."""
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

    # --- BÃºsqueda ----------------------------------------------------------

    def buscar(self, nombre):
        """Busca desde el scope mÃ¡s interno hacia el global."""
        for scope in reversed(self._pila):
            if nombre in scope:
                return scope[nombre]
        return self._global.get(nombre, None)

    def buscar_funcion(self, nombre):
        return self._global.get(nombre, None)

    # --- PresentaciÃ³n ------------------------------------------------------

    def imprimir(self):
        ancho = 74
        print("=" * ancho)
        print(" TABLA DE SÃMBOLOS ".center(ancho))
        print("=" * ancho)

        print("\n[ FUNCIONES ]")
        print(f"  {'Nombre':<20} {'Tipo retorno':<14} {'ParÃ¡metros'}")
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

        print("\n[ VARIABLES Y PARÃMETROS ]")
        print(f"  {'Nombre':<18} {'Tipo':<8} {'Clase':<22} {'Ãmbito':<16} {'Usado'}")
        print("  " + "-" * (ancho - 2))
        vars_ = [s for s in self._historial if s.clase != "funcion"]
        if vars_:
            for s in vars_:
                print(f"  {s.nombre:<18} {s.tipo:<8} {s.clase:<22} {s.ambito:<16} {'sÃ­' if s.usado else 'no'}")
        else:
            print("  (sin variables declaradas)")

        print("\n" + "=" * ancho)

    def como_dict(self):
        """Serializa la tabla a un diccionario (Ãºtil para la GUI)."""
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
        "VAR_YA_DECLARADA"  : "Variable ya declarada en este Ã¡mbito",
        "FUNC_NO_DECLARADA" : "FunciÃ³n no declarada",
        "FUNC_YA_DECLARADA" : "FunciÃ³n ya declarada",
        "TIPO_INCOMPATIBLE" : "Tipos incompatibles",
        "DIVISION_CERO"     : "DivisiÃ³n por cero",
        "RETORNO_TIPO"      : "Tipo de retorno incompatible",
    }

    def __init__(self, codigo, mensaje, ambito, linea="?"):
        self.codigo  = codigo
        self.mensaje = mensaje
        self.ambito  = ambito
        self.linea   = linea

    def __str__(self):
        etq = self.ETIQUETAS.get(self.codigo, self.codigo)
        linea_str = f"LÃ­nea {self.linea}" if self.linea != "?" else "LÃ­nea desconocida"
        return f"  [ERROR]  {etq:<30} | {linea_str} - {self.mensaje}  (Ã¡mbito: {self.ambito})"


class AdvertenciaSemantica:
    def __init__(self, codigo, mensaje, ambito, linea="?"):
        self.codigo  = codigo
        self.mensaje = mensaje
        self.ambito  = ambito
        self.linea   = linea

    def __str__(self):
        linea_str = f"LÃ­nea {self.linea}" if self.linea != "?" else "LÃ­nea desconocida"
        return f"  [AVISO]  {'Advertencia':<30} | {linea_str} - {self.mensaje}  (Ã¡mbito: {self.ambito})"


# ===========================================================================
# ANALIZADOR SEMÃNTICO
# ===========================================================================

class AnalizadorSemantico:
    """
    Recorre el AST y aplica:
      1. DeclaraciÃ³n antes de uso
      2. RedeclaraciÃ³n en el mismo Ã¡mbito
      3. Compatibilidad de tipos (int + float â†’ aviso de promociÃ³n)
      4. DivisiÃ³n por cero literal
      5. Variables declaradas y no usadas â†’ aviso
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
        self.tiene_stdio  = False

    def _get_line(self, nodo):
        if hasattr(nodo, 'nombre') and isinstance(nodo.nombre, tuple) and len(nodo.nombre) > 2: return nodo.nombre[2]
        if hasattr(nodo, 'tipo') and isinstance(nodo.tipo, tuple) and len(nodo.tipo) > 2: return nodo.tipo[2]
        if hasattr(nodo, 'valor') and isinstance(nodo.valor, tuple) and len(nodo.valor) > 2: return nodo.valor[2]
        if hasattr(nodo, 'tipo_print') and isinstance(nodo.tipo_print, tuple) and len(nodo.tipo_print) > 2: return nodo.tipo_print[2]
        if hasattr(nodo, 'variable') and isinstance(nodo.variable, tuple) and len(nodo.variable) > 2: return nodo.variable[2]
        if hasattr(nodo, 'operador') and isinstance(nodo.operador, tuple) and len(nodo.operador) > 2: return nodo.operador[2]
        return '?'

    # --- Punto de entrada --------------------------------------------------

    def analizar(self, ast):
        self.tiene_stdio = getattr(ast, 'tiene_stdio', False)
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
                self._err("FUNC_YA_DECLARADA", f"FunciÃ³n '{nombre}' ya declarada", "global", self._get_line(fn))

    # --- AnÃ¡lisis de funciÃ³n -----------------------------------------------

    def _analizar_funcion(self, nodo):
        nombre = nodo.nombre[1]
        self._func_actual = nodo
        self.tabla.entrar_ambito(nombre)
        
        self.offset_local = 0
        self.offset_param = 8
        
        for p in nodo.parametros:
            sim = Simbolo(p.nombre[1], p.tipo[1], "parametro", nombre)
            size = 8 if p.tipo[1] in ("float", "string") else 4
            sim.offset = self.offset_param
            self.offset_param += size
            
            if not self.tabla.insertar(sim):
                self._err("VAR_YA_DECLARADA",
                           f"ParÃ¡metro '{p.nombre[1]}' duplicado en '{nombre}'", nombre, self._get_line(p))
                           
        self._analizar_cuerpo(nodo.cuerpo, nombre)
        self.tabla.salir_ambito()
        self._func_actual = None
        
        # Guardar en el nodo los bytes necesarios para locales (alineado a 16)
        nodo.local_bytes = (self.offset_local + 15) & ~15

    # --- AnÃ¡lisis de lista de instrucciones --------------------------------

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
                                   f"Retorno '{tipo_expr}' en funciÃ³n '{tipo_fn}' (conversiÃ³n implÃ­cita)",
                                   ambito, self._get_line(inst))
                    else:
                        self._err("RETORNO_TIPO",
                                   f"Retorno '{tipo_expr}' incompatible con '{tipo_fn}'", ambito, self._get_line(inst))

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
                else:
                    self._err("VAR_NO_DECLARADA",
                              f"Variable '{inst.incremento.nombre[1]}' usada en incremento sin declarar",
                              ambito, self._get_line(inst.incremento))
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

        elif isinstance(inst, NodoImprimir) or isinstance(inst, NodoPrint):
            requiere_stdio = isinstance(inst, NodoImprimir) and inst.tipo[1] in ("printf", "puts")
            if requiere_stdio and not self.tiene_stdio:
                self._err("FUNC_NO_DECLARADA", "Uso de funciÃ³n de I/O sin haber incluido <stdio.h>", ambito, self._get_line(inst))
            if isinstance(inst, NodoImprimir):
                self._validar_imprimir(inst, ambito)

        elif isinstance(inst, NodoEntrada):
            if inst.tipo[1] == "scanf" and not self.tiene_stdio:
                self._err("FUNC_NO_DECLARADA", "Uso de scanf sin haber incluido <stdio.h>", ambito, self._get_line(inst))
            sim = self.tabla.buscar(inst.variable[1])
            if sim is None:
                self._err("VAR_NO_DECLARADA",
                           f"Variable '{inst.variable[1]}' usada en scanf sin declarar", ambito, self._get_line(inst))
            else:
                sim.usado = True
                inst.sim_clase = sim.clase
                inst.offset = sim.offset

        elif isinstance(inst, NodoIncremento):
            sim = self.tabla.buscar(inst.nombre[1])
            if sim is None:
                self._err("VAR_NO_DECLARADA",
                           f"Variable '{inst.nombre[1]}' usada en incremento sin declarar", ambito, self._get_line(inst))
            elif sim.tipo not in ("int", "float"):
                self._err("TIPO_INCOMPATIBLE",
                           f"No se puede aplicar '{inst.operador[1]}' a variable '{inst.nombre[1]}' de tipo '{sim.tipo}'",
                           ambito, self._get_line(inst))
            else:
                sim.usado = True
                sim.const_value = None
                inst.sim_clase = sim.clase
                inst.offset = sim.offset
                inst._tipo = sim.tipo

    def _validar_imprimir(self, inst, ambito):
        if inst.tipo[1] == "printf" and inst.argumentos and isinstance(inst.argumentos[0], NodoString):
            formato = inst.argumentos[0].valor[1].strip('"').strip("'")
            especificadores = re.findall(r"%(?:\.\d+)?[dfs]", formato)
            valores = inst.argumentos[1:]
            if especificadores and len(valores) != len(especificadores):
                self._err("TIPO_INCOMPATIBLE",
                          f"printf espera {len(especificadores)} valor(es) para el formato '{formato}'",
                          ambito, self._get_line(inst))
            if not especificadores and valores:
                self._err("TIPO_INCOMPATIBLE",
                          f"printf recibio valores, pero el formato '{formato}' no tiene %d, %f o %s",
                          ambito, self._get_line(inst))
            for spec, arg in zip(especificadores, valores):
                tipo_arg = self._tipo_expr(arg, ambito)
                esperado = "int" if spec.endswith("d") else ("float" if spec.endswith("f") else "string")
                if tipo_arg and tipo_arg != esperado:
                    self._err("TIPO_INCOMPATIBLE",
                              f"printf usa {spec}, pero recibio '{tipo_arg}'",
                              ambito, self._get_line(inst))
            return

        for arg in inst.argumentos:
            if not isinstance(arg, NodoString):
                self._tipo_expr(arg, ambito)

    # --- AsignaciÃ³n --------------------------------------------------------

    def _analizar_asignacion(self, nodo, ambito, clase="variable_local"):
        nombre    = nodo.nombre[1]
        tipo_decl = nodo.tipo[1]
        es_declaracion = getattr(nodo, "es_declaracion", True)
        sim = Simbolo(nombre, tipo_decl, clase, ambito)
        const_expr = self._valor_constante(nodo.expresion)
        
        # Calcular offset si no estÃ¡ declarado
        existente = self.tabla.buscar(nombre)
        if not es_declaracion and existente is None:
            self._err("VAR_NO_DECLARADA",
                       f"Variable '{nombre}' reasignada sin declarar", ambito, self._get_line(nodo))
        if (not es_declaracion and existente) or (es_declaracion and existente and existente.ambito == ambito):
            sim = existente
            tipo_decl = sim.tipo
            nodo.tipo = ("KEYWORD", tipo_decl)
        else:
            size = 8 if tipo_decl in ("float", "string") else 4
            self.offset_local += size
            sim.offset = -self.offset_local
        
        nodo.sim_clase = sim.clase
        nodo.offset = sim.offset
        
        if es_declaracion and not self.tabla.insertar(sim):
            self._err("VAR_YA_DECLARADA",
                       f"Variable '{nombre}' ya declarada en '{ambito}'", ambito, self._get_line(nodo))
        tipo_expr = self._tipo_expr(nodo.expresion, ambito)
        if tipo_expr and tipo_decl != tipo_expr:
            if set([tipo_decl, tipo_expr]) == {"int", "float"}:
                self._avi("TIPO_INCOMPATIBLE",
                           f"AsignaciÃ³n de '{tipo_expr}' a '{tipo_decl} {nombre}' (conversiÃ³n implÃ­cita)",
                           ambito, self._get_line(nodo))
            else:
                self._err("TIPO_INCOMPATIBLE",
                           f"No se puede asignar '{tipo_expr}' a '{tipo_decl} {nombre}'", ambito, self._get_line(nodo))
        sim.const_value = None if const_expr == "DIVISION_CERO" else const_expr

    def _valor_constante(self, nodo):
        if isinstance(nodo, NodoNumero):
            return float(nodo.valor[1]) if nodo.es_float() else int(nodo.valor[1])
        if isinstance(nodo, NodoIdent):
            sim = self.tabla.buscar(nodo.nombre[1])
            return getattr(sim, "const_value", None) if sim else None
        if isinstance(nodo, NodoOperacion):
            izq = self._valor_constante(nodo.izquierda)
            der = self._valor_constante(nodo.derecha)
            if izq is None or der is None:
                return None
            op = nodo.operador[1]
            try:
                if op == "+": return izq + der
                if op == "-": return izq - der
                if op == "*": return izq * der
                if op == "/":
                    if float(der) == 0.0:
                        return "DIVISION_CERO"
                    return izq / der
                if op == "<": return int(izq < der)
                if op == ">": return int(izq > der)
                if op == "<=": return int(izq <= der)
                if op == ">=": return int(izq >= der)
                if op == "==": return int(izq == der)
                if op == "!=": return int(izq != der)
            except Exception:
                return None
        return None

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
                           f"Variable '{nodo.nombre[1]}' usada sin declarar", ambito, self._get_line(nodo))
                return None
            sim.usado = True
            nodo.sim_clase = sim.clase
            nodo.offset = sim.offset
            return sim.tipo

        if isinstance(nodo, NodoOperacion):
            ti = self._tipo_expr(nodo.izquierda, ambito)
            td = self._tipo_expr(nodo.derecha,   ambito)
            if nodo.operador[1] == "/":
                valor_divisor = self._valor_constante(nodo.derecha)
                if valor_divisor == "DIVISION_CERO" or valor_divisor == 0 or valor_divisor == 0.0:
                    self._err("DIVISION_CERO", "Division por cero detectada en el divisor", ambito, self._get_line(nodo))
            if ti is None or td is None:
                return None
            if ti == "string" or td == "string":
                self._err("TIPO_INCOMPATIBLE", "OperaciÃ³n aritmÃ©tica no soportada con tipo 'string'", ambito, self._get_line(nodo))
                return None
            if ti == td:
                return ti
            if set([ti, td]) == {"int", "float"}:
                self._avi("TIPO_INCOMPATIBLE",
                           f"OperaciÃ³n 'int {nodo.operador[1]} float' â€” se promueve a float",
                           ambito, self._get_line(nodo))
                return "float"
            return ti

        if isinstance(nodo, NodoLlamadaFuncion):
            return self._verificar_llamada(nodo, ambito)

        return None

    # --- Llamadas a funciÃ³n ------------------------------------------------

    def _verificar_llamada(self, nodo, ambito):
        sim = self.tabla.buscar_funcion(nodo.nombre_funcion)
        if sim is None:
            self._err("FUNC_NO_DECLARADA",
                       f"Llamada a funciÃ³n no declarada '{nodo.nombre_funcion}'", ambito, getattr(nodo, 'linea', "?"))
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
                           sim.ambito, "?")

    # --- Helpers -----------------------------------------------------------

    def _err(self, codigo, mensaje, ambito, linea="?"):
        self.errores.append(ErrorSemantico(codigo, mensaje, ambito, linea))

    def _avi(self, codigo, mensaje, ambito, linea="?"):
        self.avisos.append(AdvertenciaSemantica(codigo, mensaje, ambito, linea))


# ===========================================================================
# PRESENTACIÃ“N DE RESULTADOS
# ===========================================================================

def imprimir_resultado_semantico(errores, avisos):
    ancho = 74
    print("=" * ancho)
    print(" ANÃLISIS SEMÃNTICO ".center(ancho))
    print("=" * ancho)

    if errores:
        print(f"\n[ ERRORES ({len(errores)}) ]")
        for e in errores:
            print(e)
    else:
        print("\n[ ERRORES ]")
        print("  Sin errores semÃ¡nticos. âœ“")

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
            f"\nAnÃ¡lisis semÃ¡ntico fallido â€” {len(errores)} error(es) encontrado(s)."
        )
    print("\nAnÃ¡lisis semÃ¡ntico completado sin errores.")
