section .data
    fmt_int db "%d", 10, 0
    fmt_str db "%s", 10, 0
    fmt_scanf db "%d", 0
    fmt_nl db 10, 0
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
    mov eax, 15
    mov  dword [rbp - 4], eax  ; guardar int en pila
    mov eax, 17
    mov  dword [rbp - 8], eax  ; guardar int en pila
    mov eax, [rbp - 4]
    push   rax
    mov eax, [rbp - 8]
    mov    r10d, eax
    pop    rax
    add    eax, r10d
    mov  dword [rbp - 12], eax  ; guardar int en pila
    mov eax, [rbp - 12]
    mov edx, eax
    lea rcx, [rel fmt_int]
    call printf
    xor ecx, ecx
    call fflush
    mov eax, 0  ; valor de retorno en eax
    mov rsp, rbp
    pop rbp
    ret