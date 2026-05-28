import customtkinter as ctk
from tkinter import messagebox, ttk # Importamos ttk SOLO para el Treeview
from tkinter import Toplevel
from typing import Tuple, List, Any, Optional
import sys # Para el fallback de ID_USUARIO
from tkinter import TclError # Importar TclError

# --- Importar Tema y Módulo de Base de Datos ---
from theme import *
from theme import aplicar_estilo_treeview
import database # <-- AÑADIDO: Este módulo ahora maneja la conexión

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
# ... (se mantiene)
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión con la Base de Datos)
# --- REFACTORIZADA ---
# -------------------------------------------------------------------
lista_maestra_productos: List[Tuple] = []

def obtener_productos() -> List[Tuple]:
    """
    Obtiene todos los productos (incluyendo costo).
    """
    sql = """
        SELECT idProducto, nombre, precioPorGramo, costoPorGramo, stockEnGramos, umbralMinimoGramos
        FROM Producto
        ORDER BY nombre ASC
        """
    return database.obtener_todos(sql)

def get_producto_stock(id_producto: int) -> Optional[float]:
    """
    Obtiene el stock actual de un producto específico.
    """
    sql = "SELECT stockEnGramos FROM Producto WHERE idProducto = %s"
    
    resultado = database.obtener_uno(sql, (id_producto,))
    
    return resultado[0] if resultado else None

def actualizar_stock_producto(id_producto: int, cantidad_a_sumar_gramos: float) -> bool:
    """
    Ajusta el stock de un producto.
    """
    sql = "UPDATE Producto SET stockEnGramos = stockEnGramos + %s WHERE idProducto = %s"
    
    return database.ejecutar_consulta(sql, (cantidad_a_sumar_gramos, id_producto))

# -------------------------------------------------------------------
# FUNCIÓN DE VALIDACIÓN DE ENTRADA (NÚMEROS Y DECIMALES)
# -------------------------------------------------------------------

def es_numero_o_decimal(text: str, current_value: str) -> bool:
    """
    Valida si la entrada es un número, un decimal (punto o coma), o si está vacía.
    """
    if text == "" or text == "-1": 
        return True
    
    new_value = current_value + text
    new_value = new_value.replace(',', '.')

    try:
        float(new_value)
        return True
    except ValueError:
        return False

# -------------------------------------------------------------------
# FUNCIÓN AUXILIAR PARA CONVERSIÓN DE STOCK
# -------------------------------------------------------------------

# Utilizamos los factores de conversión globales
FACTORES_PESO = {
    "Gramos": 1.0, 
    "Libras": 453.592, 
    "Kilos": 1000.0,
    "Toneladas": 1000000.0
}

def convertir_a_mejor_unidad(peso_en_gramos: float) -> Tuple[float, str]:
    """
    Convierte peso en gramos a la unidad más legible (T, Kg, Lb, g).
    """
    
    mejor_unidad = "Gramos"
    mejor_cantidad = peso_en_gramos
    
    if peso_en_gramos >= FACTORES_PESO["Toneladas"]:
        mejor_unidad = "Kilos" # Usaremos Kilos como el display más grande en la UI, o Toneladas.
        mejor_cantidad = peso_en_gramos / FACTORES_PESO["Toneladas"]
        mejor_unidad = "Toneladas"
    elif peso_en_gramos >= FACTORES_PESO["Kilos"]:
        mejor_unidad = "Kilos"
        mejor_cantidad = peso_en_gramos / FACTORES_PESO["Kilos"]
    elif peso_en_gramos >= FACTORES_PESO["Libras"]:
        mejor_unidad = "Libras"
        mejor_cantidad = peso_en_gramos / FACTORES_PESO["Libras"]
    
    if mejor_unidad == "Gramos":
        mejor_cantidad = round(mejor_cantidad, 2)
    else:
        mejor_cantidad = round(mejor_cantidad, 2)

    # Mapeo de la clave corta a la clave larga del ComboBox (si es necesario)
    if mejor_unidad == "Kilos": return (mejor_cantidad, "Kilos (kg)")
    if mejor_unidad == "Libras": return (mejor_cantidad, "Libras (lb)")
    if mejor_unidad == "Toneladas": return (mejor_cantidad, "Toneladas (t)")
    
    return (mejor_cantidad, "Gramos (g)")

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# -------------------------------------------------------------------

