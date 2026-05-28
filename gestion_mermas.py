import customtkinter as ctk
from tkinter import messagebox, ttk 
from datetime import datetime
import sys
from typing import List, Dict, Any, Optional

# --- Importar Tema ---
from theme import * # --- Importar Módulo de Base de Datos ---
import database # <-- AÑADIDO: Para las consultas simples

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
# ...
# (BLOQUE ELIMINADO - Ahora en theme.py)
# ...
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión con la Base de Datos)
# -------------------------------------------------------------------
try:
    ID_USUARIO_ACTUAL: int = int(sys.argv[1])
except (IndexError, ValueError):
    ID_USUARIO_ACTUAL: int = 1


def obtener_productos_todos() -> List[Dict[str, Any]]: # <-- REFACTORIZADO
    """
    Obtiene TODOS los productos (incluso sin stock) para el dropdown.
    --- REFACTORIZADO para usar database.py ---
    """
    sql = "SELECT idProducto, nombre, stockEnGramos FROM Producto ORDER BY nombre ASC"
    
    # LLamamos a la nueva función centralizada para obtener la lista de diccionarios
    return database.obtener_diccionarios(sql) # <-- CAMBIO AQUÍ


def registrar_merma(id_usuario: int, id_producto: int, cantidad_gramos: float, motivo: str) -> bool:
    """
    Delega el registro de la merma a database.py,
    que maneja la transacción atómica de forma centralizada.
    """
    return database.registrar_merma_db(id_usuario, id_producto, cantidad_gramos, motivo)

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# (Esta sección no necesita cambios)
# -------------------------------------------------------------------

class VentanaMermas(ctk.CTk):
    """
    Clase que genera la ventana de Registro de Mermas (Pérdidas).
    """

    def __init__(self) -> None:
        """Inicializa la ventana y las variables de estado."""
        super().__init__()

        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)

        self.title(f"Registro de Mermas - Usuario: {ID_USUARIO_ACTUAL}")
        self.geometry("500x500")
        self.minsize(480, 480)

        # Configurar layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.factores_conversion = {
            "Gramos (g)": 1.0,
            "Kilos (kg)": 1000.0,
            "Libras (lb)": 453.592,
            "Toneladas (t)": 1000000.0
        }

        self.todos_los_nombres_productos: List[str] = []
        self.productos_disponibles: Dict[str, Any] = {}
        
        # Variables de CTk
        self.label_info_stock_var = ctk.StringVar(value="Stock actual: 0 g")

        self.crear_widgets()
        self.cargar_productos()

    def crear_widgets(self) -> None:
        """Crea y posiciona todos los widgets en la ventana."""
        frame = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Registrar Pérdida de Inventario", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        # --- Producto ---
        ctk.CTkLabel(frame, text="Producto:", font=("Arial", 14)).grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        self.combo_productos = ctk.CTkComboBox(
            frame, 
            width=250, 
            height=35, 
            font=("Arial", 14),
            dropdown_font=("Arial", 12),
            border_color=COLOR_ACCENT_BUTTON,
            button_color=COLOR_ACCENT_BUTTON,
            button_hover_color=COLOR_ACCENT_HOVER
        )
        self.combo_productos.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.combo_productos.bind("<<ComboboxSelected>>", self.actualizar_info_producto)
        self.combo_productos.bind("<KeyRelease>", self.on_producto_keyrelease)
        self.combo_productos.bind("<FocusOut>", self.on_producto_focus_out)

        # --- Info Stock ---
        self.label_info_stock = ctk.CTkLabel(frame, textvariable=self.label_info_stock_var, font=("Arial", 12, "italic"), text_color="#555")
        self.label_info_stock.grid(row=2, column=1, columnspan=2, pady=(0, 10), padx=(0, 20), sticky="w")

        # --- Cantidad Perdida ---
        ctk.CTkLabel(frame, text="Cantidad Perdida:", font=("Arial", 14)).grid(row=3, column=0, padx=(20, 10), pady=10, sticky="w")
        self.entry_cantidad = ctk.CTkEntry(
            frame, 
            width=150, 
            height=35, 
            font=("Arial", 14), 
            border_color=COLOR_ACCENT_BUTTON
        )
        self.entry_cantidad.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="w")

        # --- Unidad ---
        ctk.CTkLabel(frame, text="Unidad:", font=("Arial", 14)).grid(row=4, column=0, padx=(20, 10), pady=10, sticky="w")
        unidades = list(self.factores_conversion.keys())
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
        self.combo_unidades.grid(row=4, column=1, padx=(0, 20), pady=10, sticky="w")
        self.combo_unidades.set(unidades[0])

        # --- Motivo ---
        ctk.CTkLabel(frame, text="Motivo:", font=("Arial", 14)).grid(row=5, column=0, padx=(20, 10), pady=10, sticky="nw")
        self.entry_motivo = ctk.CTkTextbox(
            frame, 
            font=("Arial", 14), 
            height=80,
            border_color=COLOR_ACCENT_BUTTON,
            border_width=2,
            fg_color=COLOR_ENTRY_BG
        )
        self.entry_motivo.grid(row=5, column=1, padx=(0, 20), pady=10, sticky="ew")

        # --- Botón Registrar ---
        self.boton_registrar = ctk.CTkButton(
            frame, 
            text="Registrar Merma", 
            command=self.on_registrar_merma, 
            fg_color=COLOR_DANGER,
            hover_color="#c0392b", # Rojo oscuro
            font=("Arial", 14, "bold"), 
            height=40,
            corner_radius=10
        )
        self.boton_registrar.grid(row=6, column=0, columnspan=2, pady=(20, 20), padx=20, sticky="ew")

    def cargar_productos(self) -> None:
        """Limpia y recarga el dropdown de productos desde la BD."""
        self.productos_disponibles.clear()
        self.todos_los_nombres_productos.clear() 

        productos = obtener_productos_todos() # <- Usa la función refactorizada
        
        self.todos_los_nombres_productos = [p['nombre'] for p in productos]

        for p in productos:
            self.productos_disponibles[p['nombre']] = p

        self.combo_productos.configure(values=self.todos_los_nombres_productos)
        
        if self.todos_los_nombres_productos:
            self.combo_productos.set(self.todos_los_nombres_productos[0])
            self.actualizar_info_producto(None)

    def actualizar_info_producto(self, event: Optional[Any]) -> None:
        """Muestra stock del producto."""
        nombre_sel = self.combo_productos.get()
        
        if nombre_sel in self.productos_disponibles:
            p = self.productos_disponibles[nombre_sel]
            info = f"Stock actual: {p['stockEnGramos']:,.0f} g"
            self.label_info_stock_var.set(info)
            self.label_info_stock.configure(text_color="#555")
        elif not nombre_sel:
            self.label_info_stock_var.set("Stock actual: 0 g")
            self.label_info_stock.configure(text_color="#555")
        else:
            self.label_info_stock_var.set("Producto no encontrado...")
            self.label_info_stock.configure(text_color=COLOR_DANGER)

    def on_registrar_merma(self) -> None:
        """Callback para 'Registrar Merma'."""
        nombre_sel = self.combo_productos.get()

        # 1. Validación de Producto
        if not nombre_sel or nombre_sel not in self.productos_disponibles:
            messagebox.showwarning("Producto Inválido",
                                  f"El producto '{nombre_sel}' no es válido o no está en la lista.")
            return

        producto_obj = self.productos_disponibles[nombre_sel]
        id_producto = producto_obj['idProducto']
        stock_actual = producto_obj['stockEnGramos']
        
        # 2. Validación de Cantidad y Tipo
        try:
            cantidad_ingresada = float(self.entry_cantidad.get())
            if cantidad_ingresada <= 0:
                messagebox.showwarning("Cantidad Inválida", "La cantidad debe ser mayor a cero.")
                return
        except ValueError:
            messagebox.showwarning("Cantidad Inválida", "Ingrese una cantidad numérica válida.")
            return
            
        unidad_seleccionada = self.combo_unidades.get()
        if not unidad_seleccionada or unidad_seleccionada not in self.factores_conversion:
             messagebox.showwarning("Unidad Inválida", "Seleccione una unidad de medida válida.")
             return
            
        factor_conversion = self.factores_conversion[unidad_seleccionada]
        cantidad_en_gramos = cantidad_ingresada * factor_conversion
        
        # 3. Validación de Stock
        if cantidad_en_gramos > stock_actual:
            msg = (
                f"No se puede registrar una merma mayor al stock.\n\n"
                f"Stock: {stock_actual:,.2f} g\n"
                f"Merma: {cantidad_ingresada} {unidad_seleccionada} ({cantidad_en_gramos:,.2f} g)"
            )
            messagebox.showerror("Stock Insuficiente", msg)
            return

        # 4. Validación de Motivo
        motivo = self.entry_motivo.get("1.0", "end-1c").strip()
        if not motivo:
            messagebox.showwarning("Motivo Requerido", "Debe ingresar un motivo (ej: 'Dañado').")
            return

        msg_confirm = (
            f"¿Está seguro de registrar esta merma?\n\n"
            f"Producto: {nombre_sel}\n"
            f"Cantidad a restar: {cantidad_ingresada} {unidad_seleccionada} ({cantidad_en_gramos:,.2f} g)\n"
            f"Motivo: {motivo}\n\n"
            "Esta acción es irreversible y afectará el inventario."
        )

        if messagebox.askyesno("Confirmar Merma", msg_confirm):
            # --- FUNCIÓN NO REFACTORIZADA (Usa la lógica original) ---
            if registrar_merma(ID_USUARIO_ACTUAL, id_producto, cantidad_en_gramos, motivo):
                self.entry_cantidad.delete(0, "end")
                self.entry_motivo.delete("1.0", "end")
                self.combo_unidades.set(list(self.factores_conversion.keys())[0])
                self.cargar_productos() # Recarga productos para actualizar el stock visible

    def on_producto_keyrelease(self, event: Any) -> None:
        """Filtra el combobox de productos."""
        if event.keysym in ("Up", "Down", "Left", "Right", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Tab", "Return"):
            return

        valor_escrito = self.combo_productos.get().lower()

        if not valor_escrito:
            self.combo_productos.configure(values=self.todos_los_nombres_productos)
            self.actualizar_info_producto(None)
        else:
            nombres_filtrados = [
                nombre for nombre in self.todos_los_nombres_productos
                if valor_escrito in nombre.lower()
            ]
            self.combo_productos.configure(values=nombres_filtrados)
            
            if self.combo_productos.get() in self.productos_disponibles:
                 self.actualizar_info_producto(None)

    def on_producto_focus_out(self, event: Optional[Any]) -> None:
        """Actualiza la info del producto al perder el foco."""
        self.after(100, lambda: self.actualizar_info_producto(None))

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
         
    app = VentanaMermas()
    app.mainloop()