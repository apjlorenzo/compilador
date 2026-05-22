section .data
    fmt_int db "%d", 10, 0
    fmt_scanf db "%d", 0
    fmt_nl db 10, 0
section .bss
extern printf
extern scanf
section .text
global main
main:
    push ebp
    mov ebp, esp
    sub esp, 16  ; reservar memoria local
    mov eax, 100
    mov  dword [ebp - 4], eax  ; guardar int en pila
    mov eax, 25
    push   eax
    mov eax, 3
    mov    ebx, eax
    pop    eax
    imul   eax, ebx
    mov  dword [ebp - 8], eax  ; guardar int en pila
    mov eax, [ebp - 4]
    push   eax
    mov eax, [ebp - 8]
    mov    ebx, eax
    pop    eax
    sub    eax, ebx
    mov  dword [ebp - 12], eax  ; guardar int en pila
    mov eax, [ebp - 12]
    push   eax
    mov eax, 10
    mov    ebx, eax
    pop    eax
    cmp eax, 0
    je  if_else_1
    mov eax, [ebp - 12]
    push eax
    push fmt_int
    call printf
    add esp, 8
    jmp if_fin_1
if_else_1:
    mov eax, 0
    push eax
    push fmt_int
    call printf
    add esp, 8
if_fin_1:
    mov eax, 0  ; valor de retorno en eax
    xor eax, eax       ; valor de retorno 0
    mov esp, ebp
    pop ebp
    ret