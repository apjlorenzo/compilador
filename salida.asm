section .data
    msg_1 db "Hola mundo", 0
    msg_2 db "Bienvenido al compilador", 10, 0
    msg_3 db "Fin del programa", 10, 0
section .bss
extern printf
section .text
global main
main:
    push ebp
    mov ebp, esp
    push msg_1   ; argumento: puntero al formato/string
    call printf            ; llamada a función externa printf
    add esp, 4             ; restaurar pila (cdecl: caller limpia)
    push msg_2   ; argumento: puntero al formato/string
    call printf            ; llamada a función externa printf
    add esp, 4             ; restaurar pila (cdecl: caller limpia)
    push msg_3   ; argumento: puntero al formato/string
    call printf            ; llamada a función externa printf
    add esp, 4             ; restaurar pila (cdecl: caller limpia)

    mov eax, 0  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret
