from node import *
from lexico import *
import json

# Analizador sintactico 
class Parser:
  def __init__(self, tokens):
    self.tokens = tokens
    self.pos = 0

  def obtener_token(self):
    return self.tokens[self.pos] if self.pos < len(self.tokens) else None

  def coincidir(self, tipo_esperado):
    token_actual = self.obtener_token()
    if token_actual and token_actual[0] == tipo_esperado:
      self.pos += 1
      return token_actual
    else:
      raise SyntaxError(f"Error sintáctico: Se esperaba {tipo_esperado} pero se encontró: {token_actual}")

  def parsear(self):
    programa = self.construccion_programa()
    return programa

  def construccion_programa(self):
    funciones = []
    main_node = None

    while self.obtener_token():
      func_actual = self.funcion()
      if func_actual.nombre[1] == "main":
        main_node = func_actual
      else:
        funciones.append(func_actual)

    return NodoPrograma(funciones, main_node)

  def funcion(self):
    tipo_retorno = self.coincidir('KEYWORD')
    nombre_funcion = self.coincidir('IDENTIFIER')
    self.coincidir('DELIMITER') # (

    parametros = []
    if nombre_funcion[1] != "main":
      if self.obtener_token() and self.obtener_token()[1] != ")":
        parametros = self.parametros()

    self.coincidir('DELIMITER') # )
    self.coincidir('DELIMITER') # {
    cuerpo = self.cuerpo()
    self.coincidir('DELIMITER') # }
    return NodoFuncion(tipo_retorno, nombre_funcion, parametros, cuerpo)

  def parametros(self):
    lista_parametros = []
    tipo = self.coincidir("KEYWORD")
    nombre = self.coincidir('IDENTIFIER')
    lista_parametros.append(NodoParametro(tipo, nombre))

    while self.obtener_token() and self.obtener_token()[1] == ',':
      self.coincidir("DELIMITER")
      tipo = self.coincidir("KEYWORD")
      nombre = self.coincidir('IDENTIFIER')
      lista_parametros.append(NodoParametro(tipo, nombre))
    return lista_parametros

  def cuerpo(self):
    instrucciones = []
    while self.obtener_token() and self.obtener_token()[1] != '}':
      token_actual = self.obtener_token()
      if token_actual[1] == 'return':
        instrucciones.append(self.retorno())
      elif token_actual[1] == 'cout':
        instrucciones.append(self.impresionPantalla())
      else:
        instrucciones.append(self.asignacion())
    return instrucciones

  def asignacion(self):
    tipo = self.coincidir('KEYWORD')
    nombre = self.coincidir('IDENTIFIER')
    operador = self.coincidir('OPERATOR')
    expresion = self.expresion()
    self.coincidir('DELIMITER')
    return NodoAsignacion(tipo, nombre, expresion)

  def retorno(self):
    self.coincidir('KEYWORD')
    expresion = self.expresion()
    self.coincidir('DELIMITER')
    return NodoRetorno(expresion)

  def expresion(self):
    izquierda = self.termino()
    while self.obtener_token() and self.obtener_token()[0] == "OPERATOR":
      operador = self.coincidir("OPERATOR")
      derecha = self.termino()
      izquierda = NodoOperacion(izquierda, operador, derecha)
    return izquierda

  def termino(self):
    token = self.obtener_token()
    if token and token[0] == "NUMBER":
      return NodoNumero(self.coincidir("NUMBER"))
    elif token and token[0] == "IDENTIFIER":
      identificador = self.coincidir("IDENTIFIER")
      if self.obtener_token() and self.obtener_token()[1] == "(":
        self.coincidir("DELIMITER")
        argumentos = []
        if self.obtener_token() and self.obtener_token()[1] != ")":
            argumentos = self.llamadaFuncion()
        self.coincidir("DELIMITER")
        return NodoLlamadaFuncion(identificador[1], argumentos)
      else:
        return NodoIdent(identificador)
    else:
      raise SyntaxError(f"Expresión no válida: {token}")

  def llamadaFuncion(self):
    argumentos = []
    sigue = True
    while sigue:
      token = self.obtener_token()
      if token[0] == "NUMBER":
        argumento = NodoNumero(self.coincidir("NUMBER"))
      elif token[0] == "IDENTIFIER":
        argumento = NodoIdent(self.coincidir("IDENTIFIER"))
      else:
        raise SyntaxError(f"Se esperaba IDENTIFICADOR|NUMERO pero se encontró: {token}")
      argumentos.append(argumento)
      if self.obtener_token() and self.obtener_token()[1] == ",":
        self.coincidir("DELIMITER")
        sigue = True
      else:
        sigue = False
    return argumentos

  def impresionPantalla(self):
    keyword = self.coincidir("KEYWORD")
    self.coincidir("OPERATOR")
    delimitador_apertura = self.coincidir("DELIMITER")
    char_cierre = delimitador_apertura[1]
    contenido = []
    while self.obtener_token() and self.obtener_token()[1] != char_cierre:
      contenido.append(self.obtener_token()[1])
      self.pos += 1
    self.coincidir("DELIMITER")
    self.coincidir("DELIMITER")
    return NodoInstruccion(keyword, [" ".join(contenido)])
  
def imprimir_ast(nodo):
    if nodo is None:
      return None
    if isinstance(nodo, NodoPrograma):
      return {
              "programa" : "Noname",
              "funciones": [imprimir_ast(f) for f in nodo.funciones],
              "main" : imprimir_ast(nodo.main)}
    elif isinstance(nodo, NodoFuncion):
      return { "funcion" : nodo.nombre[1],
               "parametros" : [imprimir_ast(p) for p in nodo.parametros],
               "cuerpo" : [imprimir_ast(c) for c in nodo.cuerpo]}
    elif(isinstance(nodo, NodoParametro)):
      return {"id" : nodo.nombre[1],
              "tipo" : nodo.tipo[1]}
    elif(isinstance(nodo, NodoAsignacion)):
      return {"tipo" : "asignacion",
              "variable" : nodo.nombre[1],
              "expresion" : imprimir_ast(nodo.expresion)}
    elif isinstance(nodo, NodoOperacion):
      return {"op" : nodo.operador[1],
              "izq" : imprimir_ast(nodo.izquierda),
              "der" : imprimir_ast(nodo.derecha)}
    elif isinstance(nodo, NodoRetorno):
      return {"tipo" : "return",
              "valor" : imprimir_ast(nodo.expresion)}
    elif isinstance(nodo, NodoIdent):
      return nodo.nombre[1]
    elif isinstance(nodo, NodoNumero):
      return int(nodo.valor[1]) if nodo.valor[1].isdigit() else nodo.valor[1]
    elif isinstance(nodo, NodoLlamadaFuncion):
      return {"tipo": "llamada_funcion", "nombre": nodo.nombre_funcion, "argumentos": [imprimir_ast(a) for a in nodo.argumentos]}
    elif isinstance(nodo, NodoInstruccion):
      return {"tipo" : nodo.tipo_instruccion[1]
          ,"instruccion" : nodo.argumentos_instruccion}
    return None