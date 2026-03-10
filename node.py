class NodoAST:
    #Clase de los nodos del Arbol de sintaxis trivial
    pass

def traducirPy(self):
  #Traducción de C a Python
  raise NotImplementedError("Método traducirPy() no implementado en este Nodo")
def traducirRuby(self):
  #Traducción de C a Ruby
  raise NotImplementedError("Método traducirRuby() no implementado en este Nodo")
def traducirRust(self):
  #Traducción de C a Rust
  raise NotImplementedError("Método traducirRust() no implementado en este Nodo")
def generarCodigo():
  #Traducción de c++ a Assembler
  raise NotImplementedError("Método generarCodigo() no implementado en este Nodo")

class NodoPrograma(NodoAST):
  def __init__(self, funciones, main):
    self.variables = []
    self.funciones = funciones
    self.main = main

  def generarCodigo(self):
    codigo = ["section .text", "global_start"]
    data = ["section .bss"]
    #Generar codigo de todas las funciones
    for funcion in self.funciones:
      codigo.append(funcion.generarCodigo())
      self.variables.append((funcion.cuerpo[0].tipo[1], funcion.cuerpo[0].nombre[1]))
      if len(funcion.parametros) > 0 :
        for parametro in funcion.parametros:
          self.variables.append((parametro.tipo[1], parametro.nombre[1]))
    #Generar el punto de entrada del programa
    codigo.append("_start:")
    codigo.append(self.main.generarCodigo())

    #Finalización del programa
    codigo.append("     mov eax, 1")
    codigo.append("     xor ebx, ebx")
    codigo.append("     int 0x80")

    #Sección de reserva de memoria para las variables
    for variable in self.variables:
      if variable[0] == "int":
        data.append(f"    {variable[1]}: resd 1")
      elif variable[0]  == "float":
        data.append(f"     {variable[1]}: res")
    codigo = "\n".join(codigo)
    data = "\n".join(data)
    return f"{data}\n{codigo}"

  def traducirRust(self):
    rust_code = []
    for func in self.funciones:
      rust_code.append(func.traducirRust())
    if self.main:
      rust_code.append(self.main.traducirRust())
    return "\n\n".join(rust_code)

class NodoFuncion(NodoAST):
    #Nodo que representa la funcion
    def __init__(self, tipo, nombre, parametros, cuerpo):
      self.tipo = tipo
      self.nombre = nombre
      self.parametros = parametros
      self.cuerpo = cuerpo

    def generarCodigo(self):
      codigo = f"{self.nombre[1]}:\n"
      if len(self.parametros) > 0:
        #TODO: Guardar en pila registro AX
        for parametro in self.parametros:
          codigo += "\n    pop eax"
          codigo += f"\n   mov {parametro.nombre[1]}"
      codigo +="\n".join(c.generarCodigo() for c in self.cuerpo)
      codigo +="\n    ret  \n"
      return codigo


    def traducirPy(self):
      params = ", ".join(p.traducirPy() for p in self.parametros)
      cuerpo = "\n  ".join(c.traducirPy() for c in self.cuerpo)
      return f"def {self.nombre[1]}({params}):\n  {cuerpo}"

    def traducirRuby(self):
      params = ", ".join(p.traducirRuby() for p in self.parametros)
      cuerpo = "\n  ".join(c.traducirRuby() for c in self.cuerpo)
      return f"def {self.nombre[1]}({params})\n  {cuerpo}\nend"

    def traducirRust(self):
      params = ", ".join(p.traducirRust() for p in self.parametros)
      cuerpo = "\n    ".join(c.traducirRust() for c in self.cuerpo)
      ret_type = " -> i32" if self.tipo[1] == "int" else ""
      return f"fn {self.nombre[1]}({params}){ret_type} {{\n    {cuerpo}\n}}"

class NodoParametro(NodoAST):
    def __init__(self, tipo, nombre):
        self.tipo = tipo
        self.nombre = nombre

    def traducirPy(self):
      return self.nombre[1]
    def traducirRuby(self):
      return self.nombre[1]
    def traducirRust(self):
      # En Rust el tipo va después del nombre: nombre: tipo
      rust_type = "i32" if self.tipo[1] == "int" else self.tipo[1]
      return f"{self.nombre[1]}: {rust_type}"

class NodoAsignacion(NodoAST):
    def __init__(self, tipo, nombre, expresion):
        self.tipo = tipo
        self.nombre = nombre
        self.expresion = expresion

    def generarCodigo(self):
      codigo = self.expresion.generarCodigo()
      codigo += f"\n    mov [{self.nombre[1]}, eax]"
      return codigo

    def traducirPy(self):
      return f"{self.nombre[1]} = {self.expresion.traducirPy()}"
    def traducirRuby(self):
      return f"{self.nombre[1]} = {self.expresion.traducirRuby()}"
    def traducirRust(self):
      return f"let {self.nombre[1]} = {self.expresion.traducirRust()};"

