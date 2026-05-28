import customtkinter as ctk
from tkinter import messagebox, ttk # Importamos ttk SOLO para el Treeview
from typing import Tuple, List, Any
import sys

# --- Importar Tema y Módulo de Base de Datos ---
from theme import *
from theme import aplicar_estilo_treeview
import database # <-- AÑADIDO: Este módulo ahora maneja la conexión

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
# ...
# (BLOQUE ELIMINADO - Ahora en theme.py)
# ...
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# PARTE LÓGICA
# --- REFACTORIZADA ---
# -------------------------------------------------------------------
lista_maestra_proveedores: List[Tuple] = []

# --- FUNCIÓN ELIMINADA ---
# La función 'ejecutar_consulta' ahora está centralizada en 'database.py'

def obtener_proveedores() -> List[Tuple]:
    """
    Obtiene todos los proveedores de la base de datos.
    --- REFACTORIZADO para usar database.py ---
    """
    sql = "SELECT idProveedor, nombre, contacto, telefono, email FROM Proveedor ORDER BY nombre ASC"
    # database.obtener_todos se encarga del try/except, conexión y cierre
    return database.obtener_todos(sql)

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# (Esta sección no necesita cambios, excepto las llamadas a funciones de la BD)
# -------------------------------------------------------------------

class VentanaGestionProveedores(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)
        
        self.title("Módulo de Gestión de Proveedores")
        self.geometry("900x550")
        self.minsize(850, 500)

        # Configurar layout principal (2 columnas)
        self.grid_columnconfigure(0, weight=1, minsize=340) # Columna Formulario
        self.grid_columnconfigure(1, weight=2)           # Columna Tabla
        self.grid_rowconfigure(0, weight=1)

        # --- Variables de CTk ---
        self.entry_nombre_var = ctk.StringVar()
        self.entry_contacto_var = ctk.StringVar()
        self.entry_telefono_var = ctk.StringVar()
        self.entry_email_var = ctk.StringVar()
        self.entry_buscar_var = ctk.StringVar()

        # --- Estilo del Treeview ---
        # (Esto ya lo hicimos en el paso anterior)
        aplicar_estilo_treeview(self)

        # --- Crear Widgets ---
        self.crear_widgets_formulario()
        self.crear_widgets_tabla()

        # --- Carga Inicial ---
        self.refrescar_tabla_proveedores()
        self.limpiar_campos()

    # --- MÉTODO ELIMINADO ---
    # def crear_estilo_treeview(self):
    # ...

    def crear_widgets_formulario(self):
        """Crea el panel izquierdo (formulario)."""
        frame_formulario = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_formulario.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        frame_formulario.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_formulario, text="Datos del Proveedor", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        # Campos del formulario
        entry_style = {"height": 35, "font": ("Arial", 14), "border_color": COLOR_ACCENT_BUTTON}
        label_style = {"font": ("Arial", 14)}

        ctk.CTkLabel(frame_formulario, text="Nombre/Empresa:", **label_style).grid(row=1, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_nombre = ctk.CTkEntry(frame_formulario, textvariable=self.entry_nombre_var, **entry_style)
        self.entry_nombre.grid(row=1, column=1, pady=10, padx=(0, 20), sticky="ew")

        ctk.CTkLabel(frame_formulario, text="Nombre Contacto:", **label_style).grid(row=2, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_contacto = ctk.CTkEntry(frame_formulario, textvariable=self.entry_contacto_var, **entry_style)
        self.entry_contacto.grid(row=2, column=1, pady=10, padx=(0, 20), sticky="ew")

        ctk.CTkLabel(frame_formulario, text="Teléfono:", **label_style).grid(row=3, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_telefono = ctk.CTkEntry(frame_formulario, textvariable=self.entry_telefono_var, **entry_style)
        self.entry_telefono.grid(row=3, column=1, pady=10, padx=(0, 20), sticky="ew")

        ctk.CTkLabel(frame_formulario, text="Email:", **label_style).grid(row=4, column=0, pady=10, padx=(20, 10), sticky="w")
        self.entry_email = ctk.CTkEntry(frame_formulario, textvariable=self.entry_email_var, **entry_style)
        self.entry_email.grid(row=4, column=1, pady=10, padx=(0, 20), sticky="ew")

        # --- Botones CRUD ---
        frame_botones = ctk.CTkFrame(frame_formulario, fg_color="transparent")
        frame_botones.grid(row=5, column=0, columnspan=2, pady=(20, 10), sticky="ew")
        frame_botones.grid_columnconfigure((0, 1, 2), weight=1)

        btn_style_crud = {"font": ("Arial", 12, "bold"), "height": 35, "corner_radius": 10}
        
        self.boton_guardar = ctk.CTkButton(frame_botones, text="Guardar Nuevo", fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, command=self.on_guardar_click, **btn_style_crud)
        self.boton_guardar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.boton_actualizar = ctk.CTkButton(frame_botones, text="Actualizar", fg_color=COLOR_ACCENT_BUTTON, hover_color=COLOR_ACCENT_HOVER, command=self.on_actualizar_click, **btn_style_crud)
        self.boton_actualizar.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.boton_eliminar = ctk.CTkButton(frame_botones, text="Eliminar", fg_color=COLOR_DANGER, hover_color="#c0392b", command=self.on_eliminar_click, **btn_style_crud)
        self.boton_eliminar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        self.boton_limpiar = ctk.CTkButton(frame_botones, text="Limpiar Campos", fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, command=self.limpiar_campos, **btn_style_crud)
        self.boton_limpiar.grid(row=1, column=0, columnspan=3, pady=(5, 10), padx=5, sticky="ew")


    def crear_widgets_tabla(self):
        """Crea el panel derecho (tabla y búsqueda)."""
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        
        frame_tabla.grid_columnconfigure(0, weight=1)
        frame_tabla.grid_rowconfigure(2, weight=1) # Fila de la tabla

        ctk.CTkLabel(frame_tabla, text="Proveedores Registrados", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        frame_busqueda = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        frame_busqueda.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        frame_busqueda.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_busqueda, text="Buscar (Nombre o Contacto):", font=("Arial", 14)).pack(side="left", padx=(0, 10))
        self.entry_buscar = ctk.CTkEntry(frame_busqueda, textvariable=self.entry_buscar_var, height=30, font=("Arial", 12), border_color=COLOR_ACCENT_BUTTON)
        self.entry_buscar.pack(side="left", fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columnas = ("id", "nombre", "contacto", "telefono", "email")
        self.tabla_proveedores = ttk.Treeview(tree_frame, columns=columnas, show="headings", style="Custom.Treeview")
        
        self.tabla_proveedores.heading("id", text="ID")
        self.tabla_proveedores.heading("nombre", text="Nombre")
        self.tabla_proveedores.heading("contacto", text="Contacto")
        self.tabla_proveedores.heading("telefono", text="Teléfono")
        self.tabla_proveedores.heading("email", text="Email")
        
        self.tabla_proveedores.column("id", width=30, anchor="e")
        self.tabla_proveedores.column("nombre", width=150, anchor="w")
        self.tabla_proveedores.column("contacto", width=100, anchor="w")
        self.tabla_proveedores.column("telefono", width=80, anchor="w")
        self.tabla_proveedores.column("email", width=120, anchor="w")
        
        self.tabla_proveedores.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tabla_proveedores.yview)
        self.tabla_proveedores.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindings
        self.entry_buscar.bind("<KeyRelease>", self.on_buscar_proveedor)
        self.tabla_proveedores.bind("<<TreeviewSelect>>", self.on_proveedor_select)

    # -------------------------------------------------------------------
    # FUNCIONES DE LOS BOTONES
    # -------------------------------------------------------------------

    def poblar_tabla_proveedores(self, proveedores: List[Tuple]) -> None:
        """Limpia la tabla y la llena con la lista de proveedores dada."""
        for item in self.tabla_proveedores.get_children():
            self.tabla_proveedores.delete(item)
        for prov in proveedores:
            self.tabla_proveedores.insert("", "end", values=prov)

    def refrescar_tabla_proveedores(self) -> None:
        """Actualiza la lista maestra y repuebla la tabla."""
        global lista_maestra_proveedores
        lista_maestra_proveedores = obtener_proveedores() # <- Usa la función refactorizada
        self.entry_buscar_var.set("")
        self.poblar_tabla_proveedores(lista_maestra_proveedores)

    def on_guardar_click(self) -> None:
        """Callback para 'Guardar Nuevo'."""
        nombre = self.entry_nombre_var.get()
        contacto = self.entry_contacto_var.get()
        telefono = self.entry_telefono_var.get()
        email = self.entry_email_var.get()

        if not nombre:
            messagebox.showwarning("Campo requerido", "El campo 'Nombre' es obligatorio.")
            return

        sql = "INSERT INTO Proveedor (nombre, contacto, telefono, email) VALUES (?, ?, ?, ?)"
        
        # --- REFACTORIZADO ---
        if database.ejecutar_consulta(sql, (nombre, contacto, telefono, email)):
            messagebox.showinfo("Éxito", f"Proveedor '{nombre}' creado correctamente.")
            self.limpiar_campos()
            self.refrescar_tabla_proveedores()

    def on_actualizar_click(self) -> None:
        """Callback para 'Actualizar'."""
        try:
            seleccion = self.tabla_proveedores.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona un proveedor.")
                return
            id_proveedor = self.tabla_proveedores.item(seleccion)["values"][0]
        except IndexError:
             messagebox.showwarning("Sin selección", "Por favor, selecciona un proveedor válido.")
             return

        nombre = self.entry_nombre_var.get()
        contacto = self.entry_contacto_var.get()
        telefono = self.entry_telefono_var.get()
        email = self.entry_email_var.get()

        if not nombre:
            messagebox.showwarning("Campo requerido", "El campo 'Nombre' es obligatorio.")
            return

        sql = "UPDATE Proveedor SET nombre = ?, contacto = ?, telefono = ?, email = ? WHERE idProveedor = ?"
        
        # --- REFACTORIZADO ---
        if database.ejecutar_consulta(sql, (nombre, contacto, telefono, email, id_proveedor)):
            messagebox.showinfo("Éxito", f"Proveedor '{nombre}' actualizado correctamente.")
            self.limpiar_campos()
            self.refrescar_tabla_proveedores()

    def on_eliminar_click(self) -> None:
        """Callback para 'Eliminar'."""
        try:
            seleccion = self.tabla_proveedores.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona un proveedor.")
                return
            id_proveedor = self.tabla_proveedores.item(seleccion)["values"][0]
            nombre_proveedor = self.tabla_proveedores.item(seleccion)["values"][1]
        except IndexError:
             messagebox.showwarning("Sin selección", "Por favor, selecciona un proveedor válido.")
             return

        if messagebox.askyesno("Confirmar Eliminación",
                              f"¿Estás seguro de que deseas eliminar a '{nombre_proveedor}'?"):
            sql = "DELETE FROM Proveedor WHERE idProveedor = ?"
            
            # --- REFACTORIZADO ---
            if database.ejecutar_consulta(sql, (id_proveedor,)):
                messagebox.showinfo("Éxito", f"Proveedor '{nombre_proveedor}' eliminado.")
                self.limpiar_campos()
                self.refrescar_tabla_proveedores()
            else:
                # El error de 'llave foránea' (compras asociadas)
                # ya lo mostrará database.py, así que este 'else' se puede
                # simplificar o eliminar. Lo mantendré por si acaso.
                messagebox.showerror("Error", "No se pudo eliminar el proveedor. Es posible que tenga compras asociadas.")

    def limpiar_campos(self) -> None:
        """Limpia los campos del formulario."""
        self.entry_nombre_var.set("")
        self.entry_contacto_var.set("")
        self.entry_telefono_var.set("")
        self.entry_email_var.set("")
        
        if self.tabla_proveedores.focus():
            self.tabla_proveedores.selection_remove(self.tabla_proveedores.focus())

        if self.entry_buscar_var.get():
            self.entry_buscar_var.set("")
            self.poblar_tabla_proveedores(lista_maestra_proveedores)

        self.entry_nombre.focus()

    def on_proveedor_select(self, event: Any) -> None:
        """Callback para selección en la tabla. Rellena el formulario."""
        try:
            seleccion = self.tabla_proveedores.focus()
            if not seleccion:
                return
            datos = self.tabla_proveedores.item(seleccion)["values"]
        except IndexError:
            return

        self.entry_nombre_var.set(datos[1])
        self.entry_contacto_var.set(datos[2] if datos[2] else "")
        self.entry_telefono_var.set(datos[3] if datos[3] else "")
        self.entry_email_var.set(datos[4] if datos[4] else "")

    def on_buscar_proveedor(self, event: Any):
        """Filtra la tabla en tiempo real."""
        termino_busqueda = self.entry_buscar_var.get().lower()
        
        if not termino_busqueda:
            self.poblar_tabla_proveedores(lista_maestra_proveedores)
            return
        
        resultados_filtrados = []
        for prov_tuple in lista_maestra_proveedores:
            nombre = str(prov_tuple[1]).lower()
            contacto = str(prov_tuple[2]).lower()
            
            if termino_busqueda in nombre or termino_busqueda in contacto:
                resultados_filtrados.append(prov_tuple)
                
        self.poblar_tabla_proveedores(resultados_filtrados)

# -------------------------------------------------------------------
# INICIAR LA APLICACIÓN
# -------------------------------------------------------------------
if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
         messagebox.showerror(
            "Error de Dependencias",
            "Falta 'customtkinter'.\n\nPor favor, instala la librería ejecutando:\n\npython -m pip install customtkinter"
        )
         sys.exit(1)

    app = VentanaGestionProveedores()
    app.mainloop()