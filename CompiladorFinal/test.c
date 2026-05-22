#include <stdio.h>
int main() {
    int balance = 100;
    int costo = 25 * 3;
    int restante = balance - costo;
    if (restante > 10) {
        printf(restante);
    } else {
        printf(0);
    }
    return 0;
}