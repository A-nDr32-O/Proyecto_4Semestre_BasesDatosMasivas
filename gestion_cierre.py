import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import sys
from typing import Tuple, Optional, Any

# --- Importar Tema ---
from theme import *

# --- Importar Módulo de Base de Datos ---
import database # <-- AÑADIDO: Este módulo ahora maneja la conexión

# -------------------------------------------------------------------
# PARTE LÓGICA (Conexión con la Base de Datos)
# -------------------------------------------------------------------
FECHA_HOY = date.today().strftime("%Y-%m-%d")

try:
    ID_USUARIO_ACTUAL: int = int(sys.argv[1])
except (IndexError, ValueError):
    ID_USUARIO_ACTUAL: int = 1


def obtener_datos_cierre_hoy() -> Tuple[Any, bool, Optional[tuple]]:
    """
    Obtiene el resumen de ventas del día (desglosado por pagos) y verifica si ya se hizo un cierre hoy.
    --- MODIFICADO para usar TransaccionPago para el desglose de ingresos ---
    Devuelve: (resumen_ventas, cierre_existente, datos_cierre)
    """
    cierre_existente = None
    resumen_ventas = {
        'TotalEfectivo': 0.0,
        'TotalTarjeta': 0.0, 
        'TotalTransferencia': 0.0
    }
    
    # 1. Verificar si ya existe un cierre para HOY
    sql_cierre = "SELECT * FROM CierreCaja WHERE fecha = %s"
    cierre_existente = database.obtener_uno(sql_cierre, (FECHA_HOY,))

    # 2. Calcular el resumen total de pagos del día usando TransaccionPago
    sql_pagos_del_dia = """
        SELECT
            T.metodo,
            SUM(T.montoAbonado) AS MontoTotal
        FROM TransaccionPago AS T
        WHERE DATE(T.fechaHora) = %s
        GROUP BY T.metodo
        """
    res_pagos = database.obtener_diccionarios(sql_pagos_del_dia, (FECHA_HOY,))

    # Rellenamos el diccionario resumen_ventas con los montos reales cobrados
    for fila in res_pagos:
        metodo = fila['metodo']
        monto = fila['MontoTotal'] if fila['MontoTotal'] is not None else 0.0
        
        if metodo == 'Efectivo':
            resumen_ventas['TotalEfectivo'] = monto
        elif metodo == 'Transferencia':
            resumen_ventas['TotalTransferencia'] = monto
        elif metodo == 'Tarjeta':
            resumen_ventas['TotalTarjeta'] = monto

    # Devolvemos el diccionario de resumen y el estado del cierre
    return (resumen_ventas, cierre_existente is not None, cierre_existente)


def registrar_cierre_caja(id_usuario: int, fecha: str, esperado: float, contado: float, diferencia: float) -> bool:
    """
    Guarda el registro del cierre en la tabla CierreCaja.
    """
    sql = """
        INSERT INTO CierreCaja (idUsuario, fecha, totalEsperado, totalContado, diferencia)
        VALUES (%s, %s, %s, %s, %s)
        """
    return database.ejecutar_consulta(sql, (id_usuario, fecha, esperado, contado, diferencia))

# -------------------------------------------------------------------
# PARTE GRÁFICA (Ventana de CustomTkinter)
# -------------------------------------------------------------------

