section .data
    fmt_int db "%d", 10, 0
    fmt_str db "%s", 10, 0
    fmt_scanf db "%d", 0
    fmt_nl db 10, 0
    str_lit_1 db "hola", 0
section .bss
extern printf
extern scanf
extern fflush
section .text
global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 48  ; locales y shadow space Win64
    lea rax, [rel str_lit_1]
    mov  qword [rbp - 8], rax  ; guardar puntero string en pila
    mov rax, [rbp - 8]
    mov  dword [rbp - 12], eax  ; guardar int en pila
    mov eax, 0  ; valor de retorno en eax
    mov rsp, rbp
    pop rbp
    ret