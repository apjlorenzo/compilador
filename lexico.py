import re

# === Análisis Léxico ===
# Definir los patrones para los diferentes tipos de tokens
# COMENTARIO y FLOAT deben ir ANTES que OPERATOR e INTEGER respectivamente
token_patron = {
    "COMENTARIO": r'//[^\n]*|/\*.*?\*/',  # // línea completa  o  /* bloque */
    "KEYWORD"   : r'\b(if|else|while|for|return|int|float|void|cout|print|println)\b',
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    "FLOAT"     : r'\b\d+\.\d+\b',        # literales de coma flotante
    "INTEGER"   : r'\b\d+\b',             # literales enteros
    "OPERATOR"  : r'<<|<=|>=|==|!=|[+\-*/=<>]',
    "DELIMITER" : r'[(),;{}\'\"]',
    "WHITESPACE": r'\s+',
}

def identificar_tokens(texto):
    patron_general = "|".join(f"(?P<{token}>{patron})" for token, patron in token_patron.items())
    # re.DOTALL para que .* en comentarios /* */ cruce saltos de línea
    patron_regex = re.compile(patron_general, re.DOTALL)

    tokens_encontrados = []
    for match in patron_regex.finditer(texto):
        for token, valor in match.groupdict().items():
            # Ignorar espacios en blanco Y comentarios — no son tokens útiles
            if valor is not None and token not in ("WHITESPACE", "COMENTARIO"):
                tokens_encontrados.append((token, valor))

    return tokens_encontrados