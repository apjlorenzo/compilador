from html import parser
from lexico import * 
from sintactico import *


def main():
    codigo_cout = """int suma(int a, int b) {
        int c = a + b;
        cout << "Hola! No quiero hacer esto :) ";
        return c;
    }
    """
    tokensCout = identificar_tokens(codigo_cout)
    parser_cout = Parser(tokensCout)
    ast_cout = parser_cout.parsear()
    print(json.dumps(imprimir_ast(ast_cout), indent = 1))
main()
