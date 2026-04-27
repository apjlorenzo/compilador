section .data
    msg_1 db "Operaciones con floats listas", 10, 0
    __flt_3_14 dq 3.14  ; constante float
    __flt_2_5 dq 2.5  ; constante float
section .bss
    a: resd 1  ; entero (32 bits)
    b: resd 1  ; entero (32 bits)
    c: resd 1  ; entero (32 bits)
    x: resq 1  ; flotante (64 bits)
    y: resq 1  ; flotante (64 bits)
    z: resq 1  ; flotante (64 bits)
    w: resq 1  ; flotante (64 bits)
    d: resq 1  ; flotante (64 bits)
    q: resq 1  ; flotante (64 bits)
extern printf
section .text
global main
main:
    push ebp
    mov ebp, esp

    mov eax, 10
    mov  dword [a], eax  ; guardar int en variable

    mov eax, 3
    mov  dword [b], eax  ; guardar int en variable

    mov eax, [a]
    push   eax

    mov eax, [b]
    mov    ebx, eax
    pop    eax
    add    eax, ebx
    mov  dword [c], eax  ; guardar int en variable
    fld  qword [__flt_3_14]  ; cargar 3.14 en ST(0) (FPU)
    fstp qword [x]  ; guardar float en variable
    fld  qword [__flt_2_5]  ; cargar 2.5 en ST(0) (FPU)
    fstp qword [y]  ; guardar float en variable

    fld  qword [x]  ; cargar variable float x en ST(0)

    fld  qword [y]  ; cargar variable float y en ST(0)
    faddp               ; ST(1) = ST(1) + ST(0), pop ST(0)
    fstp qword [z]  ; guardar float en variable

    fld  qword [x]  ; cargar variable float x en ST(0)

    fld  qword [y]  ; cargar variable float y en ST(0)
    fmulp               ; ST(1) = ST(1) * ST(0), pop ST(0)
    fstp qword [w]  ; guardar float en variable

    fld  qword [x]  ; cargar variable float x en ST(0)

    fld  qword [y]  ; cargar variable float y en ST(0)
    fsubrp              ; ST(1) = ST(1) - ST(0), pop ST(0)
    fstp qword [d]  ; guardar float en variable

    fld  qword [x]  ; cargar variable float x en ST(0)

    fld  qword [y]  ; cargar variable float y en ST(0)
    fdivrp              ; ST(1) = ST(1) / ST(0), pop ST(0)
    fstp qword [q]  ; guardar float en variable
    push msg_1   ; argumento: puntero al formato/string
    call printf            ; llamada a función externa printf
    add esp, 4             ; restaurar pila (cdecl: caller limpia)

    mov eax, 0  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret
