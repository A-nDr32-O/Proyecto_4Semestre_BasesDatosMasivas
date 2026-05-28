import sqlite3 
import customtkinter as ctk
from tkinter import messagebox, ttk 
from tkinter import Toplevel
from datetime import date, datetime
from typing import Tuple, List, Any, Dict, Optional
import sys
from tkinter import TclError 

# --- Importar la ruta desde config.py ---
from config import DB_PATH 

# --- Importar Tema ---
from theme import *
from theme import aplicar_estilo_treeview

# --- Importar Módulo de Base de Datos ---
import database 

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
# ... (se mantiene)
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión con la Base de Datos)
# -------------------------------------------------------------------
FECHA_HOY = date.today().strftime("%Y-%m-%d")

factores_conversion = {
    "Gramos (g)": 1.0,
    "Kilos (kg)": 1000.0,
    "Libras (lb)": 453.592,
    "Toneladas (t)": 1000000.0
}

def obtener_productos_lista() -> List[Dict[str, Any]]: 
    """
    Obtiene una lista de diccionarios de productos (para autocompletar).
    """
    sql = "SELECT idProducto, nombre, costoPorGramo FROM Producto ORDER BY nombre ASC"
    return database.obtener_diccionarios(sql)

def crear_nueva_compra(nombre_proveedor: str, fecha: str, carro_compras_agrupado: List[Dict[str, Any]], costo_total: float) -> bool:
    """
    Crea una nueva compra usando el nombre del proveedor.
    --- REFACTORIZADA para usar database.ejecutar_transaccion_multiples ---
    """
    operaciones = []

    # 1. Registrar la Compra (Maestra)
    # NOTA: Necesitamos el idCompra generado, lo que PyInstaller no permite
    # obtener fácilmente desde una función separada. Volveremos a usar una
    # conexión temporal para obtener el lastrowid, pero dentro de una transacción
    # que ejecutaremos en una conexión controlada localmente.
    
    conexion = None
    try:
        conexion = sqlite3.connect(DB_PATH)
        cursor = conexion.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        sql_compra = "INSERT INTO Compra (nombreProveedor, fecha, costoTotal, estado) VALUES (?, ?, ?, 'Pendiente')"
        cursor.execute(sql_compra, (nombre_proveedor, fecha, costo_total))
        id_compra_generado = cursor.lastrowid
        
        # 2. Registrar el Detalle de Compra
        sql_detalle = """
            INSERT INTO DetalleCompra (idCompra, idProducto, cantidadCompradaGramos, costoUnitarioGramo, subtotal, unidadOriginal)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        for item in carro_compras_agrupado: 
            cursor.execute(sql_detalle, (
                id_compra_generado, 
                item['id'], 
                item['cantidad_g'], 
                item['costo_g'], 
                item['subtotal'],
                item['unidad_original']
            ))
            
        conexion.commit()
        messagebox.showinfo("Éxito", f"Compra #{id_compra_generado} guardada como 'Pendiente'.")
        return True
        
    except sqlite3.Error as e:
        if conexion:
            conexion.rollback()
        # Utilizamos la lógica de error de database.py para mostrar el mensaje
        database._mostrar_error_db(e, "crear_nueva_compra")
        return False
    finally:
        if conexion:
            conexion.close()

def obtener_compras_maestras() -> List[Tuple]:
    """
    Obtiene el historial de compras para la tabla principal.
    """
    sql = """
        SELECT C.idCompra, C.nombreProveedor, C.fecha, C.costoTotal, C.estado
        FROM Compra AS C
        ORDER BY C.fecha DESC, C.idCompra DESC
        """
    return database.obtener_todos(sql)

def obtener_detalle_compra(id_compra: int) -> List[Tuple]:
    """
    Obtiene los items de una compra específica, incluyendo la unidad original.
    """
    sql = """
        SELECT P.nombre, DC.cantidadCompradaGramos, DC.costoUnitarioGramo, DC.subtotal, DC.unidadOriginal
        FROM DetalleCompra AS DC
        JOIN Producto AS P ON DC.idProducto = P.idProducto
        WHERE DC.idCompra = ?
        """
    return database.obtener_todos(sql, (id_compra,))

def procesar_recepcion_compra(id_compra: int) -> bool:
    """
    PROCESO CRÍTICO: Marca una compra como 'Recibida' y actualiza stock/costo.
    --- REFACTORIZADA para usar database.ejecutar_transaccion_multiples ---
    """
    
    # 1. Obtener los detalles de la compra para el stock y el nuevo costo
    sql_items = "SELECT idProducto, cantidadCompradaGramos, costoUnitarioGramo FROM DetalleCompra WHERE idCompra = ?"
    items_a_recibir = database.obtener_todos(sql_items, (id_compra,))
    
    if not items_a_recibir:
        messagebox.showwarning("Compra Vacía", "Esta compra no tiene productos para recibir.")
        return False

    operaciones = []
    
    # 2. Generar las operaciones de UPDATE
    sql_update_stock = "UPDATE Producto SET stockEnGramos = stockEnGramos + ? WHERE idProducto = ?"
    sql_update_costo = "UPDATE Producto SET costoPorGramo = ? WHERE idProducto = ?"
    
    for (id_producto, cantidad, costo_g) in items_a_recibir:
        # Añadir Stock
        operaciones.append((sql_update_stock, (cantidad, id_producto)))
        # Actualizar Costo
        operaciones.append((sql_update_costo, (costo_g, id_producto)))
    
    # 3. Marcar la Compra como Recibida (Debe ser la última operación)
    sql_update_compra = "UPDATE Compra SET estado = 'Recibida' WHERE idCompra = ?"
    operaciones.append((sql_update_compra, (id_compra,)))
    
    # 4. Ejecutar la Transacción
    if database.ejecutar_transaccion_multiples(operaciones):
        messagebox.showinfo("Éxito", f"¡Compra #{id_compra} recibida!\nEl stock y los costos han sido actualizados.")
        return True
    
    # database.ejecutar_transaccion_multiples ya maneja el rollback y muestra el error.
    return False

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana Principal - Historial)
# -------------------------------------------------------------------
# ... (El resto de la clase VentanaGestionCompras se mantiene) ...

class VentanaGestionCompras(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)

        self.title("Módulo de Compras a Proveedores")
        self.geometry("850x550")
        self.minsize(800, 500)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Fila de la tabla

        aplicar_estilo_treeview(self) 
        self.crear_widgets_principales()
        self.refrescar_lista_compras()

    def crear_widgets_principales(self):
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        btn_style = {"font": ("Arial", 12, "bold"), "height": 35, "corner_radius": 10}

        btn_nueva = ctk.CTkButton(frame_botones, text="Crear Nueva Compra", command=self.abrir_ventana_nueva_compra, fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, **btn_style)
        btn_nueva.pack(side="left", padx=5)
        
        btn_ver = ctk.CTkButton(frame_botones, text="Ver / Recibir Compra", command=self.abrir_ventana_detalle_compra, fg_color=COLOR_INFO, hover_color=COLOR_INFO_HOVER, **btn_style)
        btn_ver.pack(side="left", padx=5)
        
        btn_refrescar = ctk.CTkButton(frame_botones, text="Refrescar", command=self.refrescar_lista_compras, fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, **btn_style)
        btn_refrescar.pack(side="right", padx=5)

        # --- Frame de la Tabla ---
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        frame_tabla.grid_rowconfigure(1, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_tabla, text="Historial de Compras", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        tree_frame = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columnas = ("id", "proveedor", "fecha", "total", "estado")
        self.tabla_compras = ttk.Treeview(tree_frame, columns=columnas, show="headings", style="Custom.Treeview")
        
        self.tabla_compras.heading("id", text="ID Compra")
        self.tabla_compras.heading("proveedor", text="Proveedor (Nombre)") 
        self.tabla_compras.heading("fecha", text="Fecha")
        self.tabla_compras.heading("total", text="Costo Total ($)")
        self.tabla_compras.heading("estado", text="Estado")
        
        self.tabla_compras.column("id", width=60, anchor="e")
        self.tabla_compras.column("proveedor", width=200, anchor="w")
        self.tabla_compras.column("fecha", width=100, anchor="center")
        self.tabla_compras.column("total", width=100, anchor="e")
        self.tabla_compras.column("estado", width=100, anchor="center")
        
        self.tabla_compras.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tabla_compras.yview)
        self.tabla_compras.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Configuración de Tags de color ---
        self.tabla_compras.tag_configure("Pendiente", background="#FEF9E7", foreground="#856404")
        self.tabla_compras.tag_configure("Recibida", background="#E8F8F5", foreground="#145A32")

    def refrescar_lista_compras(self):
        for item in self.tabla_compras.get_children():
            self.tabla_compras.delete(item)
        compras = obtener_compras_maestras() 
        for compra in compras:
            id_compra, prov, fecha, total, estado = compra
            total_str = f"$ {total:,.2f}"
            tag = estado if estado in ("Pendiente", "Recibida") else ""
            self.tabla_compras.insert("", "end", values=(id_compra, prov, fecha, total_str, estado), tags=(tag,))
            
    def abrir_ventana_nueva_compra(self):
        VentanaNuevaCompra(self, self.refrescar_lista_compras)

    def abrir_ventana_detalle_compra(self):
        try:
            seleccion = self.tabla_compras.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona una compra del historial.")
                return
            datos = self.tabla_compras.item(seleccion)["values"]
            id_compra, estado = datos[0], datos[4]
        except IndexError:
            return 
            
        VentanaDetalleCompra(self, id_compra, estado, self.refrescar_lista_compras)


# -------------------------------------------------------------------
# CLASE Toplevel (VentanaNuevaCompra)
# -------------------------------------------------------------------
class VentanaNuevaCompra(ctk.CTkToplevel):
    def __init__(self, master, callback_exito: callable):
        super().__init__(master)
        self.master = master
        self.callback_exito = callback_exito
        
        self.configure(fg_color=COLOR_BACKGROUND)
        self.title("Crear Nueva Compra")
        self.geometry("900x650")
        self.minsize(850, 600)

        self.productos_map: Dict[str, Any] = {p['nombre']: p for p in obtener_productos_lista()}
        self.productos_nombres_lista: List[str] = list(self.productos_map.keys())
        self.carro_items: List[Dict[str, Any]] = [] # Lista de transacciones individuales
        self.last_edited_cost_field = 'unit'
        
        self.label_total_valor_var = ctk.StringVar(value="$ 0.00")
        
        self.entry_proveedor_var = ctk.StringVar()
        
        aplicar_estilo_treeview(self) 
        self.crear_widgets_nueva_compra()
        
        self.grab_set()
        self.transient(master)
        self.wait_window()
    
    # --- MÉTODO AUXILIAR PARA POBLAR LA TABLA AGRUPADA ---
    def _poblar_tabla_compra(self):
        """Limpia la tabla y la rellena con los ítems agrupados."""
        for item in self.tabla_carro_compra.get_children():
            self.tabla_carro_compra.delete(item)

        items_agrupados: Dict[int, Dict[str, Any]] = {}
        for item in self.carro_items:
            item_id = item['id']
            if item_id not in items_agrupados:
                # Inicializar el ítem agrupado (usando la primera transacción como base)
                items_agrupados[item_id] = {
                    'id': item_id,
                    'nombre': item['nombre'],
                    'cantidad_g': 0.0,
                    'costo_g': item['costo_g'], 
                    'subtotal': 0.0,
                    'unidad_original': item.get('unidad_original', 'Gramos') 
                }

            items_agrupados[item_id]['cantidad_g'] += item['cantidad_g']
            items_agrupados[item_id]['subtotal'] += item['subtotal']
            items_agrupados[item_id]['costo_g'] = item['costo_g']
            items_agrupados[item_id]['unidad_original'] = item.get('unidad_original', 'Gramos')

        for item_agrupado in items_agrupados.values():
            peso_total_g = item_agrupado['cantidad_g']
            subtotal_agrupado = item_agrupado['subtotal']
            costo_unitario = item_agrupado['costo_g']
            nombre = item_agrupado['nombre']

            # 1. Determinar la mejor unidad para el display
            cantidad_display, unidad_display = self._determinar_unidad_display(peso_total_g)
            
            # 2. Formatear valores
            cantidad_formateada = f"{cantidad_display:,.2f} {unidad_display}"
            costo_g_formateado = f"$ {costo_unitario:,.2f}" # Costo/g con 2 decimales y signo $
            subtotal_formateado = f"$ {subtotal_agrupado:,.2f}" # Subtotal con 2 decimales, comas y signo $
            
            self.tabla_carro_compra.insert("", "end", values=(nombre, cantidad_formateada, costo_g_formateado, subtotal_formateado))
            
    def _determinar_unidad_display(self, peso_en_gramos: float) -> Tuple[float, str]:
        """Lógica auxiliar para determinar la mejor unidad de visualización."""
        
        global factores_conversion 

        factores_inversos = {
            "Gramos": 1.0, 
            "Libras": factores_conversion["Libras (lb)"], 
            "Kilos": factores_conversion["Kilos (kg)"],
            "Toneladas": factores_conversion["Toneladas (t)"]
        }
        
        mejor_unidad = "Gramos"
        mejor_cantidad = peso_en_gramos
        
        if peso_en_gramos >= factores_inversos["Toneladas"]:
            mejor_unidad = "Toneladas"
            mejor_cantidad = peso_en_gramos / factores_inversos["Toneladas"]
        elif peso_en_gramos >= factores_inversos["Kilos"]:
            mejor_unidad = "Kilos"
            mejor_cantidad = peso_en_gramos / factores_inversos["Kilos"]
        elif peso_en_gramos >= factores_inversos["Libras"]:
            mejor_unidad = "Libras"
            mejor_cantidad = peso_en_gramos / factores_inversos["Libras"]
        
        if mejor_unidad == "Gramos":
            mejor_cantidad = round(mejor_cantidad, 2)
        
        return (mejor_cantidad, mejor_unidad)

    def crear_widgets_nueva_compra(self):
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Fila del carro

        # --- Estilos comunes ---
        entry_style = {"height": 35, "font": ("Arial", 14), "border_color": COLOR_ACCENT_BUTTON}
        combo_style = {"height": 35, "font": ("Arial", 14), "dropdown_font": ("Arial", 12), "border_color": COLOR_ACCENT_BUTTON, "button_color": COLOR_ACCENT_BUTTON, "button_hover_color": COLOR_ACCENT_HOVER}
        label_style = {"font": ("Arial", 14)}

        # --- Frame 1: Datos de la Compra ---
        frame_info = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_info.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        frame_info.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(frame_info, text="Datos de la Compra", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=4, padx=20, pady=(20, 10), sticky="w")

        ctk.CTkLabel(frame_info, text="Proveedor (Nombre):", **label_style).grid(row=1, column=0, padx=(20, 5), pady=5, sticky="w")
        self.entry_proveedor = ctk.CTkEntry(frame_info, textvariable=self.entry_proveedor_var, width=300, **entry_style)
        self.entry_proveedor.grid(row=1, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(frame_info, text="Fecha (YYYY-MM-DD):", **label_style).grid(row=1, column=2, padx=(20, 5), pady=5, sticky="w")
        self.entry_fecha = ctk.CTkEntry(frame_info, width=120, **entry_style)
        self.entry_fecha.grid(row=1, column=3, padx=(0, 20), pady=5)
        self.entry_fecha.insert(0, FECHA_HOY)

        # --- Frame 2: Añadir Producto ---
        frame_agregar = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_agregar.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        frame_agregar.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(frame_agregar, text="Añadir Producto a la Compra", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=5, padx=20, pady=(20, 10), sticky="w")

        ctk.CTkLabel(frame_agregar, text="Producto:", **label_style).grid(row=1, column=0, padx=(20, 5), pady=5, sticky="w")
        self.combo_productos = ctk.CTkComboBox(frame_agregar, values=self.productos_nombres_lista, width=300, **combo_style)
        self.combo_productos.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(frame_agregar, text="Cantidad:", **label_style).grid(row=2, column=0, padx=(20, 5), pady=5, sticky="w")
        self.entry_cantidad = ctk.CTkEntry(frame_agregar, width=120, **entry_style)
        self.entry_cantidad.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.combo_unidades = ctk.CTkComboBox(frame_agregar, values=list(factores_conversion.keys()), state="readonly", width=140, **combo_style)
        self.combo_unidades.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.combo_unidades.set("Kilos (kg)") # Default a Kilos

        ctk.CTkLabel(frame_agregar, text="Costo/g ($):", **label_style).grid(row=3, column=0, padx=(20, 5), pady=5, sticky="w")
        self.entry_costo_g = ctk.CTkEntry(frame_agregar, width=150, **entry_style)
        self.entry_costo_g.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(frame_agregar, text="Costo Total Ítem ($):", **label_style).grid(row=4, column=0, padx=(20, 5), pady=5, sticky="w")
        self.entry_costo_total = ctk.CTkEntry(frame_agregar, width=150, **entry_style)
        self.entry_costo_total.grid(row=4, column=1, columnspan=2, padx=5, pady=(5, 20), sticky="w")

        self.btn_anadir = ctk.CTkButton(frame_agregar, text="Añadir", command=self.on_agregar_al_carro, fg_color=COLOR_INFO, hover_color=COLOR_INFO_HOVER, font=("Arial", 12, "bold"), height=70)
        self.btn_anadir.grid(row=2, column=4, rowspan=2, padx=(20, 20), sticky="ns")

        # Bindings
        self.combo_productos.bind("<<ComboboxSelected>>", self.on_producto_select)
        self.combo_productos.bind("<KeyRelease>", self.on_producto_keyrelease)
        self.entry_cantidad.bind("<KeyRelease>", self.actualizar_costos)
        self.combo_unidades.bind("<<ComboboxSelected>>", self.actualizar_costos)
        self.entry_costo_g.bind("<KeyRelease>", self.calcular_total_desde_unitario)
        self.entry_costo_total.bind("<KeyRelease>", self.calcular_unitario_desde_total)

        # --- Frame 3: Carro de Compras ---
        frame_carro = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_carro.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        frame_carro.grid_rowconfigure(1, weight=1)
        frame_carro.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame_carro, text="Items de la Compra", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")

        tree_frame_carro = ctk.CTkFrame(frame_carro, fg_color="transparent")
        tree_frame_carro.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        tree_frame_carro.grid_rowconfigure(0, weight=1)
        tree_frame_carro.grid_columnconfigure(0, weight=1)

        columnas = ("nombre", "cantidad", "costo_g", "subtotal") 
        self.tabla_carro_compra = ttk.Treeview(tree_frame_carro, columns=columnas, show="headings", style="Custom.Treeview")
        self.tabla_carro_compra.heading("nombre", text="Producto")
        self.tabla_carro_compra.heading("cantidad", text="Cantidad") 
        self.tabla_carro_compra.heading("costo_g", text="Costo/g ($)")
        self.tabla_carro_compra.heading("subtotal", text="Subtotal ($)")
        
        self.tabla_carro_compra.column("cantidad", width=120, anchor="e")
        self.tabla_carro_compra.column("costo_g", width=100, anchor="e")
        self.tabla_carro_compra.column("subtotal", width=100, anchor="e")
        self.tabla_carro_compra.grid(row=0, column=0, sticky="nsew")
        
        scrollbar_carro = ttk.Scrollbar(tree_frame_carro, orient="vertical", command=self.tabla_carro_compra.yview)
        self.tabla_carro_compra.configure(yscrollcommand=scrollbar_carro.set)
        scrollbar_carro.grid(row=0, column=1, sticky="ns")

        # --- BOTÓN DE QUITAR (Muestra el aviso) ---
        btn_quitar = ctk.CTkButton(frame_carro, text="Quitar", command=self.on_quitar_item, fg_color=COLOR_DANGER, hover_color="#c0392b", width=80)
        btn_quitar.grid(row=1, column=1, padx=(0, 20), pady=(0, 20), sticky="n")

        # --- Frame 4: Finalizar ---
        frame_finalizar = ctk.CTkFrame(self, fg_color="transparent")
        frame_finalizar.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 20))
        
        # --- CONFIGURACIÓN DE 3 COLUMNAS para ALINEACIÓN CORRECTA ---
        frame_finalizar.grid_columnconfigure(0, weight=1, minsize=140) # Columna para Limpiar
        frame_finalizar.grid_columnconfigure(1, weight=3)            # Columna para Total (más ancha)
        frame_finalizar.grid_columnconfigure(2, weight=1, minsize=200) # Columna para Guardar
        
        # 1. Botón Limpiar (Columna 0, Alineado a la izquierda)
        btn_limpiar_carro = ctk.CTkButton(frame_finalizar, text="Limpiar Carrito", command=self.limpiar_carrito, fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, font=("Arial", 14, "bold"), height=40, corner_radius=10)
        btn_limpiar_carro.grid(row=0, column=0, padx=(10, 5), sticky="w")
        
        # 2. Total (Columna 1, Alineado al centro)
        total_frame = ctk.CTkFrame(frame_finalizar, fg_color="transparent")
        total_frame.grid(row=0, column=1, sticky="e", padx=5)
        
        self.label_total_texto = ctk.CTkLabel(total_frame, text="COSTO TOTAL:", font=("Arial", 16, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.label_total_texto.pack(side="left", padx=(0, 10))
        self.label_total_valor = ctk.CTkLabel(total_frame, textvariable=self.label_total_valor_var, font=("Arial", 16, "bold"), text_color=COLOR_DANGER)
        self.label_total_valor.pack(side="left")
        
        # 3. Botón Guardar Compra (Columna 2, Alineado a la derecha)
        self.btn_guardar = ctk.CTkButton(frame_finalizar, text="Guardar Compra (Pendiente)", command=self.guardar_compra, fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, font=("Arial", 14, "bold"), height=40, corner_radius=10)
        self.btn_guardar.grid(row=0, column=2, padx=(5, 10), sticky="e")
        
        # --- FIN CONFIGURACIÓN DE 3 COLUMNAS ---
        
    def get_cantidad_en_gramos(self) -> Optional[float]:
        try:
            cantidad_ingresada = float(self.entry_cantidad.get())
            unidad = self.combo_unidades.get()
            if not unidad: return None
            return cantidad_ingresada * factores_conversion[unidad]
        except (ValueError, TclError): 
            return None

    def calcular_total_desde_unitario(self, event=None):
        if self.focus_get() != self.entry_costo_g: return
        self.last_edited_cost_field = 'unit'
        try:
            costo_g = float(self.entry_costo_g.get())
            cantidad_g = self.get_cantidad_en_gramos()
            if cantidad_g is not None and cantidad_g > 0:
                total = costo_g * cantidad_g
                self.entry_costo_total.delete(0, "end")
                self.entry_costo_total.insert(0, f"{total:,.2f}") # Formato con comas
        except (ValueError, TclError): 
            self.entry_costo_total.delete(0, "end")

    def calcular_unitario_desde_total(self, event=None):
        if self.focus_get() != self.entry_costo_total: return
        self.last_edited_cost_field = 'total'
        try:
            total = float(self.entry_costo_total.get().replace(',', '')) # Eliminar comas para cálculo
            cantidad_g = self.get_cantidad_en_gramos()
            if cantidad_g is not None and cantidad_g > 0:
                costo_g = total / cantidad_g
                self.entry_costo_g.delete(0, "end")
                self.entry_costo_g.insert(0, f"{costo_g:.4f}")
        except (ValueError, TclError): 
            self.entry_costo_g.delete(0, "end")

    def actualizar_costos(self, event=None):
        if self.last_edited_cost_field == 'unit':
            self.calcular_total_desde_unitario()
        else:
            self.calcular_unitario_desde_total()

    def on_producto_select(self, event=None):
        nombre_sel = self.combo_productos.get()
        if nombre_sel in self.productos_map:
            costo_actual = self.productos_map[nombre_sel]['costoPorGramo']
            self.entry_costo_g.delete(0, "end")
            self.entry_costo_g.insert(0, f"{costo_actual:.4f}")
            self.entry_costo_total.delete(0, "end")
            self.entry_cantidad.delete(0, "end")
            self.last_edited_cost_field = 'unit'

    def on_producto_keyrelease(self, event):
        valor_escrito = self.combo_productos.get().lower()
        if not valor_escrito:
            self.combo_productos.configure(values=self.productos_nombres_lista)
        else:
            filtrados = [n for n in self.productos_nombres_lista if valor_escrito in n.lower()]
            self.combo_productos.configure(values=filtrados)

    def actualizar_total(self):
        total = sum(item['subtotal'] for item in self.carro_items)
        self.label_total_valor_var.set(f"$ {total:,.2f}")
        return total
        
    def limpiar_carrito(self):
        """Vacia el carro de compras y actualiza la UI."""
        if self.carro_items and messagebox.askyesno("Confirmar Limpiar Carrito", "¿Está seguro de que desea vaciar el carro de compras?", parent=self):
            self.carro_items = []
            self._poblar_tabla_compra()
            self.actualizar_total()
        elif not self.carro_items:
            messagebox.showinfo("Carrito Vacío", "El carro de compras ya está vacío.", parent=self)

    def on_agregar_al_carro(self):
        nombre_sel = self.combo_productos.get()
        
        # 1. Validación de Producto
        if nombre_sel not in self.productos_map:
            messagebox.showwarning("Producto Inválido", "Seleccione un producto válido de la lista.", parent=self)
            return

        # 2. Validación de Cantidad y Unidad
        cantidad_original = None
        try:
            cantidad_original = float(self.entry_cantidad.get())
        except ValueError:
            pass
            
        unidad_original_completa = self.combo_unidades.get()
        unidad_original = unidad_original_completa.split('(')[0].strip() # Ej: 'Kilos'
        
        cantidad_g = self.get_cantidad_en_gramos()

        if not unidad_original_completa or unidad_original_completa not in factores_conversion:
             messagebox.showwarning("Unidad Inválida", "Seleccione una unidad de medida válida.", parent=self)
             return
             
        if cantidad_g is None or cantidad_g <= 0:
            messagebox.showwarning("Cantidad Inválida", "Ingrese una cantidad numérica positiva.", parent=self)
            return
            
        # 3. Validación de Costos
        try:
            if self.last_edited_cost_field == 'total':
                self.calcular_unitario_desde_total()
            elif self.last_edited_cost_field == 'unit':
                 self.calcular_total_desde_unitario()
                 
            costo_g = float(self.entry_costo_g.get())
            
            if costo_g < 0:
                messagebox.showwarning("Costo Inválido", "El Costo/g no puede ser negativo.", parent=self)
                return
                
            subtotal = cantidad_g * costo_g
            if subtotal <= 0:
                 messagebox.showwarning("Costo Inválido", "El Subtotal debe ser mayor a cero. Verifique Costo/g.", parent=self)
                 return
                 
        except (ValueError, TclError):
            messagebox.showwarning("Costo Inválido", "Ingrese un Costo/g o Costo Total válido y numérico.", parent=self)
            return
            
        producto = self.productos_map[nombre_sel]
        
        # --- Almacenamos la transacción individual ---
        self.carro_items.append({
            'id': producto['idProducto'], 
            'nombre': producto['nombre'], 
            'cantidad_g': cantidad_g, 
            'costo_g': costo_g, 
            'subtotal': subtotal, 
            'cantidad_original': cantidad_original, 
            'unidad_original': unidad_original,     
        })
        
        # 1. Repoblar la tabla con la lógica de agrupación/visualización
        self._poblar_tabla_compra()
        
        # 2. Actualizar totales
        self.actualizar_total()
        
        # 3. Limpiar campos de entrada
        self.entry_cantidad.delete(0, "end")
        self.entry_costo_g.delete(0, "end")
        self.entry_costo_total.delete(0, "end")
        self.combo_productos.set("")

    def on_quitar_item(self):
        # NOTE: Para ítems agrupados, solo avisamos
        messagebox.showwarning("Aviso", "La función Quitar no está disponible para ítems agrupados. Considere limpiar y reingresar.", parent=self)
        return
            
    def guardar_compra(self):
        nombre_prov = self.entry_proveedor_var.get().strip() 
        
        # 1. Validación de Proveedor
        if not nombre_prov:
            messagebox.showwarning("Proveedor Inválido", "Debe ingresar el nombre del proveedor.", parent=self)
            return
            
        fecha_compra = self.entry_fecha.get().strip()
        
        # 2. Validación de Fecha
        try:
            datetime.strptime(fecha_compra, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("Fecha Inválida", "Formato de fecha incorrecto.\nUse YYYY-MM-DD (ej: 2025-11-21).", parent=self)
            return
            
        # 3. Validación de Carro
        if not self.carro_items:
            messagebox.showwarning("Carro Vacío", "Debe añadir al menos un producto.", parent=self)
            return
            
        costo_total = self.actualizar_total()
        
        # --- LÓGICA CLAVE: Agrupación de items antes de enviar a la BD ---
        
        items_agrupados_db = self._agrupar_items_para_db_final()
        
        if messagebox.askyesno("Confirmar Compra",
            f"Guardar esta compra por ${costo_total:,.2f} del proveedor {nombre_prov}?\n\n"
            "La compra se guardará como 'Pendiente' y el stock no se actualizará hasta que sea 'Recibida'.",
            parent=self):
            
            # NOTE: Usamos la función original ya que necesitamos el lastrowid,
            # pero el código de creación_nueva_compra se encarga de la transacción
            # internamente (con la conexión manual).
            if crear_nueva_compra(nombre_prov, fecha_compra, items_agrupados_db, costo_total):
                self.callback_exito()
                self.destroy()
                
    def _agrupar_items_para_db_final(self) -> List[Dict[str, Any]]:
        """
        Agrupa los ítems del carro por ID de Producto para el registro final en DetalleCompra.
        Usa el costo/g y la unidad original de la ÚLTIMA transacción del ítem.
        """
        items_finales: Dict[int, Dict[str, Any]] = {}
        
        for item in self.carro_items:
            item_id = item['id']
            
            if item_id in items_finales:
                # Sumar cantidad y subtotal
                items_finales[item_id]['cantidad_g'] += item['cantidad_g']
                items_finales[item_id]['subtotal'] += item['subtotal']
                # ACTUALIZAR el costo/g y unidad original con la ÚLTIMA transacción
                items_finales[item_id]['costo_g'] = item['costo_g']
                items_finales[item_id]['unidad_original'] = item['unidad_original']
            else:
                # Crear nuevo ítem
                items_finales[item_id] = {
                    'id': item_id,
                    'nombre': item['nombre'],
                    'cantidad_g': item['cantidad_g'],
                    'costo_g': item['costo_g'],
                    'subtotal': item['subtotal'],
                    'unidad_original': item['unidad_original']
                }
                
        # Devolver la lista de diccionarios agrupados
        return list(items_finales.values())


# -------------------------------------------------------------------
# CLASE Toplevel (VentanaDetalleCompra)
# -------------------------------------------------------------------
class VentanaDetalleCompra(ctk.CTkToplevel):
    def __init__(self, master, id_compra: int, estado: str, callback_exito: callable):
        super().__init__(master)
        self.master = master
        self.id_compra = id_compra
        self.estado = estado
        self.callback_exito = callback_exito
        
        self.configure(fg_color=COLOR_BACKGROUND)
        self.title(f"Detalle de Compra #{id_compra}")
        self.geometry("700x450")
        self.minsize(600, 400)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        aplicar_estilo_treeview(self) 
        self.crear_widgets_detalle()
        self.poblar_detalle()
        
        self.grab_set()
        self.transient(master)
        self.wait_window()

    def crear_widgets_detalle(self):
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame_tabla.grid_rowconfigure(1, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame_tabla, text=f"Items de la Compra #{self.id_compra} (Estado: {self.estado})", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        tree_frame_detalle = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame_detalle.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame_detalle.grid_rowconfigure(0, weight=1)
        tree_frame_detalle.grid_columnconfigure(0, weight=1)
        
        columnas = ("nombre", "cantidad_g", "costo_g", "subtotal")
        self.tabla_detalle = ttk.Treeview(tree_frame_detalle, columns=columnas, show="headings", style="Custom.Treeview")
        self.tabla_detalle.heading("nombre", text="Producto")
        self.tabla_detalle.heading("cantidad_g", text="Cantidad (g)")
        self.tabla_detalle.heading("costo_g", text="Costo/g ($)")
        self.tabla_detalle.heading("subtotal", text="Subtotal ($)")
        
        # --- AJUSTE DE ANCHOS DE COLUMNA ---
        self.tabla_detalle.column("nombre", width=150, anchor="w")
        self.tabla_detalle.column("cantidad_g", width=120, anchor="e") 
        self.tabla_detalle.column("costo_g", width=100, anchor="e")  
        self.tabla_detalle.column("subtotal", width=120, anchor="e") 
        # -----------------------------------
        
        self.tabla_detalle.grid(row=0, column=0, sticky="nsew")

        scrollbar_detalle = ttk.Scrollbar(tree_frame_detalle, orient="vertical", command=self.tabla_detalle.yview)
        self.tabla_detalle.configure(yscrollcommand=scrollbar_detalle.set)
        scrollbar_detalle.grid(row=0, column=1, sticky="ns")

        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        btn_style = {"font": ("Arial", 12, "bold"), "height": 40, "corner_radius": 10}

        if self.estado == "Pendiente":
            btn_recibir = ctk.CTkButton(frame_botones, text="Confirmar y Recibir Stock", command=self.confirmar_recepcion, fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, **btn_style)
            btn_recibir.pack(side="left", padx=5)
            
        btn_cerrar = ctk.CTkButton(frame_botones, text="Cerrar", command=self.destroy, fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, **btn_style)
        btn_cerrar.pack(side="right", padx=5)

    def poblar_detalle(self):
        detalles = obtener_detalle_compra(self.id_compra) 
        for fila in detalles:
            # Desempaquetamos 5 elementos
            if len(fila) == 5:
                nombre, cant_g, costo_g, subtotal, unidad_original = fila
            else:
                # Fallback por si la BD no fue actualizada correctamente
                nombre, cant_g, costo_g, subtotal = fila
                unidad_original = "Gramos" 

            # Formateamos la cantidad total con su unidad (mostrando la unidad original si existe)
            # 1. Cantidad (con 2 decimales y unidad original)
            cantidad_str = f"{cant_g:,.2f} {unidad_original}"
            
            # 2. Costo/g (con 2 decimales y signo $)
            costo_g_str = f"$ {costo_g:,.2f}" 
            
            # 3. Subtotal (con 2 decimales, comas y signo $)
            subtotal_str = f"$ {subtotal:,.2f}"

            self.tabla_detalle.insert("", "end", values=(nombre, cantidad_str, costo_g_str, subtotal_str))

    def confirmar_recepcion(self):
        if messagebox.askyesno("Confirmar Recepción",
            f"¿Está seguro de que desea recibir la Compra #{self.id_compra}?\n\n"
            "¡ESTA ACCIÓN ES IRREVERSIBLE!\n"
            "Se añadirá el stock al inventario y se actualizarán los costos.",
            parent=self):
            
            if procesar_recepcion_compra(self.id_compra):
                self.callback_exito()
                self.destroy()

# -------------------------------------------------------------------
# INICIAR LA APLICACIÓN
# -------------------------------------------------------------------

def iniciar_aplicacion():
    try:
        import customtkinter
    except ImportError:
         messagebox.showerror(
            "Error de Dependencias",
            "Falta 'customtkinter'.\n\nPor favor, instala la librería ejecutando:\n\npython -m pip install customtkinter"
        )
         sys.exit(1)
         
    app = VentanaGestionCompras()
    app.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()