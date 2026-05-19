section .data
    fmt_int db "%d", 10, 0
    fmt_scanf db "%d", 0

section .bss
extern printf
extern scanf
section .text
global main
main:
    push ebp
    mov ebp, esp
    sub esp, 16  ; reservar memoria local
    mov eax, 5
    mov  dword [ebp - 4], eax  ; guardar int en pila
    mov eax, [ebp - 4]
    push eax
    push fmt_int
    call printf
    add esp, 8
    mov eax, 0  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret