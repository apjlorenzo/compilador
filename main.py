from lexico import identificar_tokens
from sintactico import Parser, imprimir_ast
import json

def main():
    codigo = """
    int suma(int a, int b) {
        int c = a + b;
        cout << "Resultado: ";
        return c;
    }

    int main() {
        int x = 5;
        int y = 10;

        print("Iniciando programa");
        println("Bienvenido al compilador");

        if (x < y) {
            println("x es menor que y");
        } else {
            println("x es mayor o igual que y");
        }

        while (x < y) {
            println("dentro del while");
            int x = x + 1;
        }

        for (int i = 0; i < 5; i = i + 1) {
            println("iteracion del for");
        }

        return 0;
    }
    """

    tokens = identificar_tokens(codigo)
    print("TOKENS ENCONTRADOS")
    for t in tokens:
        print(t)

    print("\n ARBOL SINTÁCTICO (AST)")
    parser = Parser(tokens)
    ast = parser.parsear()
    print(json.dumps(imprimir_ast(ast), indent=2, ensure_ascii=False))

main()