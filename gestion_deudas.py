import sqlite3
import customtkinter as ctk
from tkinter import messagebox, ttk 
from typing import Tuple, List, Any, Optional, Dict
import sys
from datetime import datetime

# --- Importar Tema y Módulo de Base de Datos ---
from theme import *
from theme import aplicar_estilo_treeview
import database 

# -------------------------------------------------------------------
# LÓGICA DE NEGOCIO (Acceso a BD)
# -------------------------------------------------------------------
try:
    ID_USUARIO_ACTUAL: int = int(sys.argv[1])
except (IndexError, ValueError):
    ID_USUARIO_ACTUAL: int = 1

def obtener_deudas_pendientes() -> List[Dict[str, Any]]:
    """
    Obtiene todas las ventas registradas en VentaPendiente con estado 'Pendiente'.
    JOIN con Venta y Usuario para obtener el nombre del vendedor.
    """
    sql = """
        SELECT 
            VP.idVenta, 
            VP.fechaRegistro, 
            VP.montoPendiente,
            V.fechaHora AS fechaVenta,
            U.nombre AS nombreVendedor
        FROM VentaPendiente AS VP
        JOIN Venta AS V ON VP.idVenta = V.idVenta
        JOIN Usuario AS U ON V.idUsuario = U.idUsuario
        WHERE VP.estadoDeuda = 'Pendiente'
        ORDER BY VP.fechaRegistro ASC
    """
    # Usamos obtener_diccionarios para obtener resultados por nombre de columna
    return database.obtener_diccionarios(sql)


def registrar_abono(id_venta: int, id_usuario_cobro: int, metodo_cobro: str, monto_abonado: float, monto_pendiente_final: float) -> bool:
    """
    Registra el abono en TransaccionPago, y actualiza el monto pendiente en VentaPendiente.
    --- FUNCIÓN MODIFICADA PARA ABONOS ---
    """
    conexion = None
    try:
        from config import DB_PATH 
        conexion = sqlite3.connect(DB_PATH)
        cursor = conexion.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        fecha_cobro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Registrar el Abono/Cobro en TransaccionPago (IMPORTANTE para el cierre de caja)
        sql_transaccion = """
            INSERT INTO TransaccionPago (idVenta, montoAbonado, metodo, fechaHora)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql_transaccion, (id_venta, monto_abonado, metodo_cobro, fecha_cobro))

        # 2. Actualizar el monto pendiente y el estado en VentaPendiente
        
        if monto_pendiente_final <= 0.01: # Si queda 0 o menos, marcar como pagada
            estado = 'Pagada'
            sql_update_deuda = """
                UPDATE VentaPendiente 
                SET estadoDeuda = ?, montoPendiente = 0.00, idUsuarioCobro = ?, fechaCobro = ? 
                WHERE idVenta = ?
            """
            cursor.execute(sql_update_deuda, (estado, id_usuario_cobro, fecha_cobro, id_venta))
            
            # 3. Si se liquida, actualizar el método de pago en Venta
            sql_update_venta = "UPDATE Venta SET metodoPago = 'Crédito Liquidado' WHERE idVenta = ?"
            cursor.execute(sql_update_venta, (id_venta,))
            
        else:
            estado = 'Pendiente'
            sql_update_deuda = """
                UPDATE VentaPendiente 
                SET montoPendiente = ?
                WHERE idVenta = ?
            """
            cursor.execute(sql_update_deuda, (monto_pendiente_final, id_venta))


        conexion.commit()
        
        if estado == 'Pagada':
             messagebox.showinfo("Éxito", f"Venta #{id_venta} LIQUIDADA con abono de ${monto_abonado:,.2f} ({metodo_cobro}).")
        else:
             messagebox.showinfo("Éxito", f"Abono de ${monto_abonado:,.2f} registrado. Pendiente restante: ${monto_pendiente_final:,.2f}")
             
        return True

    except sqlite3.Error as e:
        if conexion:
            conexion.rollback()
        messagebox.showerror("Error de Abono", f"No se pudo registrar el abono. Error: {e}")
        return False
    finally:
        if conexion:
            conexion.close()


# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# -------------------------------------------------------------------

class VentanaGestionDeudas(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)
        
        self.title(f"Módulo de Cuentas por Cobrar - Usuario: {ID_USUARIO_ACTUAL}")
        self.geometry("850x550")
        self.minsize(800, 500)

        # Configurar layout principal
        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=1)           # Columna Tabla

        # Estilo del Treeview
        aplicar_estilo_treeview(self)

        # Crear Widgets
        self.crear_widgets_tabla()

        # Carga Inicial
        self.refrescar_tabla_deudas()

    def crear_widgets_tabla(self):
        """Crea el panel (tabla y botones de gestión)."""
        frame_tabla = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame_tabla.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        frame_tabla.grid_columnconfigure(0, weight=1)
        frame_tabla.grid_rowconfigure(1, weight=1) 

        ctk.CTkLabel(frame_tabla, text="Ventas Pendientes de Pago", 
                     font=ctk.CTkFont(size=18, weight="bold"), 
                     text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # Frame para Treeview y Scrollbar
        tree_frame = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columnas = ("id_venta", "fecha_venta", "monto", "vendedor", "dias_pend")
        self.tabla_deudas = ttk.Treeview(tree_frame, columns=columnas, show="headings", style="Custom.Treeview")
        
        self.tabla_deudas.heading("id_venta", text="ID Venta")
        self.tabla_deudas.heading("fecha_venta", text="Fecha Venta")
        self.tabla_deudas.heading("monto", text="Monto Pendiente ($)")
        self.tabla_deudas.heading("vendedor", text="Registrado por")
        self.tabla_deudas.heading("dias_pend", text="Días Pendientes")
        
        self.tabla_deudas.column("id_venta", width=60, anchor="center")
        self.tabla_deudas.column("fecha_venta", width=100, anchor="center")
        self.tabla_deudas.column("monto", width=120, anchor="e")
        self.tabla_deudas.column("vendedor", width=150, anchor="w")
        self.tabla_deudas.column("dias_pend", width=80, anchor="center")
        
        self.tabla_deudas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tabla_deudas.yview)
        self.tabla_deudas.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Frame de Botones de Acción
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        btn_style = {"font": ("Arial", 14, "bold"), "height": 40, "corner_radius": 10}

        # --- BOTÓN DE ABONO ---
        self.btn_abono = ctk.CTkButton(frame_botones, 
                                        text="Registrar Abono", 
                                        command=self.on_registrar_abono, 
                                        fg_color=COLOR_SUCCESS, 
                                        hover_color=COLOR_ACCENT_HOVER, 
                                        **btn_style)
        self.btn_abono.pack(side="left", padx=5)
        
        self.btn_refrescar = ctk.CTkButton(frame_botones, 
                                           text="Refrescar", 
                                           command=self.refrescar_tabla_deudas, 
                                           fg_color=COLOR_LOGOUT_BTN, 
                                           hover_color=COLOR_LOGOUT_HOVER, 
                                           **btn_style)
        self.btn_refrescar.pack(side="right", padx=5)


    def poblar_tabla(self, deudas: List[Dict[str, Any]]) -> None:
        """Limpia la tabla y la llena con la lista de deudas."""
        for item in self.tabla_deudas.get_children():
            self.tabla_deudas.delete(item)
            
        fecha_hoy = datetime.now().date()

        for deuda in deudas:
            id_venta = deuda['idVenta']
            monto = deuda['montoPendiente']
            vendedor = deuda['nombreVendedor']
            
            # Calcular días pendientes
            # MySQL devuelve datetime.datetime, no string — usamos .date() directamente
            fecha_venta_raw = deuda['fechaVenta']
            try:
                if hasattr(fecha_venta_raw, 'date'):
                    fecha_venta = fecha_venta_raw.date()
                else:
                    fecha_venta = datetime.strptime(str(fecha_venta_raw).split()[0], "%Y-%m-%d").date()
                fecha_venta_str = str(fecha_venta)
                dias_pendientes = (fecha_hoy - fecha_venta).days
            except (ValueError, AttributeError):
                fecha_venta_str = str(fecha_venta_raw)
                dias_pendientes = "N/A"

            # Formatear datos
            monto_str = f"$ {monto:,.2f}"
            
            # Tags para resaltar deudas más antiguas
            if dias_pendientes == "N/A":
                 tag = 'normal'
            elif dias_pendientes >= 30:
                tag = 'danger' # Más de 30 días
            elif dias_pendientes >= 7:
                tag = 'warning' # Más de 7 días
            else:
                tag = 'normal'
                
            self.tabla_deudas.insert("", "end", values=(
                id_venta, 
                fecha_venta_str, 
                monto_str, 
                vendedor, 
                dias_pendientes
            ), tags=(tag,))
            
        # Configurar tags de color (basado en theme.py)
        self.tabla_deudas.tag_configure('danger', background='#FADBD8', foreground=COLOR_DANGER, font=('Arial', 11, 'bold')) # Rojo claro
        self.tabla_deudas.tag_configure('warning', background='#FCF3CF', foreground=COLOR_WARNING) # Naranja claro
        self.tabla_deudas.tag_configure('normal', foreground=COLOR_TEXT_PRIMARY)


    def refrescar_tabla_deudas(self) -> None:
        """Actualiza la lista maestra y repuebla la tabla."""
        deudas = obtener_deudas_pendientes()
        if not deudas:
            messagebox.showinfo("Información", "No hay ventas pendientes de pago.")
        self.poblar_tabla(deudas)


    def on_registrar_abono(self) -> None:
        """Callback para 'Registrar Abono', lanza una ventana modal para pagos parciales."""
        try:
            seleccion = self.tabla_deudas.focus()
            if not seleccion:
                messagebox.showwarning("Sin selección", "Por favor, selecciona una venta pendiente de la lista.")
                return
                
            # Obtener ID Venta y Monto Pendiente
            id_venta = self.tabla_deudas.item(seleccion)["values"][0]
            # Convertir el monto a float limpiando el formato
            monto_str = str(self.tabla_deudas.item(seleccion)["values"][2]).replace('$', '').replace(',', '')
            monto_pendiente = float(monto_str)
            
        except IndexError:
             messagebox.showwarning("Error de Selección", "Selecciona una fila válida de la lista para proceder.")
             return
        except ValueError:
             messagebox.showwarning("Error de Datos", "El monto pendiente no es un valor numérico válido.")
             return
             
        # Lanzar la ventana modal para registrar el abono
        VentanaRegistroAbono(self, id_venta, monto_pendiente, self.refrescar_tabla_deudas)


# -------------------------------------------------------------------
# CLASE Toplevel (VentanaRegistroAbono)
# -------------------------------------------------------------------
class VentanaRegistroAbono(ctk.CTkToplevel):
    def __init__(self, master, id_venta: int, monto_pendiente: float, callback_exito: callable):
        super().__init__(master)
        self.master = master
        self.id_venta = id_venta
        self.monto_pendiente = monto_pendiente
        self.callback_exito = callback_exito
        
        self.title(f"Registrar Abono Venta #{id_venta}")
        self.geometry("450x350")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BACKGROUND)
        
        # Centrar la ventana
        self.after(100, lambda: self.geometry(f"450x350+{int((self.winfo_screenwidth()/2) - (450/2))}+{int((self.winfo_screenheight()/2) - (350/2))}"))

        self.monto_abonado_var = ctk.DoubleVar(value=0.0)
        self.monto_pendiente_final_str_var = ctk.StringVar(value=f"$ {monto_pendiente:,.2f}")
        self.metodo_cobro_var = ctk.StringVar(value="Efectivo")
        
        self.vcmd = (master.register(self.validate_numeric_input), '%P')
        
        self.crear_widgets_abono()
        
        self.grab_set()
        self.transient(master)
        self.wait_window()
        
    def validate_numeric_input(self, P):
        """Permite solo números y punto/coma decimal."""
        if P == "": return True
        
        # Permitir tanto '.' como ','
        new_value = P.replace(',', '.')
        
        try:
            # Comprobación estricta de float
            if new_value.endswith('.') and len(new_value) > 1:
                float(new_value[:-1]) 
            elif new_value == '.':
                 return False
            else:
                float(new_value)
            return True
        except ValueError:
            return False

        
    def crear_widgets_abono(self):
        frame = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=f"Registro de Abono para Venta #{self.id_venta}", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(15, 10), padx=20)
        
        # Monto Pendiente Inicial
        ctk.CTkLabel(frame, text="Monto Pendiente Actual:", font=("Arial", 14)).grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        ctk.CTkLabel(frame, text=f"${self.monto_pendiente:,.2f}", font=("Arial", 14, "bold"), text_color=COLOR_DANGER).grid(row=1, column=1, padx=(0, 20), pady=10, sticky="e")

        # Monto Abonado
        ctk.CTkLabel(frame, text="Monto a Abonar:", font=("Arial", 14)).grid(row=2, column=0, padx=(20, 10), pady=10, sticky="w")
        self.entry_monto = ctk.CTkEntry(frame, textvariable=self.monto_abonado_var, width=150, height=35, font=("Arial", 14), justify="right", border_color=COLOR_ACCENT_BUTTON, validate="key", validatecommand=self.vcmd)
        self.entry_monto.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.entry_monto.bind("<KeyRelease>", self.actualizar_pendiente_final)

        # Método de Cobro
        ctk.CTkLabel(frame, text="Método de Cobro:", font=("Arial", 14)).grid(row=3, column=0, padx=(20, 10), pady=10, sticky="w")
        self.combo_metodo = ctk.CTkComboBox(frame, values=["Efectivo", "Transferencia"], variable=self.metodo_cobro_var, state="readonly", width=150, height=35, font=("Arial", 14), border_color=COLOR_ACCENT_BUTTON, button_color=COLOR_ACCENT_BUTTON)
        self.combo_metodo.grid(row=3, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Monto Pendiente Final
        ctk.CTkLabel(frame, text="Pendiente Después:", font=("Arial", 14)).grid(row=4, column=0, padx=(20, 10), pady=10, sticky="w")
        self.label_pendiente_final = ctk.CTkLabel(frame, textvariable=self.monto_pendiente_final_str_var, font=("Arial", 14, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.label_pendiente_final.grid(row=4, column=1, padx=(0, 20), pady=10, sticky="e")
        
        # Botón Confirmar
        btn_confirmar = ctk.CTkButton(frame, text="Confirmar Abono", command=self.on_confirmar_abono, fg_color=COLOR_SUCCESS, hover_color=COLOR_ACCENT_HOVER, font=("Arial", 14, "bold"), height=40)
        btn_confirmar.grid(row=5, column=0, columnspan=2, pady=(20, 15), padx=20, sticky="ew")

    def actualizar_pendiente_final(self, event=None):
        """Calcula el monto pendiente restante en la interfaz."""
        try:
            monto_abonado = float(self.entry_monto.get().replace(',', '.'))
        except (ValueError, AttributeError):
            monto_abonado = 0.0
            
        pendiente_final = max(0.0, self.monto_pendiente - monto_abonado)
        
        if pendiente_final <= 0.01:
            self.monto_pendiente_final_str_var.set("¡LIQUIDADO!")
            self.label_pendiente_final.configure(text_color=COLOR_SUCCESS)
        else:
            self.monto_pendiente_final_str_var.set(f"$ {pendiente_final:,.2f}")
            self.label_pendiente_final.configure(text_color=COLOR_TEXT_PRIMARY)


    def on_confirmar_abono(self):
        try:
            monto_abonado = float(self.entry_monto.get().replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Monto Inválido", "Ingrese una cantidad numérica válida para el abono.", parent=self)
            return
            
        metodo_cobro = self.metodo_cobro_var.get()
        
        if monto_abonado <= 0:
             messagebox.showwarning("Monto Inválido", "El monto a abonar debe ser mayor a cero.", parent=self)
             return
        
        if monto_abonado > self.monto_pendiente + 0.01:
             messagebox.showwarning("Monto Excedido", f"El abono (${monto_abonado:,.2f}) no puede ser mayor que el pendiente (${self.monto_pendiente:,.2f}).", parent=self)
             return
             
        monto_pendiente_final = self.monto_pendiente - monto_abonado
        
        if registrar_abono(self.id_venta, ID_USUARIO_ACTUAL, metodo_cobro, monto_abonado, monto_pendiente_final):
            self.callback_exito()
            self.destroy()


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

    app = VentanaGestionDeudas()
    app.mainloop()