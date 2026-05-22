import re
import bisect

# === Análisis Léxico ===
# Patrones ordenados de mayor a menor especificidad.
token_patron = {
    # Include de stdio
    "INCLUDE"   : r'\#include\s*<stdio\.h>',
    # Comentarios de línea y de bloque
    "COMENTARIO": r'//[^\n]*|/\*.*?\*/',
    # Cadenas de texto entre comillas dobles
    "STRING"    : r'"[^"]*"',
    # Palabras reservadas
    "KEYWORD"   : r'\b(if|else|while|for|return|int|float|string|void'
                  r'|cout|print|println'
                  r'|printf|puts|scanf)\b',
    # Identificadores
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    # Literales de coma flotante (ANTES que INTEGER)
    "FLOAT"     : r'\b\d+\.\d+\b',
    # Literales enteros
    "INTEGER"   : r'\b\d+\b',
    # Operadores (incluyendo ++ y --)
    "OPERATOR"  : r'\+\+|--|<<|<=|>=|==|!=|[+\-*/=<>!]',
    # Delimitadores
    "DELIMITER" : r'[(),;{}\'\"]',
    # Espacios (se descartan)
    "WHITESPACE": r'\s+',
}

def identificar_tokens(texto):
    """
    Tokeniza *texto* y devuelve una lista de tuplas (tipo, valor, linea, columna).
    Se descartan WHITESPACE y COMENTARIO.
    """
    patron_general = "|".join(
        f"(?P<{tok}>{pat})" for tok, pat in token_patron.items()
    )
    patron_regex = re.compile(patron_general, re.DOTALL)

    # Calcular inicios de línea para reporte de errores
    line_starts = [0] + [m.start() + 1 for m in re.finditer(r'\n', texto)]
    
    def get_line_col(pos):
        line = bisect.bisect_right(line_starts, pos)
        col = pos - line_starts[line - 1] + 1
        return line, col

    tokens_encontrados = []
    pos = 0
    for match in patron_regex.finditer(texto):
        if match.start() != pos:
            linea, col = get_line_col(pos)
            fragmento = texto[pos:match.start()].splitlines()[0]
            raise SyntaxError(f"Línea {linea}, Columna {col}: token no reconocido '{fragmento}'")
        pos = match.end()
        for tok, valor in match.groupdict().items():
            if valor is not None and tok not in ("WHITESPACE", "COMENTARIO"):
                linea, col = get_line_col(match.start())
                tokens_encontrados.append((tok, valor, linea, col))

    if pos != len(texto):
        linea, col = get_line_col(pos)
        fragmento = texto[pos:].splitlines()[0]
        raise SyntaxError(f"Línea {linea}, Columna {col}: token no reconocido '{fragmento}'")

    return tokens_encontrados
