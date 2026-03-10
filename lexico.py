import re
import pandas as pd
from PyPDF2 import PdfReader

# === Análisis Léxico ===
# Definir los patrones para los diferentes tipos de tokens
token_patron = {
    "KEYWORD": r'\b(if|else|while|return|int|float|void|cout)\b',
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    "NUMBER": r'\b\d+(\.\d+)?\b',
    "OPERATOR": r'<<|[+\-*/=<>]',
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
            if valor is not None and token != "WHITESPACE": # Ignoramos espacios en blanco
                tokens_encontrados.append((token, valor))

    return tokens_encontrados



# Implementar el analizador de los tokens
#def parse(tokens):
    # Funcion auxiliar para consumir cada token
    def consume(tipo_esperado):
        global token_actual
        if token_actual[1] == tipo_esperado:
            global indice_token
            token_actual = tokens[indice_token]
            indice_token += 1
        else: # NO es el token esperado
            raise SyntaxError(f"Se esperaba {tipo_esperado} pero se encontro {token_actual[0]}")
        

