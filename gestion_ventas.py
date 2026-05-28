import sqlite3
import customtkinter as ctk
from tkinter import messagebox, ttk
from tkinter import Toplevel
from datetime import datetime
import sys
from typing import List, Dict, Any, Optional, Callable, Tuple 
import os

# --- Importar la ruta desde config.py ---
from config import DB_PATH 

# --- Importar Tema y Módulo de Base de Datos ---
from theme import *
from theme import aplicar_estilo_treeview
import database 

# -------------------------------------------------------------------
# Lógica de Ruta Base (para assets como el logo)
# -------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión con la Base de Datos)
# -------------------------------------------------------------------
try:
    ID_USUARIO_ACTUAL: int = int(sys.argv[1])
except (IndexError, ValueError):
    ID_USUARIO_ACTUAL: int = 1 

def obtener_productos_disponibles() -> List[Dict[str, Any]]:
    """
    Obtiene todos los productos con stock > 0.
    """
    sql = "SELECT idProducto, nombre, precioPorGramo, stockEnGramos FROM Producto WHERE stockEnGramos > 0 ORDER BY nombre ASC"
    return database.obtener_diccionarios(sql)


def finalizar_venta(id_usuario: int, metodo_pago_final: str, carro_compras_agrupado: List[Dict[str, Any]], monto_total: float, pagos_registrados: List[Dict[str, Any]]) -> bool:
    """
    Registra la venta, actualiza el inventario, registra los abonos y maneja la deuda.
    --- FUNCIÓN REFACTORIZADA para usar database.ejecutar_transaccion_multiples ---
    """
    
    # NOTA CRÍTICA: La inserción en Venta y la obtención del lastrowid
    # requiere una transacción manual local, similar a gestion_compras.py.
    # NO podemos usar ejecutar_transaccion_multiples para la primera parte
    # porque no devuelve el ID generado. 
    
    conexion = None
    try:
        conexion = sqlite3.connect(DB_PATH)
        cursor = conexion.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Registrar la Venta (Obtener idVenta)
        sql_venta = "INSERT INTO Venta (idUsuario, fechaHora, montoTotal, metodoPago) VALUES (?, ?, ?, ?)"
        cursor.execute(sql_venta, (id_usuario, fecha_actual, monto_total, metodo_pago_final))
        id_venta_generado = cursor.lastrowid

        # 2. Operaciones Secundarias (Detalle, Stock, Abonos, Deuda)
        operaciones_secundarias = []

        # 2a. Registrar el Detalle de Venta y Actualizar Stock
        sql_detalle = "INSERT INTO DetalleVenta (idVenta, idProducto, pesoVendido, subtotal) VALUES (?, ?, ?, ?)"
        sql_update_stock = "UPDATE Producto SET stockEnGramos = stockEnGramos - ? WHERE idProducto = ?"
        
        for item in carro_compras_agrupado: 
            operaciones_secundarias.append((sql_detalle, (id_venta_generado, item['id'], item['peso'], item['subtotal']))) 
            operaciones_secundarias.append((sql_update_stock, (item['peso'], item['id'])))
            
        # 2b. Registrar TODAS las transacciones de pago (Abonos)
        sql_transaccion = "INSERT INTO TransaccionPago (idVenta, montoAbonado, metodo, fechaHora) VALUES (?, ?, ?, ?)"
        for pago in pagos_registrados:
            operaciones_secundarias.append((sql_transaccion, (id_venta_generado, pago['monto'], pago['metodo'], fecha_actual)))

        # 2c. Manejar la Deuda Pendiente (si el método final es 'Pendiente')
        if metodo_pago_final == "Pendiente":
            monto_abonado = sum(p['monto'] for p in pagos_registrados)
            monto_pendiente_restante = monto_total - monto_abonado
            
            if monto_pendiente_restante > 0.01:
                 sql_pendiente = """
                    INSERT INTO VentaPendiente (idVenta, fechaRegistro, montoPendiente, estadoDeuda) 
                    VALUES (?, ?, ?, 'Pendiente')
                """
                 operaciones_secundarias.append((sql_pendiente, (id_venta_generado, fecha_actual, monto_pendiente_restante)))
        
        
        # 3. Ejecutar el resto de las operaciones usando la misma conexión
        for sql, params in operaciones_secundarias:
             cursor.execute(sql, params)
             
        conexion.commit()
        return True
        
    except sqlite3.Error as e:
        messagebox.showerror("Error de Transacción", f"No se pudo completar la venta. Se revirtieron los cambios.\nDetalle: {e}")
        if conexion:
            conexion.rollback()
        return False
    finally:
        if conexion:
            conexion.close()

