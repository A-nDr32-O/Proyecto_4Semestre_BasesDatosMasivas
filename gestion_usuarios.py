import customtkinter as ctk
from tkinter import messagebox, ttk # Importamos ttk SOLO para el Treeview
import hashlib
from typing import Tuple, List, Any, Optional
import sys # Para el fallback de ID_USUARIO

# --- Importar Tema y Módulo de Base de Datos ---
from theme import *
from theme import aplicar_estilo_treeview
import database # <-- AÑADIDO: Este módulo ahora maneja la conexión

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
# ...
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión y Seguridad)
# --- REFACTORIZADA ---
# -------------------------------------------------------------------

# Variable global para la lista de usuarios (para la búsqueda)
lista_maestra_usuarios: List[Tuple] = []

def hash_contrasena(contrasena: str) -> str:
    """
    Convierte una contraseña de texto plano a un hash SHA-256.
    (Esta función se mantiene, es lógica de negocio)
    """
    return hashlib.sha256(contrasena.encode('utf-8')).hexdigest()

# --- FUNCIÓN ELIMINADA ---
# La función 'ejecutar_consulta' ahora está centralizada en 'database.py'

def obtener_usuarios() -> List[Tuple]:
    """
    Obtiene todos los usuarios (sin contraseña) de la base de datos.
    --- REFACTORIZADO para usar database.py ---
    """
    sql = "SELECT idUsuario, nombre, rol, usuario FROM Usuario ORDER BY nombre ASC"
    # database.obtener_todos se encarga del try/except, conexión y cierre
    return database.obtener_todos(sql)

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# (Esta sección no necesita cambios, excepto las llamadas a funciones de la BD)
# -------------------------------------------------------------------

class VentanaGestionUsuarios(ctk.CTk):
    
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)
        
        self.title("Módulo de Gestión de Usuarios")
        self.geometry("900x550")
        self.minsize(850, 500)

        # Configurar layout principal (2 columnas)
        self.grid_columnconfigure(0, weight=1, minsize=320) # Columna Formulario
        self.grid_columnconfigure(1, weight=2)           # Columna Tabla
        self.grid_rowconfigure(0, weight=1)

        # --- Variables de CTk ---
        self.entry_nombre_var = ctk.StringVar()
        self.entry_usuario_var = ctk.StringVar()
        self.entry_contrasena_var = ctk.StringVar()
        self.combo_rol_var = ctk.StringVar()
        self.entry_buscar_var = ctk.StringVar()
        
        # --- Estilo del Treeview ---
        # (Esto ya lo hicimos en el paso anterior)
        aplicar_estilo_treeview(self)

        # --- Crear Widgets ---
        self.crear_widgets_formulario()
        self.crear_widgets_tabla()

        # --- Carga Inicial ---
        self.refrescar_tabla_usuarios()
        self.modo_edicion = False  # True si se está editando un usuario existente
        self.limpiar_campos_contrasena()

    # --- MÉTODO ELIMINADO ---
    # def crear_estilo_treeview(self):
    # ...

    def crear_widgets_formulario(self):
        """Crea el panel izquierdo (formulario)."""
        frame_formulario = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_formulario.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        
        frame_formulario.grid_columnconfigure(1, weight=1)

        # Título del Frame
        ctk.CTkLabel(frame_formulario, text="Datos del Usuario", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        # Nombre Completo
        ctk.CTkLabel(frame_formulario, text="Nombre Completo:", font=("Arial", 14)).grid(row=1, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_nombre = ctk.CTkEntry(frame_formulario, textvariable=self.entry_nombre_var, width=200, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON)
        self.entry_nombre.grid(row=1, column=1, pady=10, padx=(0, 20), sticky="ew")

        # Usuario (login)
        ctk.CTkLabel(frame_formulario, text="Usuario (login):", font=("Arial", 14)).grid(row=2, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_usuario = ctk.CTkEntry(frame_formulario, textvariable=self.entry_usuario_var, width=200, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON)
        self.entry_usuario.grid(row=2, column=1, pady=10, padx=(0, 20), sticky="ew")

        # Contraseña
        ctk.CTkLabel(frame_formulario, text="Contraseña:", font=("Arial", 14)).grid(row=3, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_contrasena = ctk.CTkEntry(frame_formulario, textvariable=self.entry_contrasena_var, width=200, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON)
        self.entry_contrasena.grid(row=3, column=1, pady=10, padx=(0, 20), sticky="ew")

        # Rol
        ctk.CTkLabel(frame_formulario, text="Rol:", font=("Arial", 14)).grid(row=4, column=0, pady=10, padx=(20, 10), sticky="w")
        self.combo_rol = ctk.CTkComboBox(frame_formulario, values=["Administrador", "Vendedor"], state="readonly", width=200, height=35, font=("Arial", 14), variable=self.combo_rol_var, border_color=COLOR_ACCENT_BUTTON, button_color=COLOR_ACCENT_BUTTON, button_hover_color=COLOR_ACCENT_HOVER)
        self.combo_rol.grid(row=4, column=1, pady=10, padx=(0, 20), sticky="ew")

        # --- Frame de Botones ---
        frame_botones = ctk.CTkFrame(frame_formulario, fg_color="transparent")
        frame_botones.grid(row=5, column=0, columnspan=2, pady=20, sticky="ew")
        frame_botones.grid_columnconfigure((0, 1, 2), weight=1) # Tres botones por fila

        btn_style = {
            "font": ("Arial", 12, "bold"),
            "height": 35,
            "corner_radius": 10
        }

        self.boton_guardar = ctk.CTkButton(frame_botones, text="Guardar Nuevo", fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, command=self.on_guardar_click, **btn_style)
        self.boton_guardar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.boton_actualizar = ctk.CTkButton(frame_botones, text="Actualizar", fg_color=COLOR_ACCENT_BUTTON, hover_color=COLOR_ACCENT_HOVER, command=self.on_actualizar_click, **btn_style)
        self.boton_actualizar.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.boton_eliminar = ctk.CTkButton(frame_botones, text="Eliminar", fg_color=COLOR_DANGER, hover_color="#c0392b", command=self.on_eliminar_click, **btn_style)
        self.boton_eliminar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        self.boton_limpiar = ctk.CTkButton(frame_botones, text="Limpiar Campos", fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, command=self.limpiar_campos, **btn_style)
        self.boton_limpiar.grid(row=1, column=0, columnspan=3, pady=(5, 10), padx=5, sticky="ew")
        
        # Bindings para el placeholder de contraseña
        self.entry_contrasena.bind("<FocusIn>", self.on_pass_focus_in)
        self.entry_contrasena.bind("<FocusOut>", self.on_pass_focus_out)

    def crear_widgets_tabla(self):
        """Crea el panel derecho (tabla y búsqueda)."""
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        
        frame_tabla.grid_columnconfigure(0, weight=1)
        frame_tabla.grid_rowconfigure(2, weight=1) # Fila de la tabla

        # Título
        ctk.CTkLabel(frame_tabla, text="Usuarios Registrados", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # Frame de Búsqueda
        frame_busqueda = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        frame_busqueda.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        frame_busqueda.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_busqueda, text="Buscar:", font=("Arial", 14)).pack(side="left", padx=(0, 10))
        self.entry_buscar = ctk.CTkEntry(frame_busqueda, textvariable=self.entry_buscar_var, height=30, font=("Arial", 12), border_color=COLOR_ACCENT_BUTTON)
        self.entry_buscar.pack(side="left", fill="x", expand=True)
        
        # Frame para Treeview y Scrollbar
        tree_frame = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columnas = ("id", "nombre", "rol", "usuario")
        self.tabla_usuarios = ttk.Treeview(tree_frame, columns=columnas, show="headings", style="Custom.Treeview")
        self.tabla_usuarios.heading("id", text="ID")
        self.tabla_usuarios.heading("nombre", text="Nombre")
        self.tabla_usuarios.heading("rol", text="Rol")
        self.tabla_usuarios.heading("usuario", text="Usuario (login)")
        
        self.tabla_usuarios.column("id", width=30, anchor="center")
        self.tabla_usuarios.column("nombre", width=150)
        self.tabla_usuarios.column("rol", width=80)
        self.tabla_usuarios.column("usuario", width=100)
        
        self.tabla_usuarios.grid(row=0, column=0, sticky="nsew")

        # Scrollbar (usamos ttk para compatibilidad con Treeview)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tabla_usuarios.yview)
        self.tabla_usuarios.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindings de eventos
        self.entry_buscar.bind("<KeyRelease>", self.on_buscar_usuario)
        self.tabla_usuarios.bind("<<TreeviewSelect>>", self.on_usuario_select)


    # -------------------------------------------------------------------
    # FUNCIONES DE LA INTERFAZ
    # -------------------------------------------------------------------

    def poblar_tabla_usuarios(self, usuarios: List[Tuple]) -> None:
        """Limpia la tabla y la llena con la lista de usuarios dada."""
        for item in self.tabla_usuarios.get_children():
            self.tabla_usuarios.delete(item)
        for user in usuarios:
            self.tabla_usuarios.insert("", "end", values=user)

    def refrescar_tabla_usuarios(self) -> None:
        """
        Obtiene los usuarios frescos de la BD, actualiza la lista maestra
        y repuebla la tabla.
        """
        global lista_maestra_usuarios
        lista_maestra_usuarios = obtener_usuarios() # <- Usa la función refactorizada
        self.entry_buscar_var.set("")
        self.poblar_tabla_usuarios(lista_maestra_usuarios)

    def on_guardar_click(self) -> None:
        """Callback para 'Guardar Nuevo'."""
        nombre = self.entry_nombre_var.get().strip()
        usuario_login = self.entry_usuario_var.get().strip()
        contrasena = self.entry_contrasena_var.get()
        rol = self.combo_rol_var.get()

        if not nombre or not usuario_login or not rol:
            messagebox.showwarning("Campos incompletos", "Los campos Nombre, Usuario, Contraseña y Rol son requeridos.")
            return
        if not contrasena or contrasena == "(Obligatorio asignar contraseña)":
            messagebox.showwarning("Contraseña obligatoria", "Debe ingresar una contraseña para el nuevo usuario.")
            return

        contrasena_hasheada = hash_contrasena(contrasena)

        sql = "INSERT INTO Usuario (nombre, rol, usuario, contrasena) VALUES (?, ?, ?, ?)"
        if database.ejecutar_consulta(sql, (nombre, rol, usuario_login, contrasena_hasheada)):
            messagebox.showinfo("Éxito", f"Usuario '{nombre}' creado correctamente.")
            self.limpiar_campos()
            self.refrescar_tabla_usuarios()
        # else:
        #   database.py ya habrá mostrado el error de 'UNIQUE constraint'

    def on_actualizar_click(self) -> None:
        """Callback para 'Actualizar'."""
        try:
            seleccion = self.tabla_usuarios.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona un usuario.")
                return
            id_usuario = self.tabla_usuarios.item(seleccion)["values"][0]
        except IndexError:
            messagebox.showwarning("Sin selección", "Por favor, selecciona un usuario válido.")
            return

        # --- APLICAR .strip() para validación de presencia de datos ---
        nombre = self.entry_nombre_var.get().strip()
        usuario_login = self.entry_usuario_var.get().strip()
        contrasena = self.entry_contrasena_var.get()
        rol = self.combo_rol_var.get()

        if not nombre or not usuario_login or not rol:
            messagebox.showwarning("Campos incompletos", "Los campos 'Nombre', 'Usuario' y 'Rol' no pueden estar vacíos.")
            return

        if contrasena and contrasena != "(Dejar vacío para no cambiar)":
            contrasena_hasheada = hash_contrasena(contrasena)
            sql = "UPDATE Usuario SET nombre = ?, rol = ?, usuario = ?, contrasena = ? WHERE idUsuario = ?"
            params = (nombre, rol, usuario_login, contrasena_hasheada, id_usuario)
        else:
            sql = "UPDATE Usuario SET nombre = ?, rol = ?, usuario = ? WHERE idUsuario = ?"
            params = (nombre, rol, usuario_login, id_usuario)

        # --- REFACTORIZADO ---
        if database.ejecutar_consulta(sql, params):
            messagebox.showinfo("Éxito", f"Usuario '{nombre}' actualizado correctamente.")
            self.limpiar_campos()
            self.refrescar_tabla_usuarios()

    def on_eliminar_click(self) -> None:
        """Callback para 'Eliminar'."""
        try:
            seleccion = self.tabla_usuarios.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona un usuario.")
                return
            
            id_usuario = self.tabla_usuarios.item(seleccion)["values"][0]
            nombre_usuario = self.tabla_usuarios.item(seleccion)["values"][1]
        except IndexError:
            messagebox.showwarning("Sin selección", "Por favor, selecciona un usuario válido.")
            return

        if id_usuario == 1:
            messagebox.showerror("Acción Denegada", "No se puede eliminar al Administrador principal (ID 1).")
            return

        if messagebox.askyesno("Confirmar Eliminación",
                                f"¿Estás seguro de que deseas eliminar al usuario '{nombre_usuario}'?"):
            sql = "DELETE FROM Usuario WHERE idUsuario = ?"
            
            # --- REFACTORIZADO ---
            if database.ejecutar_consulta(sql, (id_usuario,)):
                messagebox.showinfo("Éxito", f"Usuario '{nombre_usuario}' eliminado.")
                self.limpiar_campos()
                self.refrescar_tabla_usuarios()

    def limpiar_campos(self) -> None:
        """Limpia los campos del formulario y pone el placeholder de contraseña para NUEVO usuario."""
        self.entry_nombre_var.set("")
        self.entry_usuario_var.set("")
        self.combo_rol_var.set("")
        self.modo_edicion = False
        if self.tabla_usuarios.focus():
            self.tabla_usuarios.selection_remove(self.tabla_usuarios.focus())
        if self.entry_buscar_var.get():
            self.entry_buscar_var.set("")
            self.poblar_tabla_usuarios(lista_maestra_usuarios)
        self.limpiar_campos_contrasena()
        self.entry_nombre.focus()
        
    def on_usuario_select(self, event: Any) -> None:
        """Callback para selección en la tabla. Rellena el formulario para EDICIÓN."""
        try:
            seleccion = self.tabla_usuarios.focus()
            if not seleccion:
                return
            datos = self.tabla_usuarios.item(seleccion)["values"]
        except IndexError:
            return # Ocurre si la tabla se refresca mientras se selecciona

        self.entry_nombre_var.set(datos[1])
        self.combo_rol_var.set(datos[2])
        self.entry_usuario_var.set(datos[3])
        self.modo_edicion = True
        self.limpiar_campos_contrasena()

    def on_pass_focus_in(self, event: Any) -> None:
        """Callback para cuando el entry de contraseña recibe foco."""
        if self.entry_contrasena_var.get() in ("(Dejar vacío para no cambiar)", "(Obligatorio asignar contraseña)"):
            self.entry_contrasena_var.set("")
            self.entry_contrasena.configure(fg_color=COLOR_ENTRY_BG, text_color=COLOR_TEXT_PRIMARY, show="*")

    def on_pass_focus_out(self, event: Any) -> None:
        """Callback para cuando el entry de contraseña pierde foco."""
        if not self.entry_contrasena_var.get():
            self.limpiar_campos_contrasena()

    def limpiar_campos_contrasena(self) -> None:
        """Función helper para resetear el campo contraseña a su estado placeholder según modo."""
        if self.modo_edicion:
            self.entry_contrasena_var.set("(Dejar vacío para no cambiar)")
        else:
            self.entry_contrasena_var.set("(Obligatorio asignar contraseña)")
        self.entry_contrasena.configure(fg_color=COLOR_ENTRY_BG, text_color="grey", show="")

    def on_buscar_usuario(self, event: Any):
        """Filtra la tabla en tiempo real basado en el texto de búsqueda."""
        global lista_maestra_usuarios
        termino_busqueda = self.entry_buscar_var.get().lower()
        
        if not termino_busqueda:
            self.poblar_tabla_usuarios(lista_maestra_usuarios)
            return
        
        resultados_filtrados = []
        for usuario_tuple in lista_maestra_usuarios:
            nombre = str(usuario_tuple[1]).lower()
            login = str(usuario_tuple[3]).lower()
            
            if termino_busqueda in nombre or termino_busqueda in login:
                resultados_filtrados.append(usuario_tuple)
                
        self.poblar_tabla_usuarios(resultados_filtrados)

# -------------------------------------------------------------------
# BINDINGS y Carga Inicial
# -------------------------------------------------------------------

if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
         messagebox.showerror(
            "Error de Dependencias",
            "Falta 'customtkinter'.\n\Por favor, instala la librería ejecutando:\n\npython -m pip install customtkinter"
        )
         sys.exit(1)
         
    app = VentanaGestionUsuarios()
    app.mainloop()