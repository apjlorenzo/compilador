section .data
    fmt_int db "%d", 10, 0
    fmt_scanf db "%d", 0
    msg_1 db "Resultado de la suma:", 10, 0
    __flt_3_14 dq 3.14  ; constante float
    __flt_2_5 dq 2.5  ; constante float
section .bss
extern printf
extern scanf
section .text
global main
suma:
    push ebp
    mov ebp, esp
    sub esp, 16  ; reservar memoria local
    mov eax, [ebp + 8]
    push   eax
    mov eax, [ebp + 12]
    mov    ebx, eax
    pop    eax
    add    eax, ebx
    mov  dword [ebp - 4], eax  ; guardar int en pila
    mov eax, [ebp - 4]  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret
main:
    push ebp
    mov ebp, esp
    sub esp, 64  ; reservar memoria local
    mov eax, 10
    mov  dword [ebp - 4], eax  ; guardar int en pila
    mov eax, 3
    mov  dword [ebp - 8], eax  ; guardar int en pila
    fld  qword [__flt_3_14]  ; carga 3.14 en ST(0)
    fstp qword [ebp - 16]  ; guardar float en pila
    fld  qword [__flt_2_5]  ; carga 2.5 en ST(0)
    fstp qword [ebp - 24]  ; guardar float en pila
    fld  qword [ebp - 16]  ; float -> ST(0)
    fld  qword [ebp - 24]  ; float -> ST(0)
    fmulp               ; ST(1)*ST(0), pop
    fstp qword [ebp - 32]  ; guardar float en pila
    mov eax, [ebp - 8]
    push eax   ; pasar argumento a la pila
    mov eax, [ebp - 4]
    push eax   ; pasar argumento a la pila
    call suma
    add esp, 8  ; limpiar pila
    mov  dword [ebp - 36], eax  ; guardar int en pila
    push msg_1   ; puntero al string
    call printf
    add esp, 4             ; cdecl: caller limpia
    mov eax, 0
    mov  dword [ebp - 40], eax  ; guardar int en pila
while_ini_1:
    mov eax, [ebp - 40]
    push   eax
    mov eax, 3
    mov    ebx, eax
    pop    eax
    cmp eax, 0
    je  while_fin_1
    mov eax, [ebp - 40]
    push   eax
    mov eax, 1
    mov    ebx, eax
    pop    eax
    add    eax, ebx
    mov  dword [ebp - 44], eax  ; guardar int en pila
    mov eax, [ebp - 44]
    mov  dword [ebp - 40], eax  ; guardar int en pila
    jmp while_ini_1
while_fin_1:
    mov eax, [ebp - 36]
    push   eax
    mov eax, 10
    mov    ebx, eax
    pop    eax
    cmp eax, 0
    je  if_else_1
    mov eax, 1
    mov  dword [ebp - 48], eax  ; guardar int en pila
    jmp if_fin_1
if_else_1:
    mov eax, 0
    mov  dword [ebp - 52], eax  ; guardar int en pila
if_fin_1:
    mov eax, 0  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret