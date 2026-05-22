section .data
    fmt_int db "%d", 10, 0
    fmt_str db "%s", 10, 0
    fmt_scanf db "%d", 0
    fmt_nl db 10, 0
    str_lit_1 db "Hola Interactive!", 0
section .bss
extern printf
extern scanf
extern fflush
section .text
global main
main:
    push ebp
    mov ebp, esp
    sub esp, 16  ; reservar memoria local
    mov eax, str_lit_1
    mov  dword [ebp - 4], eax  ; guardar int en pila
    mov eax, [ebp - 4]
    push eax
    push fmt_str
    call printf
    add esp, 8
    push 0
    call fflush
    add esp, 4
    mov eax, 0  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret