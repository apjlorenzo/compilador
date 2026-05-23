import http.server
import socketserver
import json
import urllib.parse
import os
import subprocess
from main import compilar_codigo, compilar_asm
import threading
import queue
import time

current_process = None
stdout_queue = queue.Queue()

def read_process_stdout(proc):
    try:
        # Leer de a un carácter para interactividad inmediata
        while proc.poll() is None:
            char = proc.stdout.read(1)
            if not char:
                break
            stdout_queue.put(char)
        # Limpiar resto
        while True:
            char = proc.stdout.read(1)
            if not char:
                break
            stdout_queue.put(char)
    except Exception:
        pass


PORT = 8000
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

class CompilerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_stdout(self):
        salida = ""
        while not stdout_queue.empty():
            salida += stdout_queue.get()

        estado = "idle"
        if current_process:
            estado = "finished" if current_process.poll() is not None else "running"

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"salida": salida, "estado": estado}).encode('utf-8'))

    def do_GET(self):
        if self.path == '/api/stdout':
            self._send_stdout()
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/compile':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                codigo = data.get('codigo', '')
                stdin_input = data.get('stdin', '')
                
                # Configuracion de salida
                filename = data.get('filename', '').strip()
                if not filename:
                    filename = "noname"
                    
                directory = data.get('directory', '').strip()
                if not directory:
                    directory = "."
                else:
                    # Evitar saltos de directorio inseguros de forma básica
                    directory = directory.replace("..", "")
                
                # Crear directorio si no existe
                out_dir = os.path.abspath(directory)
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                
                asm_path = os.path.join(out_dir, f"{filename}.asm")
                
                # Compilar a ASM usando nuestro main.py
                resultado = compilar_codigo(codigo, asm_path, filename)
                
                if resultado["ok"]:
                    # Generar el ejecutable NASM
                    exito_asm, log_asm = compilar_asm(asm_path)
                    resultado["log"] += f"\n\n{log_asm}"
                    
                    if exito_asm:
                        # Ejecutar el archivo compilado
                        try:
                            # Asegurar que se ejecuta el binario local
                            base_exec_path = asm_path.replace(".asm", "")
                            executable_path = f"{base_exec_path}.exe" if os.name == "nt" else f"./{base_exec_path}"
                            
                            resultado["ejecutable"] = executable_path
                            resultado["log"] += f"\n\n[EJECUTABLE GENERADO: {executable_path}]"
                            
                        except Exception as e:
                            resultado["log"] += f"\n\n[ERROR] {e}"
                    else:
                        resultado["ok"] = False
                        resultado.setdefault("errores", []).append("No se pudo generar el ejecutable con NASM/GCC. Revisa el log de compilacion.")
                        resultado.setdefault("diagnosticos", []).append({
                            "fase": "enlace",
                            "severidad": "error",
                            "linea": None,
                            "columna": None,
                            "mensaje": "No se pudo generar el ejecutable. Revisa la seccion tecnica NASM/GCC del log.",
                            "fuente": "",
                        })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resultado).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_res = {"ok": False, "log": f"Error del servidor: {str(e)}", "errores": [str(e)]}
                self.wfile.write(json.dumps(error_res).encode('utf-8'))
        elif self.path == '/api/run':
            global current_process
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                executable_path = data.get('ejecutable', '')
                
                # Matar proceso previo si hay uno
                if current_process and current_process.poll() is None:
                    current_process.kill()
                    
                # Limpiar cola
                while not stdout_queue.empty():
                    stdout_queue.get()
                
                # Iniciar nuevo proceso
                current_process = subprocess.Popen(
                    executable_path,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    shell=False
                )
                
                # Iniciar hilo lector
                threading.Thread(target=read_process_stdout, args=(current_process,), daemon=True).start()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode('utf-8'))
                
        elif self.path == '/api/stdin':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                texto = data.get('texto', '')
                if current_process and current_process.poll() is None:
                    current_process.stdin.write(texto + "\n")
                    current_process.stdin.flush()
                    # Eco en el stdout para que se vea lo que escribimos
                    for c in (texto + "\n"):
                        stdout_queue.put(c)
                self.send_response(200)
                self.end_headers()
            except Exception:
                self.send_response(500)
                self.end_headers()
                
        elif self.path == '/api/stdout':
            self._send_stdout()
            
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    # Asegurar que existe la carpeta public
    if not os.path.exists(PUBLIC_DIR):
        os.makedirs(PUBLIC_DIR)
        
    with socketserver.TCPServer(("", PORT), CompilerHandler) as httpd:
        print(f"Servidor del compilador corriendo en http://localhost:{PORT}")
        httpd.serve_forever()