class VentanaGestionProductos(ctk.CTk):
    
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)
        
        self.title("Módulo de Productos - Frutos Secos La Sabana")
        self.geometry("950x650")
        self.minsize(900, 600)

        self.factores_conversion = {
            "Gramos (g)": 1.0, "Kilos (kg)": 1000.0,
            "Libras (lb)": 453.592, "Toneladas (t)": 1000000.0
        }

        # Configurar layout principal (2 columnas)
        self.grid_columnconfigure(0, weight=1, minsize=340) # Columna Formulario
        self.grid_columnconfigure(1, weight=2)           # Columna Tabla
        self.grid_rowconfigure(0, weight=1)

        # --- Variables de CTk ---
        self.entry_nombre_var = ctk.StringVar()
        self.entry_precio_var = ctk.StringVar()
        self.entry_costo_var = ctk.StringVar()
        
        self.entry_stock_var = ctk.StringVar()
        self.stock_unidad_var = ctk.StringVar(value="Kilos (kg)") 
        
        self.entry_umbral_var = ctk.StringVar()
        self.entry_buscar_var = ctk.StringVar()
        
        # --- Configuración de validación ---
        self.vcmd = (self.register(self.validate_numeric_input), '%S', '%P')

        # --- Estilo del Treeview ---
        aplicar_estilo_treeview(self)

        # --- Crear Widgets ---
        self.crear_widgets_formulario()
        self.crear_widgets_tabla()
        
        # --- Configurar Tag de Alerta de Stock ---
        self.tabla_productos.tag_configure("stock_bajo", background=COLOR_WARNING, foreground=COLOR_TEXT_PRIMARY)
        self.tabla_productos.tag_configure("stock_cero", background=COLOR_DANGER, foreground=COLOR_TEXT_NAV) 

        # --- Carga Inicial ---
        self.refrescar_tabla_productos()
        self.limpiar_campos()

    def validate_numeric_input(self, S, P):
        """Wrapper para llamar a la función de validación estricta."""
        return es_numero_o_decimal(S, P)

    def crear_widgets_formulario(self):
        """Crea el panel izquierdo (formulario)."""
        frame_formulario_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        frame_formulario_scroll.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=0)
        frame_formulario_scroll.grid_columnconfigure(0, weight=1)

        # --- Frame 1: Datos del Producto ---
        frame_datos = ctk.CTkFrame(frame_formulario_scroll, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_datos.grid(row=0, column=0, sticky="ew", pady=(20, 10))
        frame_datos.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_datos, text="Datos del Producto", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        # Campos del formulario
        entry_style = {"height": 35, "font": ("Arial", 14), "border_color": COLOR_ACCENT_BUTTON, "validate": "key", "validatecommand": self.vcmd}
        label_style = {"font": ("Arial", 14)}
        
        ctk.CTkLabel(frame_datos, text="Nombre:", **label_style).grid(row=1, column=0, pady=8, padx=(20, 10), sticky="w")
        self.entry_nombre = ctk.CTkEntry(frame_datos, textvariable=self.entry_nombre_var, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON) # Sin validación
        self.entry_nombre.grid(row=1, column=1, pady=8, padx=(0, 20), sticky="ew")

        ctk.CTkLabel(frame_datos, text="Precio/g ($):", **label_style).grid(row=2, column=0, pady=8, padx=(20, 10), sticky="w")
        self.entry_precio = ctk.CTkEntry(frame_datos, textvariable=self.entry_precio_var, **entry_style)
        self.entry_precio.grid(row=2, column=1, pady=8, padx=(0, 20), sticky="ew")

        ctk.CTkLabel(frame_datos, text="Costo/g ($):", **label_style).grid(row=3, column=0, pady=8, padx=(20, 10), sticky="w")
        self.entry_costo = ctk.CTkEntry(frame_datos, textvariable=self.entry_costo_var, **entry_style)
        self.entry_costo.grid(row=3, column=1, pady=8, padx=(0, 20), sticky="ew")

        # Stock Inicial ahora tiene entrada de cantidad y selector de unidad
        ctk.CTkLabel(frame_datos, text="Stock Inicial:", **label_style).grid(row=4, column=0, pady=8, padx=(20, 10), sticky="w")
        
        frame_stock_input = ctk.CTkFrame(frame_datos, fg_color="transparent")
        frame_stock_input.grid(row=4, column=1, pady=8, padx=(0, 20), sticky="ew")
        
        frame_stock_input.grid_columnconfigure(0, weight=3)
        frame_stock_input.grid_columnconfigure(1, weight=1)

        self.entry_stock = ctk.CTkEntry(frame_stock_input, textvariable=self.entry_stock_var, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON, justify="right", validate="key", validatecommand=self.vcmd)
        self.entry_stock.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Selector de Unidad para el Stock Inicial
        unidades_keys = list(self.factores_conversion.keys())
        self.combo_stock_unidad = ctk.CTkComboBox(frame_stock_input, 
                                                 values=unidades_keys, 
                                                 state="readonly", 
                                                 width=120, 
                                                 height=35, 
                                                 font=("Arial", 14), 
                                                 variable=self.stock_unidad_var)
        self.combo_stock_unidad.grid(row=0, column=1, sticky="e")
        
        # Umbral Mínimo (se mantiene)
        ctk.CTkLabel(frame_datos, text="Umbral Mínimo (g):", **label_style).grid(row=5, column=0, pady=8, padx=(20, 10), sticky="w")
        self.entry_umbral = ctk.CTkEntry(frame_datos, textvariable=self.entry_umbral_var, **entry_style)
        self.entry_umbral.grid(row=5, column=1, pady=8, padx=(0, 20), sticky="ew")

        # --- Botones CRUD ---
        frame_botones_crud = ctk.CTkFrame(frame_datos, fg_color="transparent")
        frame_botones_crud.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")
        frame_botones_crud.grid_columnconfigure((0, 1, 2), weight=1)

        btn_style_crud = {"font": ("Arial", 12, "bold"), "height": 35, "corner_radius": 10}
        
        self.boton_guardar = ctk.CTkButton(frame_botones_crud, text="Guardar Nuevo", fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, command=self.on_guardar_click, **btn_style_crud)
        self.boton_guardar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.boton_actualizar = ctk.CTkButton(frame_botones_crud, text="Actualizar", fg_color=COLOR_ACCENT_BUTTON, hover_color=COLOR_ACCENT_HOVER, command=self.on_actualizar_click, **btn_style_crud)
        self.boton_actualizar.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.boton_eliminar = ctk.CTkButton(frame_botones_crud, text="Eliminar", fg_color=COLOR_DANGER, hover_color="#c0392b", command=self.on_eliminar_click, **btn_style_crud)
        self.boton_eliminar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        self.boton_limpiar = ctk.CTkButton(frame_botones_crud, text="Limpiar Campos", fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, command=self.limpiar_campos, **btn_style_crud)
        self.boton_limpiar.grid(row=1, column=0, columnspan=3, pady=(5, 10), padx=5, sticky="ew")

        # --- Frame 2: Ajuste de Inventario ---
        frame_ajuste_stock = ctk.CTkFrame(frame_formulario_scroll, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_ajuste_stock.grid(row=1, column=0, pady=(10, 20), sticky="ew")
        frame_ajuste_stock.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(frame_ajuste_stock, text="Ajuste de Inventario", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        
        btn_style_ajuste = {"font": ("Arial", 12, "bold"), "height": 35, "corner_radius": 10}

        self.boton_anadir_stock = ctk.CTkButton(frame_ajuste_stock, text="Añadir Stock (+)", command=lambda: self.abrir_ventana_ajuste("añadir"), fg_color=COLOR_AJUSTE_ADD, hover_color=COLOR_AJUSTE_ADD_HOVER, **btn_style_ajuste)
        self.boton_anadir_stock.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 20))
        
        self.boton_restar_stock = ctk.CTkButton(frame_ajuste_stock, text="Restar Stock (-)", command=lambda: self.abrir_ventana_ajuste("restar"), fg_color=COLOR_AJUSTE_REST, hover_color=COLOR_AJUSTE_REST_HOVER, **btn_style_ajuste)
        self.boton_restar_stock.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 20))


    def crear_widgets_tabla(self):
        """Crea el panel derecho (tabla y búsqueda)."""
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        
        frame_tabla.grid_columnconfigure(0, weight=1)
        frame_tabla.grid_rowconfigure(2, weight=1) # Fila de la tabla

        ctk.CTkLabel(frame_tabla, text="Inventario de Productos", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        frame_busqueda = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        frame_busqueda.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        frame_busqueda.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_busqueda, text="Buscar:", font=("Arial", 14)).pack(side="left", padx=(0, 10))
        self.entry_buscar = ctk.CTkEntry(frame_busqueda, textvariable=self.entry_buscar_var, height=30, font=("Arial", 12), border_color=COLOR_ACCENT_BUTTON)
        self.entry_buscar.pack(side="left", fill="x", expand=True)
        
        tree_frame = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columnas = ("id", "nombre", "precio_g", "costo_g", "stock_g", "umbral_g")
        self.tabla_productos = ttk.Treeview(tree_frame, columns=columnas, show="headings", style="Custom.Treeview")
        
        self.tabla_productos.heading("id", text="ID")
        self.tabla_productos.heading("nombre", text="Nombre")
        self.tabla_productos.heading("precio_g", text="Precio/g")
        self.tabla_productos.heading("costo_g", text="Costo/g")
        self.tabla_productos.heading("stock_g", text="Stock (g)")
        self.tabla_productos.heading("umbral_g", text="Umbral (g)")
        
        self.tabla_productos.column("id", width=30, anchor="e")
        self.tabla_productos.column("nombre", width=150, anchor="w")
        self.tabla_productos.column("precio_g", width=60, anchor="e")
        self.tabla_productos.column("costo_g", width=60, anchor="e")
        self.tabla_productos.column("stock_g", width=60, anchor="e")
        self.tabla_productos.column("umbral_g", width=60, anchor="e")
        
        self.tabla_productos.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tabla_productos.yview)
        self.tabla_productos.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindings
        self.entry_buscar.bind("<KeyRelease>", self.on_buscar_producto)
        self.tabla_productos.bind("<<TreeviewSelect>>", self.on_producto_select)

    # -------------------------------------------------------------------
    # FUNCIONES DE LOS BOTONES (Lógica de la Interfaz Principal)
    # -------------------------------------------------------------------

    def poblar_tabla(self, productos: List[Tuple]) -> None:
        """
        Limpia la tabla y la llena con la lista de productos dada.
        Aplica alerta visual si el stock está por debajo del umbral.
        """
        for item in self.tabla_productos.get_children():
            self.tabla_productos.delete(item)
            
        for prod in productos:
            id_prod, nombre, precio_g, costo_g, stock_g, umbral_g = prod
            
            # Formatear los números para la visualización
            precio_str = f"${precio_g:,.2f}"
            costo_str = f"${costo_g:,.2f}"
            stock_str = f"{stock_g:,.2f}"
            umbral_str = f"{umbral_g:,.2f}"
            
            tag = ''
            if stock_g <= 0:
                tag = 'stock_cero'
            elif stock_g <= umbral_g:
                tag = 'stock_bajo'
                
            self.tabla_productos.insert("", "end", 
                                        values=(id_prod, nombre, precio_str, costo_str, stock_str, umbral_str),
                                        tags=(tag,))

    def refrescar_tabla_productos(self) -> None:
        """Obtiene productos frescos, actualiza lista maestra y repuebla la tabla."""
        global lista_maestra_productos
        lista_maestra_productos = obtener_productos() 
        self.entry_buscar_var.set("")
        self.poblar_tabla(lista_maestra_productos)

    def on_guardar_click(self) -> None:
        """Callback para el botón 'Guardar Nuevo'."""
        nombre = self.entry_nombre_var.get().strip()
        precio_str = self.entry_precio_var.get()
        costo_str = self.entry_costo_var.get() 
        stock_ingresado_str = self.entry_stock_var.get()
        stock_unidad = self.stock_unidad_var.get() # Obtener la unidad seleccionada
        umbral_str = self.entry_umbral_var.get()

        if not nombre:
            messagebox.showwarning("Campos incompletos", "El nombre es obligatorio.")
            return
            
        try:
            # CORRECCIÓN: Aplicar .replace(',', '.') a todos los campos numéricos antes de float
            precio = float(precio_str.replace(',', '.'))
            costo = float(costo_str.replace(',', '.')) 
            umbral = float(umbral_str.replace(',', '.'))
            
            # CONVERSIÓN CRÍTICA: Convertir stock ingresado a gramos para la BD
            stock_ingresado = float(stock_ingresado_str.replace(',', '.'))
            factor = self.factores_conversion[stock_unidad]
            stock_en_gramos = stock_ingresado * factor
            
            # Validaciones después de conversión
            if precio <= 0 or stock_ingresado < 0 or umbral < 0 or stock_en_gramos < 0:
                messagebox.showwarning("Datos inválidos", "Los valores numéricos (Precio, Stock, Umbral) deben ser válidos y positivos.")
                return
            if costo > precio:
                messagebox.showwarning("Costo Inválido", "El Costo no puede ser mayor que el Precio.")
                return
        except ValueError:
            messagebox.showwarning("Datos inválidos", "Precio, Costo, Stock y Umbral deben ser valores numéricos válidos.")
            return

        sql = """
            INSERT INTO Producto (nombre, precioPorGramo, costoPorGramo, stockEnGramos, umbralMinimoGramos)
            VALUES (%s, %s, %s, %s, %s)
            """
        
        if database.ejecutar_consulta(sql, (nombre, precio, costo, stock_en_gramos, umbral)):
            messagebox.showinfo("Éxito", f"Producto '{nombre}' creado correctamente.")
            self.limpiar_campos() 
            self.refrescar_tabla_productos() 

    def on_actualizar_click(self) -> None:
        """Callback para el botón 'Actualizar'."""
        try:
            seleccion = self.tabla_productos.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona un producto.")
                return
            id_producto = self.tabla_productos.item(seleccion)["values"][0]
        except IndexError:
             messagebox.showwarning("Sin selección", "Por favor, selecciona un producto válido.")
             return
             
        nombre = self.entry_nombre_var.get().strip()
        precio_str = self.entry_precio_var.get()
        costo_str = self.entry_costo_var.get()
        umbral_str = self.entry_umbral_var.get()
        
        if not nombre:
            messagebox.showwarning("Campos incompletos", "El nombre es obligatorio.")
            return
            
        try:
            # CORRECCIÓN: Aplicar .replace(',', '.') a todos los campos numéricos antes de float
            precio = float(precio_str.replace(',', '.'))
            costo = float(costo_str.replace(',', '.'))
            umbral = float(umbral_str.replace(',', '.'))
            
            if precio <= 0:
                messagebox.showwarning("Datos inválidos", "El Precio/g debe ser mayor a cero.")
                return
            if costo < 0 or umbral < 0:
                messagebox.showwarning("Datos inválidos", "El Costo y Umbral no pueden ser negativos.")
                return
            if costo > precio:
                messagebox.showwarning("Costo Inválido", "El Costo no puede ser mayor que el Precio.")
                return
        except ValueError:
            messagebox.showwarning("Datos inválidos", "Precio, Costo y Umbral deben ser valores numéricos válidos.")
            return

        sql = """
            UPDATE Producto
            SET nombre = %s, precioPorGramo = %s, costoPorGramo = %s, umbralMinimoGramos = %s
            WHERE idProducto = %s
            """
        
        if database.ejecutar_consulta(sql, (nombre, precio, costo, umbral, id_producto)):
            messagebox.showinfo("Éxito", f"Producto '{nombre}' actualizado correctamente.")
            self.limpiar_campos() 
            self.refrescar_tabla_productos() 

    def on_eliminar_click(self) -> None:
        """Callback para el botón 'Eliminar'."""
        try:
            seleccion = self.tabla_productos.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona un producto.")
                return
            id_producto = self.tabla_productos.item(seleccion)["values"][0]
            nombre_producto = self.tabla_productos.item(seleccion)["values"][1]
        except IndexError:
             messagebox.showwarning("Sin selección", "Por favor, selecciona un producto válido.")
             return

        if messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro de que deseas eliminar '{nombre_producto}'?"):
            sql = "DELETE FROM Producto WHERE idProducto = %s"
            
            if database.ejecutar_consulta(sql, (id_producto,)):
                messagebox.showinfo("Éxito", f"Producto '{nombre_producto}' eliminado.")
                self.limpiar_campos() 
                self.refrescar_tabla_productos() 

    def limpiar_campos(self) -> None:
        """Limpia los campos y resetea el estado de los botones."""
        self.entry_nombre_var.set("")
        self.entry_precio_var.set("")
        self.entry_costo_var.set("")
        self.entry_stock_var.set("") 
        self.entry_umbral_var.set("")
        self.stock_unidad_var.set("Kilos (kg)") # Reseteamos la unidad
        
        # --- MEJORA DE FLUJO: Stock solo editable en modo 'Guardar Nuevo' ---
        self.entry_stock.configure(state="normal", fg_color=COLOR_ENTRY_BG) 
        self.combo_stock_unidad.configure(state="readonly")
        
        self.boton_guardar.configure(state="normal")
        self.boton_actualizar.configure(state="disabled")
        self.boton_anadir_stock.configure(state="disabled")
        self.boton_restar_stock.configure(state="disabled")

        if self.tabla_productos.focus():
            self.tabla_productos.selection_remove(self.tabla_productos.focus())
            
        if self.entry_buscar_var.get():
            self.entry_buscar_var.set("")
            self.poblar_tabla(lista_maestra_productos)
            
        self.entry_nombre.focus()

    def on_producto_select(self, event: Any) -> None:
        """Rellena el formulario al seleccionar un producto."""
        try:
            seleccion = self.tabla_productos.focus()
            if not seleccion:
                return
            datos = self.tabla_productos.item(seleccion)["values"]
        except IndexError:
            return 

        # Eliminar formato de moneda y comas para que los campos numéricos sean editables
        self.entry_nombre_var.set(datos[1])
        self.entry_precio_var.set(str(datos[2]).replace('$', '').replace(',', ''))
        self.entry_costo_var.set(str(datos[3]).replace('$', '').replace(',', ''))
        
        # --- CAMBIO CLAVE: Convertir el stock de Gramos a la mejor unidad para el display ---
        stock_en_gramos = float(str(datos[4]).replace(',', ''))
        cantidad_display, unidad_display = convertir_a_mejor_unidad(stock_en_gramos)
        
        self.entry_stock_var.set(f"{cantidad_display:,.2f}") # Muestra la cantidad convertida
        self.stock_unidad_var.set(unidad_display)          # Establece la unidad correspondiente
        # ------------------------------------------------------------------------------------
        
        self.entry_umbral_var.set(str(datos[5]).replace(',', ''))
        
        # --- MEJORA DE FLUJO: Deshabilitar Stock al editar ---
        self.entry_stock.configure(state="disabled", fg_color="#e0e0e0")
        self.combo_stock_unidad.configure(state="disabled") # Deshabilitar selector de unidad en modo edición
        
        self.boton_guardar.configure(state="disabled")
        self.boton_actualizar.configure(state="normal")
        self.boton_anadir_stock.configure(state="normal")
        self.boton_restar_stock.configure(state="normal")

    def abrir_ventana_ajuste(self, tipo_ajuste: str):
        """Abre la ventana modal para añadir o restar stock."""
        try:
            seleccion = self.tabla_productos.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Debe seleccionar un producto para ajustar el stock.")
                return
            datos = self.tabla_productos.item(seleccion)["values"]
            id_producto = datos[0]
            nombre_producto = datos[1]
        except IndexError:
            return

        VentanaAjusteStock(self, id_producto, nombre_producto, tipo_ajuste, self.on_ajuste_exitoso)

    def on_ajuste_exitoso(self):
        """Callback que se ejecuta cuando el ajuste de stock es exitoso."""
        self.refrescar_tabla_productos()
        self.limpiar_campos()

    def on_buscar_producto(self, event: Any):
        """Filtra la tabla en tiempo real basado en el texto de búsqueda."""
        termino_busqueda = self.entry_buscar_var.get().lower()
        
        if not termino_busqueda:
            self.poblar_tabla(lista_maestra_productos)
            return
        
        resultados_filtrados = []
        for producto_tuple in lista_maestra_productos:
            nombre_producto = str(producto_tuple[1]).lower()
            if termino_busqueda in nombre_producto:
                resultados_filtrados.append(producto_tuple)
                
        self.poblar_tabla(resultados_filtrados)

