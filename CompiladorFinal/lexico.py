import re

# === Análisis Léxico ===
# Patrones ordenados de mayor a menor especificidad.
# COMENTARIO, STRING y FLOAT deben ir antes que OPERATOR, IDENTIFIER e INTEGER.
token_patron = {
    # Comentarios de línea y de bloque
    "COMENTARIO": r'//[^\n]*|/\*.*?\*/',
    # Cadenas de texto entre comillas dobles
    "STRING"    : r'"[^"]*"',
    # Palabras reservadas (se amplía con printf, puts, scanf del inge)
    "KEYWORD"   : r'\b(if|else|while|for|return|int|float|void'
                  r'|cout|print|println'
                  r'|printf|puts|scanf)\b',
    # Identificadores
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    # Literales de coma flotante (ANTES que INTEGER)
    "FLOAT"     : r'\b\d+\.\d+\b',
    # Literales enteros
    "INTEGER"   : r'\b\d+\b',
    # Operadores (incluyendo ++ y -- del inge)
    "OPERATOR"  : r'\+\+|--|<<|<=|>=|==|!=|[+\-*/=<>!]',
    # Delimitadores
    "DELIMITER" : r'[(),;{}\'\"]',
    # Espacios (se descartan)
    "WHITESPACE": r'\s+',
}

def identificar_tokens(texto):
    """
    Tokeniza *texto* y devuelve una lista de tuplas (tipo, valor).
    Se descartan WHITESPACE y COMENTARIO.
    """
    patron_general = "|".join(
        f"(?P<{tok}>{pat})" for tok, pat in token_patron.items()
    )
    patron_regex = re.compile(patron_general, re.DOTALL)

    tokens_encontrados = []
    for match in patron_regex.finditer(texto):
        for tok, valor in match.groupdict().items():
            if valor is not None and tok not in ("WHITESPACE", "COMENTARIO"):
                tokens_encontrados.append((tok, valor))

    return tokens_encontrados