class VentanaCierre(ctk.CTk):
    """
    Clase que genera la ventana de Cierre de Caja (Arqueo) con CustomTkinter.
    """

    def __init__(self) -> None:
        """Inicializa la ventana y las variables de estado."""
        super().__init__()
        
        ctk.set_appearance_mode("Light")
        self.configure(fg_color=COLOR_BACKGROUND)

        self.title(f"Cierre de Caja (Arqueo) - Usuario: {ID_USUARIO_ACTUAL}")
        self.geometry("450x500")
        self.resizable(False, False)

        self.total_esperado_efectivo = 0.0 
        
        # --- Variables de CTk ---
        self.total_contado = ctk.DoubleVar(value=0.0)
        self.diferencia = ctk.StringVar(value="$ 0.00")
        self.label_transferencia_var = ctk.StringVar(value="$ 0.00")
        self.label_esperado_var = ctk.StringVar(value="$ 0.00")
        self.label_estado_var = ctk.StringVar(value="")

        # Configuración de validación para entrada de contado
        self.vcmd = (self.register(self.validate_numeric_input), '%S', '%P') # <-- Usa la función corregida

        self.crear_widgets()
        self.cargar_datos_iniciales()
        
        self.after(100, lambda: self.geometry(f"450x500+{int((self.winfo_screenwidth()/2) - (450/2))}+{int((self.winfo_screenheight()/2) - (500/2))}"))

    # Función de validación para entradas numéricas
    def validate_numeric_input(self, S, P):
        """Permite solo números y punto/coma decimal, y maneja el reemplazo de comas.
        --- FUNCIÓN CORREGIDA ---
        """
        if S == "" or S == "-1": return True
        
        # Permitir tanto '.' como ',' y luego reemplazamos solo para la validación
        new_value = P.replace(',', '.')
        
        # Permitir un solo punto decimal y que no termine solo en punto
        try:
            # Si el nuevo valor es solo un punto, es inválido
            if new_value == '.': return False 
            
            # Intenta convertir, permite que termine en punto (ej: "123.")
            if new_value.endswith('.'):
                float(new_value[:-1]) 
            else:
                float(new_value)
                
            return True
        except ValueError:
            return False

    def crear_widgets(self) -> None:
        """Crea y posiciona todos los widgets en la ventana."""
        frame = ctk.CTkFrame(self, fg_color=COLOR_WHITE_FRAME, corner_radius=20)
        frame.pack(expand=True, fill="both", padx=20, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Resumen de Ventas del Día", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, columnspan=2, pady=(15, 5))
        ctk.CTkLabel(frame, text=f"{FECHA_HOY}", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_PRIMARY_NAV).grid(row=1, column=0, columnspan=2, pady=(0, 15))

        # --- Desglose (Transferencia) ---
        font_label_desglose = ("Arial", 14)
        font_valor_desglose = ("Arial", 14, "bold")
        
        ctk.CTkLabel(frame, text="Ventas por Transferencia:", font=font_label_desglose).grid(row=2, column=0, sticky="w", padx=20, pady=4)
        self.label_transferencia = ctk.CTkLabel(frame, textvariable=self.label_transferencia_var, font=font_valor_desglose, text_color=COLOR_WARNING)
        self.label_transferencia.grid(row=2, column=1, sticky="e", padx=20)

        # --- Separador ---
        ctk.CTkFrame(frame, height=1, fg_color="#cccccc").grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=15)

        # --- Arqueo de Efectivo ---
        font_label_arqueo = ("Arial", 16)
        font_valor_arqueo = ("Arial", 16, "bold")

        ctk.CTkLabel(frame, text="Total Esperado (Efectivo):", font=font_label_arqueo).grid(row=4, column=0, sticky="w", padx=20, pady=10)
        self.label_esperado = ctk.CTkLabel(frame, textvariable=self.label_esperado_var, font=font_valor_arqueo, text_color=COLOR_INFO)
        self.label_esperado.grid(row=4, column=1, sticky="e", padx=20)

        ctk.CTkLabel(frame, text="Total Contado (Físico):", font=font_label_arqueo).grid(row=5, column=0, sticky="w", padx=20, pady=10)
        self.entry_contado = ctk.CTkEntry(
            frame, 
            textvariable=self.total_contado, 
            font=("Arial", 16), 
            width=150,
            justify="right",
            border_color=COLOR_ACCENT_BUTTON,
            validate="key", 
            validatecommand=self.vcmd
        )
        self.entry_contado.grid(row=5, column=1, sticky="e", padx=20)
        self.entry_contado.bind("<KeyRelease>", self.actualizar_diferencia)

        ctk.CTkLabel(frame, text="Diferencia (Efectivo):", font=font_label_arqueo).grid(row=6, column=0, sticky="w", padx=20, pady=10)
        self.label_diferencia = ctk.CTkLabel(frame, textvariable=self.diferencia, font=font_valor_arqueo, text_color=COLOR_TEXT_PRIMARY)
        self.label_diferencia.grid(row=6, column=1, sticky="e", padx=20)

        # --- Separador ---
        ctk.CTkFrame(frame, height=1, fg_color="#cccccc").grid(row=7, column=0, columnspan=2, sticky="ew", padx=20, pady=20)

        # --- Botón de Cierre ---
        self.boton_cerrar_caja = ctk.CTkButton(
            frame, 
            text="Realizar Cierre Definitivo", 
            command=self.on_realizar_cierre,
            fg_color=COLOR_SUCCESS, 
            hover_color=COLOR_ACCENT_HOVER, 
            font=("Arial", 14, "bold"), 
            height=40,
            corner_radius=10
        )
        self.boton_cerrar_caja.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20)

        self.label_estado = ctk.CTkLabel(frame, textvariable=self.label_estado_var, font=("Arial", 12, "italic"), text_color=COLOR_DANGER)
        self.label_estado.grid(row=9, column=0, columnspan=2, pady=(10, 0))

    def cargar_datos_iniciales(self) -> None:
        """Carga los datos del día y deshabilita campos si ya se cerró la caja."""
        # Se asegura de que la tabla exista antes de la consulta
        try:
             database.ejecutar_consulta("""
                 CREATE TABLE IF NOT EXISTS CierreCaja (
                    idCierre INTEGER PRIMARY KEY AUTO_INCREMENT,
                    idUsuario INTEGER NOT NULL,
                    fecha DATE NOT NULL UNIQUE,
                    totalEsperado REAL NOT NULL,
                    totalContado REAL NOT NULL,
                    diferencia REAL NOT NULL,
                    FOREIGN KEY (idUsuario) REFERENCES Usuario(idUsuario)
                 )
             """)
        except Exception:
             # Si falla la creación, el error será capturado por database.py
             pass 

        resumen, ya_cerrado, datos_cierre = obtener_datos_cierre_hoy()

        if resumen:
            efectivo = resumen.get('TotalEfectivo', 0.0)
            transferencia = resumen.get('TotalTransferencia', 0.0)
            
            self.label_transferencia_var.set(f"$ {transferencia:,.2f}")
            self.total_esperado_efectivo = efectivo
            self.label_esperado_var.set(f"$ {efectivo:,.2f}")
        else:
            self.total_esperado_efectivo = 0.0
            self.label_esperado_var.set("$ 0.00")
            self.label_transferencia_var.set("$ 0.00")

        if ya_cerrado:
            # datos_cierre es una tupla: (idCierre, idUsuario, fecha, totalEsperado, totalContado, diferencia)
            contado    = datos_cierre[4]
            diferencia = datos_cierre[5]
            id_usuario = datos_cierre[1]
            
            # Formatear contado para mostrar correctamente (reemplazando . por ,)
            self.entry_contado.delete(0, "end")
            self.entry_contado.insert(0, f"{contado:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','))

            self.entry_contado.configure(state="disabled")
            self.diferencia.set(f"$ {diferencia:,.2f}")
            self.actualizar_color_diferencia(diferencia)
            self.boton_cerrar_caja.configure(text="Cierre ya realizado", state="disabled")
            self.label_estado_var.set(f"Cierre registrado por usuario ID: {id_usuario}")
        else:
            self.actualizar_diferencia() # Calcular diferencia inicial

    def actualizar_diferencia(self, event: Optional[Any] = None) -> None:
        """Calcula la diferencia entre lo contado y lo esperado.
        --- FUNCIÓN CORREGIDA ---
        """
        try:
            # CAMBIO CLAVE: Reemplazar comas por puntos ANTES de float
            contado_str = self.entry_contado.get().replace(',', '.')
            contado = float(contado_str) if contado_str and contado_str != '.' else 0.0
        except Exception: 
            contado = 0.0
            
        diferencia_calc = contado - self.total_esperado_efectivo
        self.diferencia.set(f"$ {diferencia_calc:,.2f}")
        self.actualizar_color_diferencia(diferencia_calc)

    def actualizar_color_diferencia(self, diferencia_calc: float) -> None:
        """Cambia el color del texto de la diferencia (faltante, sobrante, exacto)."""
        if abs(diferencia_calc) < 0.01: # Usar una pequeña tolerancia para flotantes
            self.label_diferencia.configure(text_color=COLOR_SUCCESS)
        elif diferencia_calc > 0:
            self.label_diferencia.configure(text_color=COLOR_WARNING)
        else:
            self.label_diferencia.configure(text_color=COLOR_DANGER)

    def on_realizar_cierre(self) -> None:
        """Callback para el botón 'Realizar Cierre Definitivo'.
        --- FUNCIÓN CORREGIDA ---
        """
        try:
            # CAMBIO CLAVE: Reemplazar comas por puntos para el cálculo final
            contado_str = self.entry_contado.get().replace(',', '.')
            contado = float(contado_str) if contado_str and contado_str != '.' else 0.0
            
            if contado < 0:
                messagebox.showwarning("Valor inválido", "El monto contado no puede ser negativo.")
                return
        except Exception:
            messagebox.showwarning("Valor inválido", "Ingrese un monto numérico válido.")
            return
            
        esperado = self.total_esperado_efectivo
        diferencia_calc = contado - esperado
        
        msg_confirm = (
            f"Vas a cerrar la caja (solo efectivo):\n\n"
            f"Total Esperado (Efectivo): ${esperado:,.2f}\n"
            f"Total Contado (Físico):  ${contado:,.2f}\n"
            f"Diferencia:                   ${diferencia_calc:,.2f}\n\n"
            "¿Estás seguro? Esta acción es definitiva para el día de hoy."
        )
        
        if messagebox.askyesno("Confirmar Cierre de Caja", msg_confirm):
            if registrar_cierre_caja(ID_USUARIO_ACTUAL, FECHA_HOY, esperado, contado, diferencia_calc):
                messagebox.showinfo("Éxito", "Cierre de caja guardado correctamente.")
                self.entry_contado.configure(state="disabled")
                self.boton_cerrar_caja.configure(text="Cierre ya realizado", state="disabled")
                self.label_estado_var.set("Cierre registrado exitosamente.")
            else:
                # El error ya fue reportado por database.py
                pass 

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

    app = VentanaCierre()
    app.mainloop()