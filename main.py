import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk 
import sys
import os
import subprocess 
from datetime import datetime
from PIL import Image, ImageTk

# --- Importar Tema ---
from theme import *

# --- Importar Módulo de Base de Datos ---
import database 

# -------------------------------------------------------------------
# Lógica de Ruta Base (para assets como el logo)
# -------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # Estamos en un ejecutable (PyInstaller)
    BASE_DIR = sys._MEIPASS 
else:
    # Estamos en un script .py normal
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------------------------------------------

ctk.set_appearance_mode("Light")
class App(ctk.CTk):
    def __init__(self, id_usuario_actual: int, nombre_usuario_actual: str, rol_usuario_actual: str) -> None:
        super().__init__()

        self.id_usuario_actual = id_usuario_actual
        self.nombre_usuario_actual = nombre_usuario_actual
        self.rol_usuario_actual = rol_usuario_actual

        self.title(f"Panel Principal ({self.rol_usuario_actual}) - Frutos Secos La Sabana")
        self.geometry("1100x720") 
        self.minsize(1000, 600)
        self.configure(fg_color=COLOR_BACKGROUND) 

        # Configurar layout de la cuadrícula
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Frame de Navegación Lateral ---
        self.navigation_frame = ctk.CTkFrame(self, 
                                             width=180, 
                                             corner_radius=0, 
                                             fg_color=COLOR_PRIMARY_NAV) 
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        
        # --- Frame Deslizable para Botones ---
        self.scrollable_nav_frame = ctk.CTkScrollableFrame(self.navigation_frame,
                                                            fg_color="transparent",
                                                            corner_radius=0)
        self.scrollable_nav_frame.grid(row=2, column=0, sticky="nsew", pady=(20, 0))
        self.navigation_frame.grid_rowconfigure(2, weight=1) 

        # --- Título (Muestra el Nombre) ---
        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame,
                                                  text=self.nombre_usuario_actual,
                                                  compound="left",
                                                  font=ctk.CTkFont(size=16, weight="bold"),
                                                  text_color=COLOR_TEXT_NAV)
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=(20, 0))

        # --- Logo ---
        logo_bg_frame = ctk.CTkFrame(self.navigation_frame, 
                                     fg_color=COLOR_WHITE_FRAME, 
                                     corner_radius=20)
        logo_bg_frame.grid(row=1, column=0, padx=20, pady=(10, 20))

        logo_path = os.path.join(BASE_DIR, "Logo frutos.png")

        try:
            pil_image = Image.open(logo_path)
            target_width = 160 
            w_percent = (target_width / float(pil_image.size[0]))
            h_size = int((float(pil_image.size[1]) * float(w_percent)))
            
            self.logo_image = ctk.CTkImage(light_image=pil_image, size=(target_width, h_size))
            
            self.logo_label = ctk.CTkLabel(logo_bg_frame, image=self.logo_image, text="")
            self.logo_label.grid(row=0, column=0, padx=10, pady=10)

        except Exception:
            self.logo_label = ctk.CTkLabel(logo_bg_frame, text="TPV La Sabana\n(Logo Error)", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_PRIMARY_NAV)
            self.logo_label.grid(row=0, column=0, padx=10, pady=10)


        # --- Botones de navegación (DENTRO del frame deslizable) ---
        
        btn_config = {
            "corner_radius": 10,
            "height": 40,
            "border_spacing": 10,
            "text_color": COLOR_TEXT_NAV, 
            "hover_color": COLOR_PRIMARY_HOVER, 
            "anchor": "w",
            "font": ctk.CTkFont(size=14)
        }

        self.home_button = ctk.CTkButton(self.scrollable_nav_frame,
                                         text="Nueva Venta (TPV)",
                                         fg_color="transparent",
                                         command=self.abrir_tpv,
                                         **btn_config)
        self.home_button.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 5))

        self.cierre_button = ctk.CTkButton(self.scrollable_nav_frame,
                                           text="Realizar Cierre",
                                           fg_color="transparent",
                                           command=self.abrir_cierre,
                                           **btn_config)
        self.cierre_button.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Botones solo para Administrador
        if self.rol_usuario_actual == "Administrador":

            # self.proveedores_button ya no existe
            
            self.productos_button = ctk.CTkButton(self.scrollable_nav_frame,
                                                  text="Gestionar Productos",
                                                  fg_color="transparent",
                                                  command=self.abrir_productos,
                                                  **btn_config)
            self.productos_button.grid(row=4, column=0, sticky="ew", padx=10, pady=5) # El row ahora es 4

            self.reportes_button = ctk.CTkButton(self.scrollable_nav_frame,
                                                 text="Generar Reportes",
                                                 fg_color="transparent",
                                                 command=self.abrir_reportes,
                                                 **btn_config)
            self.reportes_button.grid(row=5, column=0, sticky="ew", padx=10, pady=5) # El row ahora es 5

            self.mermas_button = ctk.CTkButton(self.scrollable_nav_frame,
                                               text="Registrar Mermas",
                                               fg_color="transparent",
                                               command=self.abrir_mermas,
                                               **btn_config)
            self.mermas_button.grid(row=6, column=0, sticky="ew", padx=10, pady=5) # El row ahora es 6

            self.usuarios_button = ctk.CTkButton(self.scrollable_nav_frame,
                                                 text="Gestionar Usuarios",
                                                 fg_color="transparent",
                                                 command=self.abrir_usuarios,
                                                 **btn_config)
            self.usuarios_button.grid(row=7, column=0, sticky="ew", padx=10, pady=5) # El row ahora es 7


        # --- Botones de Salida (FUERA del frame deslizable) ---
        
        self.logout_button = ctk.CTkButton(self.navigation_frame,
                                           text="Cerrar Sesión",
                                           command=self.on_cerrar_sesion,
                                           fg_color=COLOR_LOGOUT_BTN,
                                           hover_color=COLOR_LOGOUT_HOVER,
                                           font=("Arial", 14, "bold"),
                                           height=40,
                                           corner_radius=10)
        self.logout_button.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 5)) 

        self.exit_button = ctk.CTkButton(self.navigation_frame,
                                         text="Salir",
                                         command=self.on_salir,
                                         fg_color=COLOR_DANGER,
                                         hover_color="#c0392b",
                                         font=("Arial", 14, "bold"),
                                         height=40,
                                         corner_radius=10)
        self.exit_button.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20)) 

        # --- Frame Principal de Contenido (Home) ---
        self.home_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.home_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(0, weight=0)
        self.home_frame.grid_rowconfigure(1, weight=1)

        self.crear_widgets_home()
        
        # Cargar datos iniciales del dashboard
        self.update_resumen_del_dia()
        self.update_alertas_stock_bajo()
        
        # Configurar protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self.on_salir)

    # -------------------------------------------------------------------
    # MÉTODOS DE LANZAMIENTO
    # -------------------------------------------------------------------
    
    def lanzar_script(self, nombre_script: str) -> None:
        """Ejecuta un script de Python (.py) como un proceso separado."""
        try:
            interprete = sys.executable
            
            if getattr(sys, 'frozen', False):
                ruta_base_app = os.path.dirname(sys.executable)
            else:
                ruta_base_app = BASE_DIR
                
            ruta_script = os.path.join(ruta_base_app, nombre_script)
            
            if not os.path.exists(ruta_script):
                messagebox.showerror("Error de Archivo", f"No se encontró el script: {nombre_script}")
                return

            # Pasamos ID de usuario como primer argumento para la BD
            cmd = [interprete, ruta_script, str(self.id_usuario_actual)]
            subprocess.Popen(cmd)
            
        except Exception as e:
            messagebox.showerror("Error al Abrir Módulo", f"No se pudo iniciar {nombre_script}.\nError: {e}")

    def abrir_tpv(self) -> None:
        self.lanzar_script("gestion_ventas.py")
        
    def abrir_cierre(self) -> None:
        self.lanzar_script("gestion_cierre.py")

    def abrir_compras(self) -> None:
        self.lanzar_script("gestion_compras.py")

    # --- MÉTODO ELIMINADO ---
    # def abrir_proveedores(self) -> None:
    #     self.lanzar_script("gestion_proveedores.py")

    def abrir_productos(self) -> None:
        self.lanzar_script("gestion_productos.py")

    def abrir_reportes(self) -> None:
        self.lanzar_script("gestion_reportes.py")

    def abrir_mermas(self) -> None:
        self.lanzar_script("gestion_mermas.py")

    def abrir_usuarios(self) -> None:
        self.lanzar_script("gestion_usuarios.py")
        
    def abrir_deudas(self) -> None: 
        self.lanzar_script("gestion_deudas.py")

    def on_cerrar_sesion(self) -> None:
        if messagebox.askyesno("Cerrar Sesión", "¿Estás seguro de que quieres cerrar la sesión?"):
            self.destroy()
            try:
                interprete = sys.executable
                
                if getattr(sys, 'frozen', False):
                    ruta_base_app = os.path.dirname(sys.executable)
                else:
                    ruta_base_app = BASE_DIR
                    
                ruta_login = os.path.join(ruta_base_app, "Login.py") 
                
                if not os.path.exists(ruta_login):
                     ruta_login = os.path.join(ruta_base_app, "login.py")
                
                if not os.path.exists(ruta_login):
                    messagebox.showerror("Error", "No se pudo encontrar 'Login.py' para reiniciar.")
                    return
                
                subprocess.Popen([interprete, ruta_login])
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo reiniciar la sesión.\nError: {e}")

    def on_salir(self) -> None:
        if messagebox.askyesno("Salir", "¿Estás seguro de que quieres salir de la aplicación?"):
            self.destroy()

    # -------------------------------------------------------------------
    # MÉTODOS DE DOBLE CLIC (REDIRECCIÓN)
    # -------------------------------------------------------------------
    def on_double_click_stock(self, event):
        """Lanza el módulo de Productos al hacer doble clic en la tabla de Stock."""
        self.abrir_productos()

    def on_double_click_pagos(self, event):
        """Lanza el módulo de Deudas al hacer doble clic en la tabla de Pagos Pendientes."""
        self.abrir_deudas()

    # -------------------------------------------------------------------
    # WIDGETS Y LÓGICA DEL HOME (Mantiene el mismo contenido visual)
    # -------------------------------------------------------------------

    def crear_widgets_home(self) -> None:
        # --- Frame de Resumen del Día (sin cambios) ---
        frame_resumen = ctk.CTkFrame(self.home_frame, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_resumen.grid(row=0, column=0, sticky="ew", pady=(0, 20), padx=0)
        frame_resumen.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_resumen, text=f"Resumen del Día ({datetime.now().strftime('%Y-%m-%d')})",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")

        # Ventas Totales
        ctk.CTkLabel(frame_resumen, text="Ventas Totales:", font=("Arial", 14), text_color=COLOR_TEXT_PRIMARY).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.label_ventas_totales = ctk.CTkLabel(frame_resumen, text="$ 0.00", font=("Arial", 14, "bold"), text_color=COLOR_SUCCESS)
        self.label_ventas_totales.grid(row=1, column=1, padx=20, pady=5, sticky="e")

        # Costo Mercancía
        ctk.CTkLabel(frame_resumen, text="Costo Mercancía:", font=("Arial", 14), text_color=COLOR_TEXT_PRIMARY).grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.label_costo_mercancia = ctk.CTkLabel(frame_resumen, text="$ 0.00", font=("Arial", 14, "bold"), text_color=COLOR_DANGER)
        self.label_costo_mercancia.grid(row=2, column=1, padx=20, pady=5, sticky="e")

        # Utilidad Bruta
        ctk.CTkLabel(frame_resumen, text="Utilidad Bruta:", font=("Arial", 14), text_color=COLOR_TEXT_PRIMARY).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.label_utilidad_bruta = ctk.CTkLabel(frame_resumen, text="$ 0.00", font=("Arial", 14, "bold"), text_color=COLOR_SUCCESS)
        self.label_utilidad_bruta.grid(row=3, column=1, padx=20, pady=5, sticky="e")
        
        # Nº Transacciones
        ctk.CTkLabel(frame_resumen, text="Nº Transacciones:", font=("Arial", 14), text_color=COLOR_TEXT_PRIMARY).grid(row=4, column=0, padx=20, pady=5, sticky="w")
        self.label_num_transacciones = ctk.CTkLabel(frame_resumen, text="0", font=("Arial", 14, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.label_num_transacciones.grid(row=4, column=1, padx=20, pady=5, sticky="e")

        # Botón Recargar Resumen
        btn_recargar_resumen = ctk.CTkButton(frame_resumen, 
                                             text="Recargar Resumen", 
                                             command=self.update_resumen_del_dia,
                                             fg_color=COLOR_ACCENT_BUTTON,
                                             hover_color=COLOR_ACCENT_HOVER,
                                             font=("Arial", 14, "bold"),
                                             height=35,
                                             corner_radius=10)
        btn_recargar_resumen.grid(row=5, column=0, columnspan=2, pady=20)


        # --- Frame Principal para las Alertas (Dividido en dos columnas) ---
        frame_alertas_container = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        frame_alertas_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 20))
        frame_alertas_container.grid_columnconfigure(0, weight=1)
        frame_alertas_container.grid_columnconfigure(1, weight=1)
        frame_alertas_container.grid_rowconfigure(0, weight=1) 

        # -------------------------------------------------------------------
        # 1. Alertas de Stock Bajo (Columna 0)
        # -------------------------------------------------------------------
        self.frame_stock_alertas = ctk.CTkFrame(frame_alertas_container, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        self.frame_stock_alertas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.frame_stock_alertas.grid_columnconfigure(0, weight=1)
        self.frame_stock_alertas.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.frame_stock_alertas, text="🚨 Alertas de Stock Mínimo",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Estilo del Treeview (Replicado de la lógica anterior)
        style = ttk.Style(self)
        style.theme_use("default")
        
        style.configure("Treeview",
                        background=COLOR_ENTRY_BG,
                        foreground=COLOR_TEXT_PRIMARY,
                        fieldbackground=COLOR_ENTRY_BG,
                        bordercolor=COLOR_ENTRY_BG,
                        borderwidth=0,
                        rowheight=25,
                        font=("Arial", 11))
        style.map('Treeview', background=[('selected', COLOR_ACCENT_BUTTON)])
        
        style.configure("Treeview.Heading",
                        font=("Arial", 11, "bold"),
                        background=COLOR_PRIMARY_NAV,
                        foreground=COLOR_TEXT_NAV,
                        relief="flat",
                        padding=(5, 5))
        style.map("Treeview.Heading", background=[('active', COLOR_PRIMARY_HOVER)])
        
        # --- SCROLLBAR STOCK ---
        tree_frame_stock = ctk.CTkFrame(self.frame_stock_alertas, fg_color="transparent")
        tree_frame_stock.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        tree_frame_stock.grid_rowconfigure(0, weight=1)
        tree_frame_stock.grid_columnconfigure(0, weight=1)

        self.tree_alertas_stock = ttk.Treeview(tree_frame_stock, columns=("producto", "actual", "umbral"), show="headings")
        self.tree_alertas_stock.heading("producto", text="PRODUCTO")
        self.tree_alertas_stock.heading("actual", text="STOCK (g)")
        self.tree_alertas_stock.heading("umbral", text="UMBRAL (g)")
        self.tree_alertas_stock.column("actual", anchor="e", width=100)
        self.tree_alertas_stock.column("umbral", anchor="e", width=100)
        self.tree_alertas_stock.column("producto", width=200, anchor="w")
        
        self.tree_alertas_stock.grid(row=0, column=0, sticky="nsew")

        scrollbar_stock = ctk.CTkScrollbar(tree_frame_stock, command=self.tree_alertas_stock.yview)
        scrollbar_stock.grid(row=0, column=1, sticky="ns")
        self.tree_alertas_stock.configure(yscrollcommand=scrollbar_stock.set)
        # --- FIN SCROLLBAR STOCK ---

        # -------------------------------------------------------------------
        # 2. Alertas de Pagos Pendientes (Columna 1)
        # -------------------------------------------------------------------
        self.frame_pagos_alertas = ctk.CTkFrame(frame_alertas_container, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        self.frame_pagos_alertas.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.frame_pagos_alertas.grid_columnconfigure(0, weight=1)
        self.frame_pagos_alertas.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.frame_pagos_alertas, text="💰 Cuentas por Cobrar Pendientes",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # --- SCROLLBAR PAGOS ---
        tree_frame_pagos = ctk.CTkFrame(self.frame_pagos_alertas, fg_color="transparent")
        tree_frame_pagos.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        tree_frame_pagos.grid_rowconfigure(0, weight=1)
        tree_frame_pagos.grid_columnconfigure(0, weight=1)

        self.tree_alertas_pagos = ttk.Treeview(tree_frame_pagos, columns=("id", "monto", "vendedor"), show="headings")
        self.tree_alertas_pagos.heading("id", text="ID Venta")
        self.tree_alertas_pagos.heading("monto", text="MONTO ($)")
        self.tree_alertas_pagos.heading("vendedor", text="DEUDA(S) PENDIENTE(S)")
        self.tree_alertas_pagos.column("id", anchor="center", width=80)
        self.tree_alertas_pagos.column("monto", anchor="e", width=120)
        self.tree_alertas_pagos.column("vendedor", anchor="w", width=200)

        self.tree_alertas_pagos.grid(row=0, column=0, sticky="nsew")

        scrollbar_pagos = ctk.CTkScrollbar(tree_frame_pagos, command=self.tree_alertas_pagos.yview)
        scrollbar_pagos.grid(row=0, column=1, sticky="ns")
        self.tree_alertas_pagos.configure(yscrollcommand=scrollbar_pagos.set)
        # --- FIN SCROLLBAR PAGOS ---
        
        # Botón Recargar Alertas (Unificado al final)
        btn_recargar_alertas = ctk.CTkButton(self.home_frame, 
                                            text="Recargar Alertas", 
                                            command=self.update_alertas_stock_bajo,
                                            fg_color=COLOR_ACCENT_BUTTON,
                                            hover_color=COLOR_ACCENT_HOVER,
                                            font=("Arial", 14, "bold"),
                                            height=35,
                                            corner_radius=10)
        btn_recargar_alertas.grid(row=2, column=0, pady=(0, 20)) 


    def update_resumen_del_dia(self) -> None:
        """Consulta y actualiza el resumen financiero del día."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        query_ventas = """
        SELECT SUM(V.montoTotal), COUNT(V.idVenta)
        FROM Venta V
        WHERE DATE(V.fechaHora) = %s
        """
        ventas_data = database.obtener_uno(query_ventas, (hoy,))
        ventas_totales = ventas_data[0] if (ventas_data and ventas_data[0] is not None) else 0.0
        num_transacciones = ventas_data[1] if (ventas_data and ventas_data[1] is not None) else 0

        query_costo = """
        SELECT SUM(DV.pesoVendido * P.costoPorGramo)
        FROM DetalleVenta DV
        JOIN Venta V ON DV.idVenta = V.idVenta
        JOIN Producto P ON DV.idProducto = P.idProducto
        WHERE DATE(V.fechaHora) = %s
        """
        costo_data = database.obtener_uno(query_costo, (hoy,))
        costo_mercancia = costo_data[0] if (costo_data and costo_data[0] is not None) else 0.0
        
        utilidad_bruta = ventas_totales - costo_mercancia

        self.label_ventas_totales.configure(text=f"$ {ventas_totales:,.2f}")
        self.label_costo_mercancia.configure(text=f"$ {costo_mercancia:,.2f}")
        self.label_utilidad_bruta.configure(text=f"$ {utilidad_bruta:,.2f}")
        
        if utilidad_bruta < 0:
            self.label_utilidad_bruta.configure(text_color=COLOR_DANGER)
        else:
            self.label_utilidad_bruta.configure(text_color=COLOR_SUCCESS)
            
        self.label_num_transacciones.configure(text=f"{num_transacciones}")


    def update_alertas_stock(self) -> None:
        """Actualiza la tabla de alertas de stock mínimo."""
        for item in self.tree_alertas_stock.get_children():
            self.tree_alertas_stock.delete(item)
            
        # Configurar tags de color (dentro de este método o globalmente)
        self.tree_alertas_stock.tag_configure('danger_stock', background='#FFEBEE', foreground=COLOR_DANGER)
        self.tree_alertas_stock.tag_configure('warning_stock', background='#FFF9E0', foreground=COLOR_WARNING)
        self.tree_alertas_stock.tag_configure('info_stock', foreground=COLOR_SUCCESS, font=("Arial", 11, "italic"))

        query_alertas = """
        SELECT nombre, stockEnGramos, umbralMinimoGramos 
        FROM Producto
        WHERE stockEnGramos <= umbralMinimoGramos
        ORDER BY nombre
        """
        alertas = database.obtener_todos(query_alertas)
        
        alertas_existentes = False

        for producto, stock_actual, umbral in alertas:
            alertas_existentes = True
            
            if stock_actual <= 0:
                tag = 'danger_stock'
            else:
                tag = 'warning_stock'
                
            self.tree_alertas_stock.insert("", "end", values=(
                producto, 
                f"{stock_actual:,.0f}", 
                f"{umbral:,.0f}"
            ), tags=(tag,))
            
        if not alertas_existentes: 
            self.tree_alertas_stock.insert("", "end", values=("¡Inventario en buen nivel!", "N/A", "N/A"), tags=('info_stock',))
            
        # ASIGNAR EL BINDING DE DOBLE CLIC
        self.tree_alertas_stock.bind("<Double-1>", self.on_double_click_stock)
            
    def update_alertas_pagos(self) -> None:
        """Actualiza la tabla de alertas de pagos pendientes."""
        for item in self.tree_alertas_pagos.get_children():
            self.tree_alertas_pagos.delete(item)
            
        # Configuramos los tags específicos para pagos
        self.tree_alertas_pagos.tag_configure('danger_pago', background='#FFEBEE', foreground=COLOR_DANGER)
        self.tree_alertas_pagos.tag_configure('info_pago', foreground=COLOR_SUCCESS, font=("Arial", 11, "italic"))

        # Consultamos las deudas pendientes
        sql_deudas = """
            SELECT 
                VP.idVenta, 
                VP.montoPendiente,
                U.nombre AS nombreVendedor
            FROM VentaPendiente AS VP
            JOIN Venta AS V ON VP.idVenta = V.idVenta
            JOIN Usuario AS U ON V.idUsuario = U.idUsuario
            WHERE VP.estadoDeuda = 'Pendiente'
            ORDER BY VP.fechaRegistro ASC
            LIMIT 5 -- Limitamos para no llenar la tabla de alertas
        """
        deudas = database.obtener_diccionarios(sql_deudas)
        
        if not deudas:
             self.tree_alertas_pagos.insert("", "end", values=("No hay pagos pendientes.", "N/A", "N/A"), tags=('info_pago',))
        else:
            for deuda in deudas:
                self.tree_alertas_pagos.insert("", "end", values=(
                    deuda['idVenta'], 
                    f"$ {deuda['montoPendiente']:,.2f}", 
                    deuda['nombreVendedor']
                ), tags=('danger_pago',))

        # ASIGNAR EL BINDING DE DOBLE CLIC
        self.tree_alertas_pagos.bind("<Double-1>", self.on_double_click_pagos)


    def update_alertas_stock_bajo(self) -> None:
        """Llama a los métodos de actualización de alertas de Stock y Pagos."""
        self.update_alertas_stock()
        self.update_alertas_pagos()


# --- Función de arranque ---
def start_main_app(id_usuario: int, rol_usuario: str, nombre_usuario: str) -> None:
    app = App(id_usuario_actual=id_usuario, 
              nombre_usuario_actual=nombre_usuario,
              rol_usuario_actual=rol_usuario)
    app.mainloop()

if __name__ == "__main__":
    # Esto es para pruebas directas del main.py
    try:
        user_id = int(sys.argv[1])
        user_role = sys.argv[2]
        user_name = sys.argv[3]
    except (IndexError, ValueError):
        # Valores por defecto para pruebas
        user_id = 1
        user_role = "Administrador" 
        user_name = "Admin (Prueba)"

    start_main_app(user_id, user_role, user_name)