class NodoOperacion(NodoAST):
    def __init__(self, izquierda, operador, derecha):
        self.izquierda = izquierda
        self.derecha = derecha
        self.operador = operador
    def generarCodigo(self):
      codigo = []
      codigo.append(self.izquierda.generarCodigo())
      codigo.append("    push   eax")
      codigo.append(self.derecha.generarCodigo())
      codigo.append("    mov    ebx, eax")
      codigo.append("    pop    eax")
      if self.operador[1] == "+":
        codigo.append("    add    eax, ebx")
      elif self.operador[1] == "-":
        codigo.append("    sub    eax, ebx")
      elif self.operador[1] == "*":
        codigo.append("    imul   eax, ebx")
      elif self.operador[1] == "/":
        codigo.append("    xor    edx, edx")
        codigo.append("    idiv   ebx")
      return "\n".join(codigo)

    def traducirPy(self):
      return f"{self.izquierda.traducirPy()} {self.operador[1]} {self.derecha.traducirPy()}"
    def traducirRuby(self):
      return f"{self.izquierda.traducirRuby()} {self.operador[1]} {self.derecha.traducirRuby()}"
    def traducirRust(self):
      return f"{self.izquierda.traducirRust()} {self.operador[1]} {self.derecha.traducirRust()}"

class NodoRetorno(NodoAST):
    def __init__(self, expresion ):
        self.expresion = expresion

    def generarCodigo(self):
      codigo = self.expresion.generarCodigo()

    def traducirPy(self):
      return f"return {self.expresion.traducirPy()}"
    def traducirRuby(self):
      return f"return {self.expresion.traducirRuby()}"
    def traducirRust(self):
      return f"return {self.expresion.traducirRust()};"

class NodoIdent(NodoAST):
    def __init__(self, nombre):
        self.nombre = nombre

    def generarCodigo(self):
      return f"\n    mov eax, [{self.nombre[1]}]"

    def traducirPy(self):
      return self.nombre[1]
    def traducirRuby(self):
      return self.nombre[1]
    def traducirRust(self):
      return self.nombre[1]

class NodoNumero(NodoAST):
    def __init__(self, valor):
        self.valor = valor

    def generarCodigo(self):
      return f"\n    mov eax, {self.valor[1]}"
    def traducirPy(self):
        return self.valor[1]
    def traducirRuby(self):
       return self.valor[1]
    def traducirRust(self):
       return self.valor[1]

class NodoLlamadaFuncion():
  def __init__(self, nombref, argumentos):
    self.nombre_funcion = nombref
    self.argumentos = argumentos
  def traducirPy(self):
    args = ", ".join(a.traducirPy() for a in self.argumentos)
    return f"{self.nombre_funcion}({args})"
  def traducirRust(self):
    args = ", ".join(a.traducirRust() for a in self.argumentos)
    return f"{self.nombre_funcion}({args})"

class NodoInstruccion(NodoAST):
    def __init__(self, tipo, argumentos):
        self.tipo_instruccion = tipo
        self.argumentos_instruccion = argumentos

    def traducirPy(self):
        if self.tipo_instruccion[1] == 'cout':
            args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirPy() for a in self.argumentos_instruccion)
            return f"print({args})"
        return ""
    def traducirRuby(self):
        if self.tipo_instruccion[1] == 'cout':
            args = ", ".join(a if isinstance(a, str) else a.traducirRuby() for a in self.argumentos_instruccion)
            return f'puts "{args}"'
        return ""
    def traducirRust(self):
        if self.tipo_instruccion[1] == 'cout':
            # En Rust usamos println!
            args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirRust() for a in self.argumentos_instruccion)
            return f'println!("{{}}", {args});'
        return ""
    
class NodoPrint(NodoAST):
    """
    Nodo para:
      print("texto")      →  sin salto de línea
      println("texto")    →  con salto de línea
    """
    def __init__(self, tipo_print, argumentos):
        # tipo_print: token KEYWORD con valor 'print' o 'println'
        self.tipo_print = tipo_print
        self.argumentos = argumentos  # lista de strings / nodos

    def traducirPy(self):
        args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirPy() for a in self.argumentos)
        if self.tipo_print[1] == "println":
            return f"print({args})"          # print en Python ya agrega \n
        else:
            return f"print({args}, end='')"  # sin salto

    def traducirRuby(self):
        args = " ".join(a if isinstance(a, str) else a.traducirRuby() for a in self.argumentos)
        if self.tipo_print[1] == "println":
            return f'puts "{args}"'
        else:
            return f'print "{args}"'

    def traducirRust(self):
        args = ", ".join(f'"{a}"' if isinstance(a, str) else a.traducirRust() for a in self.argumentos)
        if self.tipo_print[1] == "println":
            return f'println!("{{}}", {args});'
        else:
            return f'print!("{{}}", {args});'


