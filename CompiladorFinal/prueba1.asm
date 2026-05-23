section .data
    fmt_int db "%d", 10, 0
    fmt_str db "%s", 10, 0
    fmt_scanf db "%d", 0
    fmt_nl db 10, 0
    __flt_5_2 dq 5.2  ; constante float
    __flt_0_2 dq 0.2  ; constante float
section .bss
extern printf
extern scanf
extern fflush
section .text
global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 64  ; locales y shadow space Win64
    fld  qword [__flt_5_2]  ; carga 5.2 en ST(0)
    fstp qword [rbp - 8]  ; guardar float en pila
    fld  qword [__flt_0_2]  ; carga 0.2 en ST(0)
    fstp qword [rbp - 16]  ; guardar float en pila
    fld  qword [rbp - 8]  ; float -> ST(0)
    fld  qword [rbp - 16]  ; float -> ST(0)
    fdivrp              ; ST(1)/ST(0), pop
    fstp qword [rbp - 24]  ; guardar float en pila
    fld  qword [rbp - 24]  ; float -> ST(0)
    mov edx, eax
    lea rcx, [rel fmt_int]
    call printf
    xor ecx, ecx
    call fflush
    mov eax, 0  ; valor de retorno en eax
    mov rsp, rbp
    pop rbp
    ret