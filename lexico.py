import re

# === Análisis Léxico ===
# Definir los patrones para los diferentes tipos de tokens
token_patron = {
    "KEYWORD": r'\b(if|else|while|for|return|int|float|void|cout|print|println)\b',
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    "NUMBER": r'\b\d+(\.\d+)?\b',
    "OPERATOR": r'<<|<=|>=|==|!=|[+\-*/=<>]',
    "DELIMITER": r'[(),;{}\'\"]',
    "WHITESPACE": r'\s+',
}

def identificar_tokens(texto):
    # Unimos todos los patrones en un único patrón usando grupos nombrados
    patron_general = "|".join(f"(?P<{token}>{patron})" for token, patron in token_patron.items())
    patron_regex = re.compile(patron_general)

    tokens_encontrados = []
    for match in patron_regex.finditer(texto):
        for token, valor in match.groupdict().items():
            if valor is not None and token != "WHITESPACE":  # Ignoramos espacios en blanco
                tokens_encontrados.append((token, valor))

    return tokens_encontrados