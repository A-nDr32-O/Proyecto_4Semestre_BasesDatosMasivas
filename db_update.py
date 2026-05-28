# db_update.py

import sqlite3
import sys
from tkinter import messagebox

# Asegúrate de que 'database' y 'config' estén accesibles
try:
    import database
    from config import DB_PATH
except ImportError:
    messagebox.showerror("Error de Módulos", "Asegúrate de tener los archivos 'database.py' y 'config.py' en el mismo directorio.")
    sys.exit(1)

def actualizar_esquema_db():
    """
    Función principal para aplicar todos los cambios de esquema necesarios.
    Utiliza CREATE TABLE IF NOT EXISTS y ALTER TABLE IF NOT EXISTS.
    """
    
    print("--- Iniciando Actualización de Esquema de Base de Datos ---")
    print(f"Ruta de la DB: {DB_PATH}")

    # -----------------------------------------------------------
    # 1. Crear la tabla CierreCaja (Soluciona el error actual)
    # -----------------------------------------------------------
    sql_create_cierre_caja = """
    CREATE TABLE IF NOT EXISTS CierreCaja (
        idCierre INTEGER PRIMARY KEY AUTOINCREMENT,
        idUsuario INTEGER NOT NULL,
        fecha DATE NOT NULL UNIQUE,
        totalEsperado REAL NOT NULL,
        totalContado REAL NOT NULL,
        diferencia REAL NOT NULL,
        FOREIGN KEY (idUsuario) REFERENCES Usuario(idUsuario)
    );
    """
    print("-> Intentando crear tabla CierreCaja...")
    if database.ejecutar_consulta(sql_create_cierre_caja):
        print("   ✅ CierreCaja asegurada/creada.")
    else:
        print("   ❌ Error al crear CierreCaja. Revisa el mensaje de error.")
        return

    # -----------------------------------------------------------
    # 2. Asegurar campos de Deuda (idUsuarioCobro, fechaCobro)
    #    (Necesarios para registrar quién y cuándo cobró una deuda)
    # -----------------------------------------------------------
    
    # La adición de columnas requiere manejo específico en SQLite
    # Usaremos una conexión manual para un manejo de errores más específico en ALTER TABLE.
    
    columnas_pendientes = [
        ("VentaPendiente", "idUsuarioCobro", "INTEGER"),
        ("VentaPendiente", "fechaCobro", "DATETIME")
    ]

    for tabla, columna, tipo in columnas_pendientes:
        sql_check = f"SELECT {columna} FROM {tabla} LIMIT 1"
        try:
            # Intentar ejecutar un SELECT para ver si la columna ya existe
            database.obtener_uno(sql_check)
            print(f"-> Columna {tabla}.{columna} ya existe.")
        except sqlite3.OperationalError:
            # Si da un error, significa que la columna no existe y debe ser agregada
            sql_alter = f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"
            print(f"-> Añadiendo columna {tabla}.{columna}...")
            if database.ejecutar_consulta(sql_alter):
                print(f"   ✅ Columna {columna} añadida a {tabla}.")
            else:
                print(f"   ❌ Error al añadir columna {tabla}.{columna}.")
                # Podemos continuar, ya que el error de una columna no debería detener las demás
                pass 

    # -----------------------------------------------------------
    # 3. Asegurar la tabla TransaccionPago (Si no existe)
    #    (Clave para el nuevo flujo de pagos mixtos y cobros)
    # -----------------------------------------------------------
    sql_create_transaccion_pago = """
    CREATE TABLE IF NOT EXISTS TransaccionPago (
        idTransaccion INTEGER PRIMARY KEY AUTOINCREMENT,
        idVenta INTEGER NOT NULL,
        montoAbonado REAL NOT NULL,
        metodo TEXT NOT NULL, -- 'Efectivo', 'Transferencia', etc.
        fechaHora DATETIME NOT NULL,
        FOREIGN KEY (idVenta) REFERENCES Venta(idVenta) ON DELETE CASCADE
    );
    """
    print("-> Intentando crear tabla TransaccionPago...")
    if database.ejecutar_consulta(sql_create_transaccion_pago):
        print("   ✅ TransaccionPago asegurada/creada.")
    else:
        print("   ❌ Error al crear TransaccionPago. Revisa el mensaje de error.")


    print("\n--- Actualización de Esquema Finalizada ---")
    messagebox.showinfo("Actualización de DB", "La estructura de la base de datos ha sido actualizada.\nAhora puedes ejecutar 'gestion_cierre.py'.")


if __name__ == "__main__":
    actualizar_esquema_db()