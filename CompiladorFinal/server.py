import http.server
import socketserver
import json
import urllib.parse
import os
import subprocess
from main import compilar_codigo, compilar_asm

PORT = 8000
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

class CompilerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_POST(self):
        if self.path == '/api/compile':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                codigo = data.get('codigo', '')
                
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
                resultado = compilar_codigo(codigo, asm_path)
                
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
                            res_exec = subprocess.run(executable_path, capture_output=True, text=True, timeout=5, shell=True)
                            resultado["log"] += f"\n\n[EJECUCIÓN]\n{res_exec.stdout}"
                            if res_exec.stderr:
                                resultado["log"] += f"\n[ERRORES EJECUCIÓN]\n{res_exec.stderr}"
                        except Exception as e:
                            resultado["log"] += f"\n\n[ERROR AL EJECUTAR] {e}"
                
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