# -------------------------------------------------------------------
# LÓGICA DE UNIDADES Y DISPLAY 
# -------------------------------------------------------------------
def _determinar_unidad_display(peso_en_gramos: float) -> Tuple[float, str]:
    """
    Determina la unidad de peso más apropiada para mostrar la cantidad.
    Devuelve la cantidad formateada y el sufijo (ej: 2.5, "Kilos").
    """
    # Factores de conversión: Gramos -> Factor
    factores_inversos = {
        "Gramos": 1.0, 
        "Libras": 453.592, 
        "Kilos": 1000.0,
        "Toneladas": 1000000.0
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

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana Principal de Ventas)
# -------------------------------------------------------------------
class VentanaVentas(ctk.CTkFrame):

    def __init__(self, master: Any, **kwargs):
        super().__init__(master, fg_color=COLOR_BACKGROUND, **kwargs)
        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.factores_conversion = {
            "Gramos (g)": 1.0, 
            "Kilos (kg)": 1000.0,
            "Libras (lb)": 453.592, 
        }

        self.productos_maestros = obtener_productos_disponibles()
        self.carro_compras: List[Dict[str, Any]] = [] # Lista de transacciones individuales
        self.nombre_productos_disponibles: List[str] = [p['nombre'] for p in self.productos_maestros]
        self.producto_seleccionado: Optional[Dict[str, Any]] = None

        self.total_venta_var = ctk.DoubleVar(value=0.0)
        self.entry_producto_var = ctk.StringVar(value="")
        self.entry_cantidad_var = ctk.StringVar(value="") 
        self.combo_unidad_var = ctk.StringVar(value=list(self.factores_conversion.keys())[0]) 
        
        aplicar_estilo_treeview(master)

        self.crear_widgets()
        self.poblar_tabla_carrito()

    def _agrupar_items_para_db(self) -> List[Dict[str, Any]]:
        """
        Procesa la lista de transacciones individuales (self.carro_compras)
        y devuelve una lista de ítems únicos agrupados por idProducto.
        """
        items_finales: Dict[int, Dict[str, Any]] = {}
        
        for item in self.carro_compras:
            item_id = item['id']
            
            if item_id in items_finales:
                items_finales[item_id]['peso'] += item['peso']
                items_finales[item_id]['subtotal'] += item['subtotal']
            else:
                items_finales[item_id] = {
                    'id': item_id,
                    'nombre': item['nombre'],
                    'peso': item['peso'],
                    'precio_unitario': item['precio_unitario'],
                    'subtotal': item['subtotal']
                }
                
        return list(items_finales.values())

    def crear_widgets(self):
        # Frame del Carrito de Compras (Columna 0)
        frame_carrito = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=15)
        frame_carrito.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        frame_carrito.grid_rowconfigure(2, weight=1)
        frame_carrito.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_carrito, text="CARRITO DE COMPRAS", font=("Arial", 16, "bold"), text_color=COLOR_PRIMARY_NAV).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Separador
        ctk.CTkFrame(frame_carrito, height=2, fg_color=COLOR_ENTRY_BG).grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")

        # --- SOLUCIÓN SCROLLBAR CARRITO ---
        tree_frame_carrito = ctk.CTkFrame(frame_carrito, fg_color="transparent")
        tree_frame_carrito.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        tree_frame_carrito.grid_rowconfigure(0, weight=1)
        tree_frame_carrito.grid_columnconfigure(0, weight=1)
        # --- FIN SOLUCIÓN SCROLLBAR CARRITO ---
        
        # Tabla del Carrito
        self.tree_carrito = ttk.Treeview(tree_frame_carrito, 
                                          columns=("Nombre", "Cantidad", "Subtotal"), 
                                          show="headings", 
                                          style="Custom.Treeview")
        self.tree_carrito.heading("Nombre", text="PRODUCTO")
        self.tree_carrito.heading("Cantidad", text="PESO / CANTIDAD") 
        self.tree_carrito.heading("Subtotal", text="SUBTOTAL")
        
        self.tree_carrito.column("Nombre", width=150, anchor="w")
        self.tree_carrito.column("Cantidad", width=80, anchor="e") 
        self.tree_carrito.column("Subtotal", width=80, anchor="e")
        
        self.tree_carrito.grid(row=0, column=0, sticky="nsew") 

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_frame_carrito, command=self.tree_carrito.yview) 
        scrollbar.grid(row=0, column=1, sticky="ns") 
        self.tree_carrito.configure(yscrollcommand=scrollbar.set)
        
        # Frame de Resumen y Botones (Abajo del carrito)
        frame_resumen = ctk.CTkFrame(frame_carrito, fg_color=COLOR_ENTRY_BG, corner_radius=10)
        frame_resumen.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(frame_resumen, text="TOTAL:", font=("Arial", 20, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=10, pady=10)
        
        self.label_total_valor = ctk.CTkLabel(frame_resumen, text="", font=("Arial", 20, "bold"), text_color=COLOR_ACCENT_BUTTON)
        self.label_total_valor.pack(side="right", padx=10, pady=10)
        
        btn_pagar = ctk.CTkButton(frame_carrito, text="PROCESAR PAGO", font=("Arial", 16, "bold"), height=50, fg_color=COLOR_ACCENT_BUTTON, hover_color=COLOR_ACCENT_HOVER, command=self.abrir_ventana_pago)
        btn_pagar.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        btn_borrar = ctk.CTkButton(frame_carrito, text="LIMPIAR CARRITO", font=("Arial", 12), fg_color=COLOR_LOGOUT_BTN, hover_color=COLOR_LOGOUT_HOVER, command=self.limpiar_carrito)
        btn_borrar.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Frame de Entrada de Producto (Columna 1)
        frame_entrada = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=15)
        frame_entrada.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        frame_entrada.grid_columnconfigure(0, weight=1)
        frame_entrada.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_entrada, text="AÑADIR PRODUCTO", font=("Arial", 16, "bold"), text_color=COLOR_PRIMARY_NAV).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        
        # Campo Producto
        ctk.CTkLabel(frame_entrada, text="Producto:", font=("Arial", 12, "bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.combo_productos = ctk.CTkComboBox(frame_entrada, 
                                            variable=self.entry_producto_var,
                                            values=self.nombre_productos_disponibles,
                                            command=self.on_producto_select,
                                            font=("Arial", 12),
                                            height=35,
                                            dropdown_fg_color=COLOR_ENTRY_BG)
        self.combo_productos.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.combo_productos.bind("<KeyRelease>", self.on_producto_keyrelease)
        
        # Campo Cantidad
        ctk.CTkLabel(frame_entrada, text="Cantidad:", font=("Arial", 12, "bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=1, column=1, padx=20, pady=(10, 0), sticky="w")
        
        frame_cantidad_unidad = ctk.CTkFrame(frame_entrada, fg_color="transparent")
        frame_cantidad_unidad.grid(row=2, column=1, padx=20, pady=(0, 10), sticky="ew")
        frame_cantidad_unidad.grid_columnconfigure(0, weight=1)
        
        self.entry_cantidad = ctk.CTkEntry(frame_cantidad_unidad, 
                                        textvariable=self.entry_cantidad_var, 
                                        font=("Arial", 12), 
                                        height=35,
                                        width=100, 
                                        fg_color=COLOR_ENTRY_BG,
                                        justify="right")
        self.entry_cantidad.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # COMBO BOX RESTAURADO
        self.combo_unidades = ctk.CTkComboBox(frame_cantidad_unidad,
                                            variable=self.combo_unidad_var,
                                            values=list(self.factores_conversion.keys()) + ["Toneladas (t)"], 
                                            state="readonly",
                                            width=100,
                                            height=35,
                                            font=("Arial", 12),
                                            button_color=COLOR_ACCENT_BUTTON)
        self.combo_unidades.pack(side="right", fill="x", padx=(5, 0))
        # ----------------------------------------------------------------------------------
        
        # Botón Añadir
        btn_anadir = ctk.CTkButton(frame_entrada, text="AÑADIR AL CARRITO", font=("Arial", 14, "bold"), height=45, fg_color=COLOR_INFO, hover_color=COLOR_INFO_HOVER, command=self.anadir_a_carrito)
        btn_anadir.grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")

        # Info del Producto
        self.label_info_producto_var = ctk.StringVar(value="Seleccione un producto para ver el precio y stock.")
        self.label_info_producto = ctk.CTkLabel(frame_entrada, textvariable=self.label_info_producto_var, font=("Arial", 12), justify="left", wraplength=450)
        self.label_info_producto.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")
        
        # Botón para Quitar Ítem
        btn_quitar = ctk.CTkButton(frame_entrada, text="QUITAR ÍTEM SELECCIONADO", font=("Arial", 12), fg_color=COLOR_DANGER, hover_color="#c0392b", command=self.quitar_de_carrito)
        btn_quitar.grid(row=5, column=0, columnspan=2, padx=20, pady=(20, 20), sticky="ew")


    def poblar_tabla_carrito(self):
        for item in self.tree_carrito.get_children():
            self.tree_carrito.delete(item)
            
        total = 0.0
        # Reagrupar ítems antes de poblar la tabla
        items_agrupados: Dict[int, Dict[str, Any]] = {}

        for item in self.carro_compras:
            item_id = item['id']
            if item_id not in items_agrupados:
                # Inicializar el ítem agrupado (usando la primera transacción como base)
                items_agrupados[item_id] = {
                    'id': item_id,
                    'nombre': item['nombre'],
                    'peso': 0.0,
                    'subtotal': 0.0,
                    'precio_unitario': item['precio_unitario'] 
                }

            items_agrupados[item_id]['peso'] += item['peso']
            items_agrupados[item_id]['subtotal'] += item['subtotal']
            
        for item_agrupado in items_agrupados.values():
            peso_total_g = item_agrupado['peso']
            subtotal_agrupado = item_agrupado['subtotal']
            nombre = item_agrupado['nombre']

            # Determinar la mejor unidad para el display
            cantidad_display, unidad_display = _determinar_unidad_display(peso_total_g)
            
            # Formatear la cantidad y subtotal
            cantidad_formateada = f"{cantidad_display:,.2f} {unidad_display}"
            subtotal_formateado = f"$ {subtotal_agrupado:,.2f}"
            
            self.tree_carrito.insert("", "end", values=(nombre, cantidad_formateada, subtotal_formateado))
            total += subtotal_agrupado
            
        self.total_venta_var.set(total)
        self.label_total_valor.configure(text=f"$ {total:,.2f}")


    def limpiar_carrito(self):
        if self.carro_compras and messagebox.askyesno("Confirmar Limpiar Carrito", "¿Está seguro de que desea vaciar el carrito de compras?"):
            
            # Restaurar stock de todos los ítems antes de borrar el carro
            for item in self.carro_compras:
                peso_quitado = item['peso']
                producto_a_restaurar = next(
                    (p for p in self.productos_maestros if p['idProducto'] == item['id']), 
                    None
                )
                if producto_a_restaurar:
                    producto_a_restaurar['stockEnGramos'] += peso_quitado

            self.carro_compras = []
            self.poblar_tabla_carrito()
            self.productos_maestros = obtener_productos_disponibles()
            self.nombre_productos_disponibles = [p['nombre'] for p in self.productos_maestros]
            messagebox.showinfo("Limpieza Exitosa", "El carrito ha sido vaciado.")
        elif not self.carro_compras:
            messagebox.showinfo("Carrito Vacío", "El carrito de compras ya está vacío.")
            
    def quitar_de_carrito(self):
        seleccion = self.tree_carrito.selection()
        if not seleccion:
            messagebox.showwarning("Selección Requerida", "Debe seleccionar un ítem del carrito para quitarlo.")
            return

        item_index_en_tabla = self.tree_carrito.index(seleccion[0])
        
        # NOTA: Quitar el ítem de una tabla agrupada requiere más lógica.
        # Por simplicidad y consistencia con el flujo del carrito de TPV (que es transaccional),
        # esta implementación original opera sobre la tabla visual (agrupada). 
        # Si se desea un control fino, se debe quitar de self.carro_compras por ID y recalcular.
        
        messagebox.showwarning("Aviso", "La función Quitar Ítem solo borra la primera ocurrencia agrupada en esta versión. Considere usar 'Limpiar Carrito' para vaciar completamente.", parent=self)
        
        # Intento de borrado de la primera aparición agrupada (menos preciso, pero evita IndexErrors)
        try:
            item_a_borrar_nombre = self.tree_carrito.item(seleccion[0], 'values')[0]
            
            # Encuentra el índice de la primera coincidencia del nombre en la lista no agrupada
            index_to_remove = next((i for i, item in enumerate(self.carro_compras) if item['nombre'] == item_a_borrar_nombre), -1)
            
            if index_to_remove != -1:
                item_quitado = self.carro_compras.pop(index_to_remove)
                nombre_producto = item_quitado['nombre']
                peso_quitado = item_quitado['peso']
                
                producto_a_restaurar = next(
                    (p for p in self.productos_maestros if p['idProducto'] == item_quitado['id']), 
                    None
                )
                if producto_a_restaurar:
                    producto_a_restaurar['stockEnGramos'] += peso_quitado
                
                self.poblar_tabla_carrito()
                self.actualizar_info_producto(None) 
                messagebox.showinfo("Ítem Quitado", f"Una porción de '{nombre_producto}' ha sido quitada del carrito.")
            else:
                messagebox.showerror("Error Interno", "No se pudo encontrar el ítem seleccionado en el carrito.")
        except Exception:
             messagebox.showerror("Error Interno", "Error al procesar la selección para borrar.")


    def on_producto_keyrelease(self, event: Any) -> None:
        if event.keysym in ("Up", "Down", "Left", "Right", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Tab", "Return", "BackSpace", "Delete"):
            return

        valor_escrito = self.combo_productos.get().lower()

        if not valor_escrito:
            self.combo_productos.configure(values=self.nombre_productos_disponibles)
            self.actualizar_info_producto(None)
        else:
            nombres_filtrados = [
                nombre for nombre in self.nombre_productos_disponibles
                if valor_escrito in nombre.lower()
            ]
            self.combo_productos.configure(values=nombres_filtrados)
            
            if self.combo_productos.get() in nombres_filtrados:
                 self.actualizar_info_producto(None)

    def on_producto_select(self, seleccion: str):
        self.actualizar_info_producto(seleccion)
        
    def actualizar_info_producto(self, seleccion: Optional[str]):
        nombre_producto = seleccion if seleccion else self.entry_producto_var.get()
        
        self.producto_seleccionado = next(
            (p for p in self.productos_maestros if p['nombre'] == nombre_producto), 
            None
        )

        if self.producto_seleccionado:
            p = self.producto_seleccionado
            
            # --- Stock Multi-Unidad ---
            precio_formateado = f"${p['precioPorGramo']:,.2f}"
            stock_g = p['stockEnGramos']
            stock_info = f"Stock Disponible:\n{stock_g:,.0f} gramos (Base)"
            
            factores_disp = {
                "Kilos (kg)": 1000.0,
                "Libras (lb)": 453.592,
                "Toneladas (t)": 1000000.0
            }
            
            for unidad, factor in factores_disp.items():
                cantidad_convertida = stock_g / factor
                if cantidad_convertida >= 1: 
                    stock_info += f"\n{cantidad_convertida:,.2f} {unidad.split('(')[0].strip()}"
                elif factor == 1000.0 and cantidad_convertida >= 0.01:
                    stock_info += f"\n{cantidad_convertida:,.4f} {unidad.split('(')[0].strip()}"


            info = (
                f"ID: {p['idProducto']}\n"
                f"Precio: {precio_formateado} por gramo\n"
                f"{stock_info}"
            )
            
            self.label_info_producto.configure(text_color=COLOR_TEXT_PRIMARY)
        else:
            info = "Producto no encontrado o fuera de stock."
            self.label_info_producto.configure(text_color=COLOR_DANGER)
            
        self.label_info_producto_var.set(info)

    def anadir_a_carrito(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("Selección Requerida", "Debe seleccionar un producto válido de la lista.")
            return

        # 1. Validación de Cantidad y Tipo
        try:
            cantidad_ingresada = float(self.entry_cantidad_var.get().replace(',', '.'))
            if cantidad_ingresada <= 0:
                raise ValueError("Cantidad debe ser positiva.")
        except ValueError:
            messagebox.showerror("Entrada Inválida", "Por favor, ingrese una cantidad numérica válida y positiva.")
            return

        # 2. Validación de Unidad
        unidad_seleccionada_completa = self.combo_unidad_var.get()
        unidad_original = unidad_seleccionada_completa.split('(')[0].strip()
        
        factores_venta = {
            "Gramos (g)": 1.0, 
            "Kilos (kg)": 1000.0,
            "Libras (lb)": 453.592, 
            "Toneladas (t)": 1000000.0
        }

        if not unidad_seleccionada_completa or unidad_seleccionada_completa not in factores_venta:
             messagebox.showwarning("Unidad Inválida", "Seleccione una unidad de medida válida.")
             return
             
        factor_conversion = factores_venta.get(unidad_seleccionada_completa, 1.0)
        peso_en_gramos = cantidad_ingresada * factor_conversion
        
        producto_id = self.producto_seleccionado['idProducto']
        stock_actual = self.producto_seleccionado['stockEnGramos']
        precio_gramo = self.producto_seleccionado['precioPorGramo']
        nombre_producto = self.producto_seleccionado['nombre']
        
        if peso_en_gramos > stock_actual:
            messagebox.showerror("Stock Insuficiente", f"Stock insuficiente para {nombre_producto}.\nStock actual: {stock_actual:,.2f} g.\nSe intentó vender: {peso_en_gramos:,.2f} g.")
            return

        subtotal = peso_en_gramos * precio_gramo
        
        self.carro_compras.append({
            'id': producto_id,
            'nombre': nombre_producto,
            'peso': peso_en_gramos, 
            'cantidad_original': cantidad_ingresada, 
            'unidad_original': unidad_original,
            'precio_unitario': precio_gramo,
            'subtotal': subtotal
        })
        
        self.producto_seleccionado['stockEnGramos'] -= peso_en_gramos
        self.entry_cantidad_var.set("")
        self.actualizar_info_producto(None)
        
        self.poblar_tabla_carrito()

    def _agrupar_items_para_db(self) -> List[Dict[str, Any]]:
        """
        Procesa la lista de transacciones individuales (self.carro_compras)
        y devuelve una lista de ítems únicos agrupados por idProducto.
        """
        items_finales: Dict[int, Dict[str, Any]] = {}
        
        for item in self.carro_compras:
            item_id = item['id']
            
            if item_id in items_finales:
                items_finales[item_id]['peso'] += item['peso']
                items_finales[item_id]['subtotal'] += item['subtotal']
            else:
                items_finales[item_id] = {
                    'id': item_id,
                    'nombre': item['nombre'],
                    'peso': item['peso'],
                    'precio_unitario': item['precio_unitario'],
                    'subtotal': item['subtotal']
                }
                
        return list(items_finales.values())


    def abrir_ventana_pago(self):
        if not self.carro_compras:
            messagebox.showwarning("Carrito Vacío", "El carrito de compras está vacío. Agregue productos antes de procesar el pago.")
            return
            
        carro_agrupado_db = self._agrupar_items_para_db()
        
        VentanaPago(self.master, 
                    self.total_venta_var.get(), 
                    carro_agrupado_db, 
                    self.on_pago_exitoso)


    def on_pago_exitoso(self):
        self.productos_maestros = obtener_productos_disponibles() 
        self.nombre_productos_disponibles = [p['nombre'] for p in self.productos_maestros]
        self.carro_compras = []
        self.poblar_tabla_carrito()
        self.entry_producto_var.set("")
        self.actualizar_info_producto(None)

# -------------------------------------------------------------------
# VENTANA DE PAGO (TOPLEVEL) - REESTRUCTURADA PARA PAGOS MIXTOS
# -------------------------------------------------------------------
class VentanaPago(ctk.CTkToplevel):
    def __init__(self, master_window: Any, monto_total: float, carro_compras_agrupado: List[Dict[str, Any]], callback_on_exito: Callable, **kwargs):
        super().__init__(master_window, **kwargs)
        self.master_window = master_window
        self.monto_total_inicial = monto_total
        self.carro_compras_agrupado = carro_compras_agrupado 
        self.callback_on_exito = callback_on_exito
        
        self.pagos_registrados: List[Dict[str, Any]] = [] 
        
        self.title("Procesar Pago")
        self.geometry("600x650")
        self.transient(master_window)
        self.grab_set() 
        self.resizable(False, False)
        
        self.monto_pendiente_var = ctk.DoubleVar(value=monto_total)
        self.monto_pendiente_str_var = ctk.StringVar(value=f"$ {self.monto_total_inicial:,.2f}")
        self.paga_con_var = ctk.DoubleVar(value=0.0)
        self.vueltas_var = ctk.StringVar(value="$ 0.00")
        
        self.frame_main = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND)
        self.frame_main.pack(fill="both", expand=True, padx=20, pady=20)
        self.frame_main.grid_columnconfigure(0, weight=1)
        
        self.crear_widgets_pago()
        self.actualizar_estado_pago()

    def crear_widgets_pago(self):
        
        frame_pago = ctk.CTkFrame(self.frame_main, fg_color=COLOR_WHITE_FRAME, corner_radius=15)
        frame_pago.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame_pago.grid_columnconfigure(0, weight=1)

        # --- RESUMEN DE PAGO ---
        ctk.CTkLabel(frame_pago, text="RESUMEN DE PAGO", font=("Arial", 18, "bold"), text_color=COLOR_PRIMARY_NAV).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Total a Pagar / Pendiente
        frame_totales = ctk.CTkFrame(frame_pago, fg_color=COLOR_ENTRY_BG, corner_radius=10)
        frame_totales.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        ctk.CTkLabel(frame_totales, text="TOTAL INICIAL:", font=("Arial", 14, "bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(frame_totales, text=f"$ {self.monto_total_inicial:,.2f}", font=("Arial", 14, "bold"), text_color=COLOR_DANGER).grid(row=0, column=1, padx=10, pady=5, sticky="e")

        ctk.CTkLabel(frame_totales, text="MONTO PENDIENTE:", font=("Arial", 18, "bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.label_pendiente = ctk.CTkLabel(frame_totales, textvariable=self.monto_pendiente_str_var, font=("Arial", 18, "bold"), text_color=COLOR_DANGER)
        self.label_pendiente.grid(row=1, column=1, padx=10, pady=5, sticky="e")
        
        frame_totales.grid_columnconfigure(1, weight=1)
        self.monto_pendiente_var.trace_add("write", self.actualizar_color_pendiente)

        # --- REGISTRO DE PAGO (PARCIAL) ---
        
        frame_registro = ctk.CTkFrame(frame_pago, fg_color="transparent")
        frame_registro.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        frame_registro.grid_columnconfigure((0, 1), weight=1)
        frame_registro.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(frame_registro, text="Monto a Pagar:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(5, 0))
        self.entry_monto = ctk.CTkEntry(frame_registro, 
                                        textvariable=self.paga_con_var, 
                                        font=("Arial", 14), 
                                        height=40, 
                                        fg_color=COLOR_ENTRY_BG,
                                        justify="right")
        self.entry_monto.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        self.entry_monto.bind("<KeyRelease>", self.actualizar_vueltas) 
        
        self.combo_metodo = ctk.CTkComboBox(frame_registro, 
                                            values=["Efectivo", "Transferencia"], 
                                            state="readonly", 
                                            font=("Arial", 14),
                                            height=40,
                                            width=150)
        self.combo_metodo.grid(row=1, column=1, sticky="ew", padx=5)
        self.combo_metodo.set("Efectivo")

        btn_registrar = ctk.CTkButton(frame_registro, text="Registrar Pago", 
                                      command=self.on_registrar_pago_parcial,
                                      fg_color=COLOR_INFO,
                                      hover_color=COLOR_INFO_HOVER,
                                      height=40)
        btn_registrar.grid(row=1, column=2, padx=(5, 0))

        # Vueltas (solo para referencia de efectivo)
        ctk.CTkLabel(frame_registro, text="Vueltas:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=(5, 0))
        ctk.CTkLabel(frame_registro, textvariable=self.vueltas_var, font=("Arial", 14, "bold"), text_color=COLOR_SUCCESS, height=40, fg_color=COLOR_ENTRY_BG, corner_radius=5).grid(row=3, column=0, sticky="ew", padx=(0, 5))

        # --- TABLA DE PAGOS REGISTRADOS ---
        frame_tabla = ctk.CTkFrame(frame_pago, fg_color="transparent")
        frame_tabla.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 10))
        frame_tabla.grid_columnconfigure(0, weight=1)
        frame_tabla.grid_rowconfigure(0, weight=1)

        columnas = ("monto", "metodo")
        self.tree_pagos = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=3) 
        self.tree_pagos.heading("monto", text="MONTO")
        self.tree_pagos.heading("metodo", text="MÉTODO")
        self.tree_pagos.column("monto", width=120, anchor="e") 
        self.tree_pagos.column("metodo", width=180, anchor="w") 
        self.tree_pagos.grid(row=0, column=0, sticky="nsew")

        # Añadir scrollbar al treeview 
        scrollbar_pagos = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree_pagos.yview)
        self.tree_pagos.configure(yscrollcommand=scrollbar_pagos.set)
        scrollbar_pagos.grid(row=0, column=1, sticky="ns")

        # --- BOTONES DE FINALIZACIÓN ---
        
        frame_finalizar = ctk.CTkFrame(frame_pago, fg_color="transparent")
        frame_finalizar.grid(row=4, column=0, pady=(15, 20), padx=20, sticky="ew")
        frame_finalizar.grid_columnconfigure(0, weight=1)

        self.btn_pagar_final = ctk.CTkButton(
            frame_finalizar, 
            text="FINALIZAR VENTA (Pagado)", 
            fg_color=COLOR_SUCCESS, 
            hover_color=COLOR_ACCENT_HOVER,
            command=self.on_confirmar_pago_final,
            font=("Arial", 14, "bold"), 
            height=45
        )
        self.btn_pagar_final.grid(row=0, column=0, sticky="ew", pady=5)
        
        self.btn_credito = ctk.CTkButton(
            frame_finalizar, 
            text="REGISTRAR MONTO PENDIENTE COMO CRÉDITO", 
            fg_color=COLOR_WARNING, 
            hover_color="#e09010",
            command=self.on_registrar_credito,
            font=("Arial", 14, "bold"), 
            height=45
        )
        self.btn_credito.grid(row=1, column=0, sticky="ew", pady=5)
        
        
    # --- LÓGICA DE VALIDACIÓN Y ACTUALIZACIÓN ---
    
    def actualizar_color_pendiente(self, *args):
        """Cambia el color del label pendiente y le da formato de moneda."""
        pendiente = self.monto_pendiente_var.get()
        
        self.monto_pendiente_str_var.set(f"$ {pendiente:,.2f}")
        
        if pendiente <= 0.01:
            self.label_pendiente.configure(text_color=COLOR_SUCCESS)
        else:
            self.label_pendiente.configure(text_color=COLOR_DANGER)

    def actualizar_vueltas(self, *args):
        """Calcula las vueltas si se está ingresando un monto en efectivo."""
        try:
            paga_con = self.paga_con_var.get()
            pendiente = self.monto_pendiente_var.get()
            
            if pendiente > 0:
                vueltas = max(0.0, paga_con - pendiente)
            else:
                vueltas = 0.0 
                
            self.vueltas_var.set(f"$ {vueltas:,.2f}")
        except Exception:
            self.vueltas_var.set("$ 0.00")

    def actualizar_estado_pago(self):
        """Calcula el monto pagado, actualiza el pendiente y habilita/deshabilita botones."""
        pagado = sum(p['monto'] for p in self.pagos_registrados)
        pendiente = self.monto_total_inicial - pagado
        
        if abs(pendiente) < 0.01: 
            pendiente = 0.0
            
        self.monto_pendiente_var.set(pendiente) 
        
        # Actualizar la tabla de pagos
        for item in self.tree_pagos.get_children():
            self.tree_pagos.delete(item)
        for pago in self.pagos_registrados:
            monto_str = f"$ {pago['monto']:,.2f}"
            self.tree_pagos.insert("", "end", values=(monto_str, pago['metodo']))
            
        # Habilitar/Deshabilitar botones
        if pendiente <= 0:
            self.btn_pagar_final.configure(state="normal", text="FINALIZAR VENTA (Pagado Totalmente)")
            self.btn_credito.configure(state="disabled")
            self.entry_monto.configure(state="disabled")
            self.combo_metodo.configure(state="disabled")
        else:
            self.btn_pagar_final.configure(state="disabled")
            self.btn_credito.configure(state="normal")
            self.entry_monto.configure(state="normal")
            self.combo_metodo.configure(state="readonly")

    def on_registrar_pago_parcial(self):
        """Registra un monto parcial con el método seleccionado."""
        try:
            monto = self.paga_con_var.get()
            metodo = self.combo_metodo.get()
            pendiente = self.monto_pendiente_var.get()

            if monto <= 0:
                messagebox.showwarning("Monto Inválido", "El monto a pagar debe ser mayor a cero.", parent=self)
                return
            
            if monto > pendiente:
                if messagebox.askyesno("Pago Excedente", f"El monto ingresado (${monto:,.2f}) excede el pendiente (${pendiente:,.2f}). ¿Desea registrar solo el monto pendiente?", parent=self):
                    monto = pendiente
                else:
                    return 
            
            if monto <= 0: return 

            self.pagos_registrados.append({'monto': monto, 'metodo': metodo})
            
            self.paga_con_var.set(0.0)
            self.vueltas_var.set("$ 0.00")
            self.entry_monto.focus()

            self.actualizar_estado_pago()
            
            if self.monto_pendiente_var.get() <= 0:
                 messagebox.showinfo("Pago Completo", "¡El monto ha sido cubierto! Presione 'FINALIZAR VENTA'.", parent=self)

        except Exception as e:
            messagebox.showerror("Error de Registro", f"Asegúrese de ingresar un valor numérico válido.\nDetalle: {e}", parent=self)

    # --- FINALIZACIÓN DE VENTA ---
    
    def on_confirmar_pago_final(self):
        """Finaliza la venta cuando el monto pendiente es cero."""
        if self.monto_pendiente_var.get() > 0.01:
            messagebox.showwarning("Pendiente", "Aún queda un monto pendiente. Registre un pago o conviértalo a crédito.", parent=self)
            return

        metodo_final = "Mixto"
        if not self.pagos_registrados:
             metodo_final = "Efectivo"
        elif len(self.pagos_registrados) == 1:
             metodo_final = self.pagos_registrados[0]['metodo']
        
        # El carro_compras_agrupado ya está listo y fue pasado en el init
        if finalizar_venta(ID_USUARIO_ACTUAL, metodo_final, self.carro_compras_agrupado, self.monto_total_inicial, self.pagos_registrados):
            messagebox.showinfo("Venta Exitosa", "Venta registrada con éxito.", parent=self.master_window)
            self.callback_on_exito()
            self.destroy()
            
    def on_registrar_credito(self):
        """Finaliza la venta registrando el monto restante como pendiente (crédito)."""
        pendiente = self.monto_pendiente_var.get()
        if pendiente <= 0.01:
            messagebox.showwarning("Estado Inválido", "El monto ya está pagado. Use 'FINALIZAR VENTA'.", parent=self)
            return
            
        if not messagebox.askyesno("Confirmar Crédito", 
                                   f"Se registrará la Venta como PENDIENTE con un monto de ${pendiente:,.2f} a cuenta.\n\n"
                                   "¿Desea continuar?", 
                                   parent=self):
            return
            
        if finalizar_venta(ID_USUARIO_ACTUAL, "Pendiente", self.carro_compras_agrupado, self.monto_total_inicial, self.pagos_registrados):
            messagebox.showinfo("Venta a Crédito", f"Venta registrada como PENDIENTE. Monto de deuda: ${pendiente:,.2f}", parent=self.master_window)
            self.callback_on_exito()
            self.destroy()


# --- INICIO DEL MÓDULO ---
if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
         messagebox.showerror(
            "Error de Dependencias",
            "Falta 'customtkinter'.\n\nPor favor, instala la librería ejecutando:\n\npython -m pip install customtkinter"
        )
         sys.exit(1)
         
    app = ctk.CTk()
    app.title(f"Punto de Venta (TPV) - Usuario: {ID_USUARIO_ACTUAL}")
    app.geometry("950x650") 
    app.minsize(900, 600)
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)
    
    VentanaVentas(app).grid(row=0, column=0, sticky="nsew")

    app.protocol("WM_DELETE_WINDOW", app.quit) 
    
    app.mainloop()