# -------------------------------------------------------------------
# --- CLASE Toplevel (VentanaAjusteStock) ---
# -------------------------------------------------------------------
class VentanaAjusteStock(ctk.CTkToplevel):
    def __init__(self, master, id_producto: int, nombre_producto: str, tipo_ajuste: str, callback_exito: callable):
        super().__init__(master)
        self.master = master
        self.id_producto = id_producto
        self.tipo_ajuste = tipo_ajuste
        self.callback_exito = callback_exito
        
        self.titulo = "Añadir Stock" if tipo_ajuste == "añadir" else "Restar Stock"
        self.color_boton = COLOR_AJUSTE_ADD if tipo_ajuste == "añadir" else COLOR_AJUSTE_REST
        self.color_hover = COLOR_AJUSTE_ADD_HOVER if tipo_ajuste == "añadir" else COLOR_AJUSTE_REST_HOVER

        self.configure(fg_color=COLOR_BACKGROUND)
        self.title(self.titulo)
        self.geometry("450x300") 
        self.resizable(False, False)

        self.vcmd = (master.register(self.validate_numeric_input_ajuste), '%S', '%P')
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.crear_widgets_ajuste(nombre_producto)
        
        self.grab_set()
        self.transient(master)
        self.wait_window()
        
    def validate_numeric_input_ajuste(self, S, P):
        """Wrapper para validación en la ventana modal."""
        return es_numero_o_decimal(S, P)

    def crear_widgets_ajuste(self, nombre_producto: str):
        frame = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        frame.grid_columnconfigure(1, weight=2) 
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame, text=f"Producto: {nombre_producto}", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(15, 10), padx=20)
        
        label_texto = "Cantidad a Añadir:" if self.tipo_ajuste == "añadir" else "Cantidad a Restar:"
        ctk.CTkLabel(frame, text=label_texto, font=("Arial", 14)).grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        
        # Aplicar validación aquí
        self.entry_cantidad = ctk.CTkEntry(frame, width=150, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON, validate="key", validatecommand=self.vcmd)
        self.entry_cantidad.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew") 
        
        ctk.CTkLabel(frame, text="Unidad:", font=("Arial", 14)).grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")
        unidades = list(self.master.factores_conversion.keys()) # Accede desde master
        self.combo_unidades = ctk.CTkComboBox(
            frame, 
            values=unidades, 
            state="readonly", 
            width=150, 
            height=35, 
            font=("Arial", 14),
            border_color=COLOR_ACCENT_BUTTON,
            button_color=COLOR_ACCENT_BUTTON,
            button_hover_color=COLOR_ACCENT_HOVER
        )
        self.combo_unidades.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.combo_unidades.set(unidades[0])
        
        btn_confirmar = ctk.CTkButton(
            frame, 
            text=f"Confirmar {self.titulo}", 
            command=self.on_confirmar_ajuste, 
            fg_color=self.color_boton, 
            hover_color=self.color_hover, 
            font=("Arial", 14, "bold"),
            height=40,
            corner_radius=10
        )
        btn_confirmar.grid(row=3, column=0, columnspan=2, pady=(20, 15), padx=20, sticky="ew")

    def on_confirmar_ajuste(self):
        try:
            # Reemplazar comas por puntos antes de la conversión final
            cantidad_ingresada = float(self.entry_cantidad.get().replace(',', '.'))
            if cantidad_ingresada <= 0:
                messagebox.showwarning("Cantidad Inválida", "La cantidad debe ser mayor a cero.", parent=self)
                return
        except ValueError:
            messagebox.showwarning("Cantidad Inválida", "Ingrese una cantidad numérica válida.", parent=self)
            return
            
        unidad_seleccionada = self.combo_unidades.get()
        if not unidad_seleccionada or unidad_seleccionada not in self.master.factores_conversion:
             messagebox.showwarning("Unidad Inválida", "Seleccione una unidad de medida válida.", parent=self)
             return
             
        factor = self.master.factores_conversion[unidad_seleccionada] 
        cantidad_en_gramos = cantidad_ingresada * factor
        
        if self.tipo_ajuste == "restar":
            stock_actual = get_producto_stock(self.id_producto) 
            if stock_actual is None: return
            if cantidad_en_gramos > stock_actual:
                messagebox.showerror("Stock Insuficiente", f"No se puede restar {cantidad_en_gramos:,.2f} g.\nStock actual: {stock_actual:,.2f} g", parent=self)
                return
            cantidad_en_gramos = -cantidad_en_gramos
        
        if actualizar_stock_producto(self.id_producto, cantidad_en_gramos): 
            tipo_str = "añadido" if self.tipo_ajuste == "añadir" else "restado"
            messagebox.showinfo("Éxito", f"Stock {tipo_str} correctamente.", parent=self.master)
            self.callback_exito()
            self.destroy()
        else:
            pass

# -------------------------------------------------------------------
# Carga inicial de datos
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

    app = VentanaGestionProductos()
    app.mainloop()