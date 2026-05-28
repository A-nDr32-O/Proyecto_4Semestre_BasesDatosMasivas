import customtkinter as ctk
from tkinter import messagebox, ttk 
from datetime import date, datetime
from typing import Tuple, List, Any, Optional, Dict
import sys

# --- Importar Tema y Módulo de Base de Datos ---
from theme import *
from theme import aplicar_estilo_treeview
import database 

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
# ...
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión con la Base de Datos)
# --- REFACTORIZADA ---
# -------------------------------------------------------------------

def obtener_reporte_ventas(fecha_inicio: str, fecha_fin: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Consulta la BD para un rango de fechas y devuelve un resumen y un detalle.
    """
    # 1. Definimos la estructura de retorno por defecto
    resumen_dict = {
        'TotalVentas': 0.0, 'TotalTransacciones': 0,
        'TotalEfectivo': 0.0, 
        'TotalTransferencia': 0.0, 'TotalCosto': 0.0,
        'TotalUtilidad': 0.0
    }
    detalle: List[Dict[str, Any]] = []

    # --- Consulta A: Desglose REAL de Pagos (Usando TransaccionPago) ---
    sql_desglose_pagos = """
        SELECT
            T.metodo,
            SUM(T.montoAbonado) AS MontoTotal
        FROM TransaccionPago AS T
        JOIN Venta AS V ON T.idVenta = V.idVenta
        WHERE DATE(V.fechaHora) BETWEEN %s AND %s
        GROUP BY T.metodo
    """
    res_pagos = database.obtener_diccionarios(sql_desglose_pagos, (fecha_inicio, fecha_fin))
    
    # Rellenamos el diccionario resumen_dict con los montos de la nueva tabla
    ingreso_total = 0.0
    for fila in res_pagos:
        metodo = fila['metodo']
        monto = fila['MontoTotal']
        ingreso_total += monto
        
        if metodo == 'Efectivo':
            resumen_dict['TotalEfectivo'] = monto
        elif metodo == 'Transferencia':
            resumen_dict['TotalTransferencia'] = monto
    
    # 2. Obtener la suma total de VENTAS y NÚMERO DE TRANSACCIONES (basado en Venta)
    sql_resumen_ventas = """
        SELECT
            COUNT(idVenta) AS TotalTransacciones,
            SUM(montoTotal) AS TotalVentas
        FROM Venta
        WHERE DATE(fechaHora) BETWEEN %s AND %s
    """
    res_ventas = database.obtener_uno(sql_resumen_ventas, (fecha_inicio, fecha_fin))
    
    if res_ventas and res_ventas[1] is not None:
        resumen_dict['TotalTransacciones'] = res_ventas[0]
        resumen_dict['TotalVentas'] = res_ventas[1]
        
        if resumen_dict['TotalVentas'] > 0 and ingreso_total > 0:
            resumen_dict['TotalVentas'] = ingreso_total
        
    # --- Consulta 3: Resumen de Costos ---
    sql_resumen_costos = """
        SELECT SUM(DV.pesoVendido * P.costoPorGramo) AS TotalCosto
        FROM DetalleVenta AS DV
        JOIN Producto AS P ON DV.idProducto = P.idProducto
        JOIN Venta AS V ON DV.idVenta = V.idVenta
        WHERE DATE(V.fechaHora) BETWEEN %s AND %s
    """
    res_costos = database.obtener_uno(sql_resumen_costos, (fecha_inicio, fecha_fin))

    if res_costos and res_costos[0] is not None:
        resumen_dict['TotalCosto'] = res_costos[0]

    # --- Cálculo de Utilidad (Lógica de Python) ---
    resumen_dict['TotalUtilidad'] = resumen_dict['TotalVentas'] - resumen_dict['TotalCosto']
    
    # --- Consulta 4: Detalle de Productos (MODIFICADO para incluir la FECHA) ---
    sql_detalle = """
        SELECT P.nombre, 
               SUM(DV.pesoVendido) as TotalPeso, 
               SUM(DV.subtotal)    as TotalSubtotal, 
               SUM(DV.pesoVendido * P.costoPorGramo) AS TotalCostoProducto,
               DATE(V.fechaHora) AS FechaVenta,
               V.idVenta as IDVenta
        FROM DetalleVenta AS DV
        JOIN Producto AS P ON DV.idProducto = P.idProducto
        JOIN Venta AS V ON DV.idVenta = V.idVenta
        WHERE DATE(V.fechaHora) BETWEEN %s AND %s
        GROUP BY P.nombre, DATE(V.fechaHora), V.idVenta
        ORDER BY FechaVenta ASC, TotalSubtotal DESC
    """
    detalle = database.obtener_diccionarios(sql_detalle, (fecha_inicio, fecha_fin))

    return (resumen_dict, detalle)

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# -------------------------------------------------------------------

class VentanaReportes(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        
        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)

        self.title("Reporte de Ventas y Utilidad")
        self.geometry("900x750")
        self.minsize(850, 700)
        
        self.fecha_hoy: str = date.today().strftime("%Y-%m-%d")

        # --- Variables de CTk para los labels ---
        self.ventas_var = ctk.StringVar(value="$ 0.00")
        self.costo_var = ctk.StringVar(value="$ 0.00")
        self.utilidad_var = ctk.StringVar(value="$ 0.00")
        self.trans_var = ctk.StringVar(value="0")
        self.efectivo_var = ctk.StringVar(value="$ 0.00")
        self.transfer_var = ctk.StringVar(value="$ 0.00")

        # --- Layout Principal ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Selector Fechas
        self.grid_rowconfigure(1, weight=0) # Resumen
        self.grid_rowconfigure(2, weight=1) # Tabla

        # --- Estilo del Treeview ---
        aplicar_estilo_treeview(self)

        # --- Crear Widgets ---
        self.crear_widgets_selector()
        self.crear_widgets_resumen()
        self.crear_widgets_tabla()
        
        # --- Carga Inicial ---
        self.on_generar_reporte()

    def crear_widgets_selector(self) -> None:
        """Frame Superior: Selector de Fechas."""
        frame_selector = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_selector.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        ctk.CTkLabel(frame_selector, text="Fecha Inicio (YYYY-MM-DD):", font=("Arial", 14)).grid(row=0, column=0, padx=(20, 5), pady=20)
        self.entry_inicio = ctk.CTkEntry(frame_selector, width=120, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON)
        self.entry_inicio.grid(row=0, column=1, padx=5, pady=20)
        self.entry_inicio.insert(0, self.fecha_hoy)
        
        ctk.CTkLabel(frame_selector, text="Fecha Fin (YYYY-MM-DD):", font=("Arial", 14)).grid(row=0, column=2, padx=(15, 5), pady=20)
        self.entry_fin = ctk.CTkEntry(frame_selector, width=120, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON)
        self.entry_fin.grid(row=0, column=3, padx=5, pady=20)
        self.entry_fin.insert(0, self.fecha_hoy)
        
        self.boton_generar = ctk.CTkButton(
            frame_selector, text="Generar Reporte", 
            command=self.on_generar_reporte,
            fg_color=COLOR_ACCENT_BUTTON, 
            hover_color=COLOR_ACCENT_HOVER,
            font=("Arial", 14, "bold"),
            height=35,
            corner_radius=10
        )
        self.boton_generar.grid(row=0, column=4, padx=(20, 20), pady=20)
        
        frame_selector.grid_columnconfigure(4, weight=1)


    def crear_widgets_resumen(self) -> None:
        """Frame Medio: Resumen."""
        frame_resumen = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_resumen.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        frame_resumen.grid_columnconfigure(1, weight=1)
        
        font_label = ("Arial", 14)
        font_valor = ("Arial", 14, "bold")
        font_total = ("Arial", 16, "bold")
        
        ctk.CTkLabel(frame_resumen, text="Resumen del Período", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")

        # Fila 1: Ventas
        ctk.CTkLabel(frame_resumen, text="Ingresos Totales (Cobrados):", font=font_total).grid(row=1, column=0, sticky="w", pady=5, padx=20) 
        self.label_total_ventas = ctk.CTkLabel(frame_resumen, textvariable=self.ventas_var, font=font_total, text_color=COLOR_SUCCESS)
        self.label_total_ventas.grid(row=1, column=1, sticky="e", pady=5, padx=20)

        # Fila 2: Costo
        ctk.CTkLabel(frame_resumen, text="Total Costo de Mercancía (Egresos):", font=font_total).grid(row=2, column=0, sticky="w", pady=5, padx=20)
        self.label_total_costo = ctk.CTkLabel(frame_resumen, textvariable=self.costo_var, font=font_total, text_color=COLOR_DANGER)
        self.label_total_costo.grid(row=2, column=1, sticky="e", pady=5, padx=20)

        # Fila 3: Utilidad
        ctk.CTkLabel(frame_resumen, text="Utilidad Bruta (Ganancia):", font=font_total).grid(row=3, column=0, sticky="w", pady=5, padx=20)
        self.label_total_utilidad = ctk.CTkLabel(frame_resumen, textvariable=self.utilidad_var, font=font_total, text_color=COLOR_SUCCESS)
        self.label_total_utilidad.grid(row=3, column=1, sticky="e", pady=5, padx=20)
        
        # Separador
        ctk.CTkFrame(frame_resumen, height=1, fg_color="#e0e0e0").grid(row=4, column=0, columnspan=2, sticky='ew', padx=20, pady=10)

        # Fila 5: Transacciones
        ctk.CTkLabel(frame_resumen, text="N° Transacciones (Facturadas):", font=font_label).grid(row=5, column=0, sticky="w", pady=5, padx=20) 
        ctk.CTkLabel(frame_resumen, textvariable=self.trans_var, font=font_valor, text_color=COLOR_TEXT_PRIMARY).grid(row=5, column=1, sticky="e", pady=5, padx=20)

        # Separador
        ctk.CTkFrame(frame_resumen, height=1, fg_color="#e0e0e0").grid(row=6, column=0, columnspan=2, sticky='ew', padx=20, pady=10)
        
        # Fila 7: Efectivo
        ctk.CTkLabel(frame_resumen, text="Ingreso en Efectivo (Abonos):", font=font_label).grid(row=7, column=0, sticky="w", pady=3, padx=20)
        ctk.CTkLabel(frame_resumen, textvariable=self.efectivo_var, font=font_valor, text_color=COLOR_TEXT_PRIMARY).grid(row=7, column=1, sticky="e", pady=3, padx=20)
        
        # Fila 8: Transferencia
        ctk.CTkLabel(frame_resumen, text="Ingreso por Transferencia (Abonos):", font=font_label).grid(row=8, column=0, sticky="w", pady=(3, 20), padx=20)
        ctk.CTkLabel(frame_resumen, textvariable=self.transfer_var, font=font_valor, text_color=COLOR_TEXT_PRIMARY).grid(row=8, column=1, sticky="e", pady=(3, 20), padx=20)


    def crear_widgets_tabla(self) -> None:
        """Frame Inferior: Tabla de Detalles."""
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))
        frame_tabla.grid_columnconfigure(0, weight=1)
        frame_tabla.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_tabla, text="Productos Vendidos (Agrupados)", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # Frame para Treeview y Scrollbar
        tree_frame = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # --- MODIFICACIÓN DE COLUMNAS PARA INCLUIR FECHA Y ID ---
        columnas = ("id_venta", "fecha", "producto", "peso_total", "subtotal_total", "costo_total", "utilidad_prod")
        self.tabla_reporte = ttk.Treeview(tree_frame, columns=columnas, show="headings", style="Custom.Treeview")

        self.tabla_reporte.heading("id_venta", text="ID Venta")
        self.tabla_reporte.heading("fecha", text="Fecha")
        self.tabla_reporte.heading("producto", text="Producto")
        self.tabla_reporte.heading("peso_total", text="Peso (g)")
        self.tabla_reporte.heading("subtotal_total", text="Venta ($)")
        self.tabla_reporte.heading("costo_total", text="Costo ($)")
        self.tabla_reporte.heading("utilidad_prod", text="Utilidad ($)")

        self.tabla_reporte.column("id_venta", width=50, anchor="center")
        self.tabla_reporte.column("fecha", width=80, anchor="center")
        self.tabla_reporte.column("producto", width=150, anchor="w")
        self.tabla_reporte.column("peso_total", width=90, anchor="e")
        self.tabla_reporte.column("subtotal_total", width=90, anchor="e")
        self.tabla_reporte.column("costo_total", width=90, anchor="e")
        self.tabla_reporte.column("utilidad_prod", width=90, anchor="e")

        self.tabla_reporte.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tabla_reporte.yview)
        self.tabla_reporte.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def on_generar_reporte(self) -> None:
        fecha_ini = self.entry_inicio.get()
        fecha_fin = self.entry_fin.get()

        if not (self.validar_fecha(fecha_ini) and self.validar_fecha(fecha_fin)):
            messagebox.showerror("Fecha Inválida", "Formato de fecha incorrecto.\nUse YYYY-MM-DD.")
            return

        resumen, detalle = obtener_reporte_ventas(fecha_ini, fecha_fin) 

        # Actualizar Resumen (usando TransaccionPago)
        self.ventas_var.set(f"$ {resumen.get('TotalVentas', 0.0):,.2f}")
        self.costo_var.set(f"$ {resumen.get('TotalCosto', 0.0):,.2f}")
        
        utilidad = resumen.get('TotalUtilidad', 0.0)
        self.utilidad_var.set(f"$ {utilidad:,.2f}")
        
        if utilidad < 0:
            self.label_total_utilidad.configure(text_color=COLOR_DANGER)
        else:
            self.label_total_utilidad.configure(text_color=COLOR_SUCCESS)

        self.trans_var.set(f"{resumen.get('TotalTransacciones', 0)}")
        
        # Desglose de ingresos (ahora más preciso de TransaccionPago)
        self.efectivo_var.set(f"$ {resumen.get('TotalEfectivo', 0.0):,.2f}")
        self.transfer_var.set(f"$ {resumen.get('TotalTransferencia', 0.0):,.2f}") 

        # Limpiar y Poblar Tabla
        for item in self.tabla_reporte.get_children():
            self.tabla_reporte.delete(item)

        for fila in detalle:
            id_venta = fila['IDVenta']
            fecha = fila['FechaVenta']
            nombre = fila['nombre']
            peso = fila['TotalPeso']
            subtotal = fila['TotalSubtotal']
            costo_prod = fila['TotalCostoProducto']
            
            utilidad_prod = subtotal - costo_prod
            
            # Formatear valores
            peso_str = f"{peso:,.2f} g"
            subtotal_str = f"$ {subtotal:,.2f}"
            costo_str = f"$ {costo_prod:,.2f}"
            utilidad_str = f"$ {utilidad_prod:,.2f}"
            
            self.tabla_reporte.insert("", "end", values=(
                id_venta, 
                fecha,
                nombre, 
                peso_str, 
                subtotal_str, 
                costo_str, 
                utilidad_str
            ))

    def validar_fecha(self, fecha_texto: str) -> bool:
        try:
            datetime.strptime(fecha_texto, '%Y-%m-%d')
            return True
        except ValueError:
            return False

# --- Iniciar la aplicación ---
if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
         messagebox.showerror(
            "Error de Dependencias",
            "Falta 'customtkinter'.\n\nPor favor, instala la librería ejecutando:\n\npython -m pip install customtkinter"
        )
         sys.exit(1)

    app = VentanaReportes()
    app.mainloop()