class NodoWhile(NodoAST):
    """
    Nodo para:
      while (condicion) { cuerpo }
    """
    def __init__(self, condicion, cuerpo):
        self.condicion = condicion
        self.cuerpo = cuerpo

    def traducirPy(self):
        cond = self.condicion.traducirPy()
        cuerpo = "\n    ".join(c.traducirPy() for c in self.cuerpo)
        return f"while {cond}:\n    {cuerpo}"

    def traducirRuby(self):
        cond = self.condicion.traducirRuby()
        cuerpo = "\n  ".join(c.traducirRuby() for c in self.cuerpo)
        return f"while {cond}\n  {cuerpo}\nend"

    def traducirRust(self):
        cond = self.condicion.traducirRust()
        cuerpo = "\n    ".join(c.traducirRust() for c in self.cuerpo)
        return f"while {cond} {{\n    {cuerpo}\n}}"


class NodoFor(NodoAST):
    """
    Nodo para:
      for (inicio; condicion; incremento) { cuerpo }
    """
    def __init__(self, inicio, condicion, incremento, cuerpo):
        self.inicio = inicio          # NodoAsignacion (sin tipo, reutilizamos)
        self.condicion = condicion    # NodoOperacion / NodoIdent
        self.incremento = incremento  # string con la expresión de incremento
        self.cuerpo = cuerpo

    def traducirPy(self):
        # Python no tiene for C-style; lo convertimos a while
        inicio = self.inicio.traducirPy()
        cond = self.condicion.traducirPy()
        inc = self.incremento
        cuerpo = "\n    ".join(c.traducirPy() for c in self.cuerpo)
        return f"{inicio}\nwhile {cond}:\n    {cuerpo}\n    {inc}"

    def traducirRuby(self):
        inicio = self.inicio.traducirRuby()
        cond = self.condicion.traducirRuby()
        inc = self.incremento
        cuerpo = "\n  ".join(c.traducirRuby() for c in self.cuerpo)
        return f"{inicio}\nwhile {cond}\n  {cuerpo}\n  {inc}\nend"

    def traducirRust(self):
        inicio = self.inicio.traducirRust()
        cond = self.condicion.traducirRust()
        inc = self.incremento
        cuerpo = "\n    ".join(c.traducirRust() for c in self.cuerpo)
        return f"{inicio}\nwhile {cond} {{\n    {cuerpo}\n    {inc};\n}}"


class NodoIf(NodoAST):
    """
    Nodo para:
      if (condicion) { cuerpo_if }
      if (condicion) { cuerpo_if } else { cuerpo_else }
    """
    def __init__(self, condicion, cuerpo_if, cuerpo_else=None):
        self.condicion = condicion
        self.cuerpo_if = cuerpo_if
        self.cuerpo_else = cuerpo_else  # puede ser None

    def traducirPy(self):
        cond = self.condicion.traducirPy()
        cuerpo_if = "\n    ".join(c.traducirPy() for c in self.cuerpo_if)
        resultado = f"if {cond}:\n    {cuerpo_if}"
        if self.cuerpo_else:
            cuerpo_else = "\n    ".join(c.traducirPy() for c in self.cuerpo_else)
            resultado += f"\nelse:\n    {cuerpo_else}"
        return resultado

    def traducirRuby(self):
        cond = self.condicion.traducirRuby()
        cuerpo_if = "\n  ".join(c.traducirRuby() for c in self.cuerpo_if)
        resultado = f"if {cond}\n  {cuerpo_if}"
        if self.cuerpo_else:
            cuerpo_else = "\n  ".join(c.traducirRuby() for c in self.cuerpo_else)
            resultado += f"\nelse\n  {cuerpo_else}"
        resultado += "\nend"
        return resultado

    def traducirRust(self):
        cond = self.condicion.traducirRust()
        cuerpo_if = "\n    ".join(c.traducirRust() for c in self.cuerpo_if)
        resultado = f"if {cond} {{\n    {cuerpo_if}\n}}"
        if self.cuerpo_else:
            cuerpo_else = "\n    ".join(c.traducirRust() for c in self.cuerpo_else)
            resultado += f" else {{\n    {cuerpo_else}\n}}"
        return resultado