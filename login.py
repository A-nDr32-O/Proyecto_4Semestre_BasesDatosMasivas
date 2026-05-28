import customtkinter as ctk
from tkinter import messagebox
import hashlib
import subprocess
import sys
from typing import Tuple, Optional
import os
from PIL import Image, ImageTk

# --- Importar Tema ---
from theme import *

# --- Importar Módulo de Base de Datos ---
import database # <-- Este módulo ahora maneja la conexión

# --- Lógica de Ruta Base (para assets como el logo del avatar)
# -------------------------------------------------------------------
# NOTA: Definición de BASE_DIR para encontrar recursos en modo script o ejecutable
if getattr(sys, 'frozen', False):
    # Estamos en un ejecutable (PyInstaller)
    # En modo ejecutable, la ruta temporal de los assets es la raíz del ejecutable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Estamos en un script .py normal
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_PATH = os.path.join(BASE_DIR, "assets", "icons")

# -------------------------------------------------------------------

def hash_contrasena(contrasena: str) -> str:
    """
    Convierte una contraseña de texto plano a un hash SHA-256.
    """
    return hashlib.sha256(contrasena.encode('utf-8')).hexdigest()


def verificar_credenciales(usuario: str, contrasena: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Verifica si un usuario y contraseña coinciden en la base de datos.
    Devuelve: (autenticado, id_usuario, rol, nombre_completo)
    """
    contrasena_hasheada = hash_contrasena(contrasena)

    sql = "SELECT idUsuario, rol, nombre FROM Usuario WHERE usuario = ? AND contrasena = ?"
    
    resultado = database.obtener_uno(sql, (usuario, contrasena_hasheada))

    if resultado:
        id_usuario = resultado[0]
        rol = resultado[1]
        nombre = resultado[2] 
        return (True, id_usuario, rol, nombre) 
    else:
        return (False, None, None, None) 

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de Tkinter)
# -------------------------------------------------------------------

class VentanaLogin(ctk.CTk):
    
    def __init__(self):
        super().__init__()
        
        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND) 

        self.title("Iniciar Sesión - Frutos Secos La Sabana")
        self.geometry("400x500")
        self.resizable(False, False)
        
        # --- Variables de CTk ---
        self.label_mensaje_var = ctk.StringVar(value="")

        self.crear_widgets()
        
        # Centrar la ventana
        self.after(100, self.center_window)

    def center_window(self):
        """Centra la ventana en la pantalla."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def load_avatar_icon(self):
        """Carga el icono del avatar desde la carpeta de assets."""
        path = os.path.join(ASSETS_PATH, "user.png") 
        try:
            if not os.path.exists(path):
                # Si falla en el modo script, intentamos la ruta relativa de PyInstaller
                # En modo ejecutable, PyInstaller a veces usa esta ruta temporal
                path = os.path.join(os.path.dirname(sys.executable), "assets", "icons", "user.png")
            
            if not os.path.exists(path):
                 print(f"Advertencia: No se encontró el icono: user.png en la ruta final.")
                 return None
            
            image = Image.open(path).resize((60, 60))
            return ctk.CTkImage(light_image=image, dark_image=image, size=(60, 60))
        except Exception as e:
            print(f"Error al cargar el icono user.png: {e}")
            return None

    def crear_widgets(self):
        """Crea y posiciona todos los widgets en la ventana."""
        
        # --- Frame Principal (el panel blanco) ---
        login_frame = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        login_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.8)

        login_frame.grid_columnconfigure(0, weight=1)
        login_frame.grid_rowconfigure(6, weight=1) 

        # --- Icono de Avatar ---
        self.avatar_icon = self.load_avatar_icon()
        avatar_bg = ctk.CTkFrame(
            login_frame, 
            fg_color=COLOR_ACCENT_BUTTON, 
            width=80, 
            height=80, 
            corner_radius=40
        )
        avatar_bg.grid(row=0, column=0, pady=(30, 15))
        
        avatar_label = ctk.CTkLabel(avatar_bg, image=self.avatar_icon, text="")
        if self.avatar_icon:
            avatar_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Título ---
        titulo = ctk.CTkLabel(
            login_frame,
            text="INICIAR SESIÓN",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY 
        )
        titulo.grid(row=1, column=0, pady=(0, 20), sticky="n")

        # --- Campo de Usuario ---
        label_usuario = ctk.CTkLabel(
            login_frame,
            text="Usuario",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_PRIMARY 
        )
        label_usuario.grid(row=2, column=0, padx=30, sticky="w")

        self.entry_usuario = ctk.CTkEntry(
            login_frame,
            placeholder_text="Nombre de usuario",
            font=ctk.CTkFont(size=14),
            border_color=COLOR_ACCENT_BUTTON, 
            height=40,
            corner_radius=10
        )
        self.entry_usuario.grid(row=3, column=0, padx=30, sticky="ew")

        # --- Campo de Contraseña ---
        label_pass = ctk.CTkLabel(
            login_frame,
            text="Contraseña",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_PRIMARY 
        )
        label_pass.grid(row=4, column=0, padx=30, pady=(15, 0), sticky="w")

        self.entry_contrasena = ctk.CTkEntry(
            login_frame,
            placeholder_text="Contraseña secreta",
            font=ctk.CTkFont(size=14),
            show="*",
            border_color=COLOR_ACCENT_BUTTON, 
            height=40,
            corner_radius=10
        )
        self.entry_contrasena.grid(row=5, column=0, padx=30, sticky="ew")

        # --- Botón de Ingresar ---
        self.boton_ingresar = ctk.CTkButton(
            login_frame,
            text="INGRESAR",
            command=self.on_ingresar_click,
            fg_color=COLOR_ACCENT_BUTTON, 
            hover_color=COLOR_ACCENT_HOVER, 
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            corner_radius=10
        )
        self.boton_ingresar.grid(row=6, column=0, padx=30, pady=(30, 10), sticky="s")

        # --- Mensaje de Error ---
        self.label_mensaje = ctk.CTkLabel(
            login_frame,
            textvariable=self.label_mensaje_var,
            text_color=COLOR_DANGER, 
            font=ctk.CTkFont(size=12)
        )
        self.label_mensaje.grid(row=7, column=0, padx=30, pady=(0, 20), sticky="s")

        # Binds para la tecla Enter
        self.entry_usuario.bind("<Return>", self.on_ingresar_click)
        self.entry_contrasena.bind("<Return>", self.on_ingresar_click)

    def on_ingresar_click(self, event=None):
        """Callback que se ejecuta al presionar 'Ingresar'."""
        usuario = self.entry_usuario.get()
        contrasena = self.entry_contrasena.get()

        if not usuario or not contrasena:
            self.label_mensaje_var.set("Ambos campos son requeridos.")
            return

        autenticado, id_usuario, rol, nombre = verificar_credenciales(usuario, contrasena)

        if autenticado:
            self.label_mensaje_var.set("")
            self.withdraw() 
            
            try:
                interprete = sys.executable
                
                # --- LÓGICA CORREGIDA PARA PYINSTALLER ---
                if getattr(sys, 'frozen', False):
                    # En modo ejecutable, la ruta_base_app es la raíz del paquete
                    ruta_base_app = os.path.dirname(sys.executable)
                else:
                    # Modo script
                    ruta_base_app = BASE_DIR
                # ----------------------------------------
                    
                ruta_main = os.path.join(ruta_base_app, "main.py")
                
                if not os.path.exists(ruta_main):
                    # Aquí es donde fallaba. La corrección en el comando PyInstaller (add-data) 
                    # y la ruta base correcta deberían solucionar este error crítico.
                    messagebox.showerror("Error Crítico", f"No se encontró 'main.py' en\n{ruta_base_app}")
                    self.destroy() 
                    return
                
                # Pasamos id, rol y nombre a main.py
                cmd = [interprete, ruta_main, str(id_usuario), rol, nombre]
                
                subprocess.Popen(cmd)
                
                self.destroy() 
                
            except Exception as e:
                messagebox.showerror("Error al Iniciar", f"No se pudo lanzar 'main.py'.\nError: {e}")
                self.destroy() 

        else:
            self.label_mensaje_var.set("Usuario o contraseña incorrectos.")
            self.entry_contrasena.delete(0, "end")


# --- Iniciar la aplicación ---
if __name__ == "__main__":
    try:
        import customtkinter
        from PIL import Image, ImageTk
    except ImportError:
         messagebox.showerror(
            "Error de Dependencias",
            "Faltan 'customtkinter' y/o 'Pillow'.\n\nPor favor, instala las librerías ejecutando:\n\n"
            "python -m pip install customtkinter\n"
            "python -m pip install pillow"
        )
         sys.exit(1)
         
    app = VentanaLogin()
    app.mainloop()