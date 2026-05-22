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
    cmp    eax, ebx
    setg  al
    movzx  eax, al
    cmp eax, 0
    je  if_else_3
    mov eax, [ebp - 12]
    push eax
    push fmt_int
    call printf
    add esp, 8
    push 0
    call fflush
    add esp, 4
    jmp if_fin_3
if_else_3:
    mov eax, 0
    push eax
    push fmt_int
    call printf
    add esp, 8
    push 0
    call fflush
    add esp, 4
if_fin_3:
    mov eax, 0  ; valor de retorno en eax
    mov esp, ebp
    pop ebp
    ret