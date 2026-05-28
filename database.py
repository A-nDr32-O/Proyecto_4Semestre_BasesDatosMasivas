# database.py
import mysql.connector
from mysql.connector import Error as MySQLError
from tkinter import messagebox
from typing import Tuple, List, Any, Optional, Dict
from datetime import datetime

# --- Importar configuración de conexión desde config.py ---
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


# -------------------------------------------------------------------
# FUNCIÓN INTERNA: Crear conexión
# -------------------------------------------------------------------

def _obtener_conexion():
    """
    Crea y devuelve una conexión a la base de datos MySQL.
    Lanza una excepción si no puede conectar.
    """
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=False,
        use_pure=True  # <--- ¡ESTA ES LA LÍNEA CLAVE!
    )


def _normalizar_parametros_sql(sql: str) -> str:
    """Convierte placeholders de SQLite (?) a placeholders de MySQL (%s)."""
    return sql.replace("?", "%s")


def _mostrar_error_db(e: MySQLError, contexto: str = "") -> None:
    """Muestra un messagebox de error estandarizado."""
    contexto_str = f" en {contexto}" if contexto else ""

    # Código 1062 = Duplicate entry (equivalente a UNIQUE constraint de SQLite)
    if e.errno == 1062:
        messagebox.showerror(
            "Error de Duplicado",
            f"Error: Ya existe un registro con ese valor.{contexto_str}\n\nDetalle: {e.msg}"
        )
    else:
        messagebox.showerror(
            "Error de Base de Datos",
            f"Error al operar con la base de datos{contexto_str}.\n\nDetalle: {e.msg}\n"
            f"(BD: {DB_NAME} @ {DB_HOST})"
        )


# -------------------------------------------------------------------
# FUNCIONES GENÉRICAS CRUD
# -------------------------------------------------------------------

def ejecutar_consulta(sql: str, parametros: Tuple = ()) -> bool:
    """
    Ejecuta consultas de escritura (INSERT, UPDATE, DELETE).
    Devuelve True si tiene éxito, False si falla.
    """
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor()
        sql = _normalizar_parametros_sql(sql)
        cursor.execute(sql, parametros)
        con.commit()
        return True
    except MySQLError as e:
        if con:
            con.rollback()
        _mostrar_error_db(e, f"ejecutar_consulta ({sql[:40]}...)")
        return False
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


def obtener_todos(sql: str, parametros: Tuple = ()) -> List[Any]:
    """
    Ejecuta un SELECT y devuelve TODAS las filas como lista de tuplas.
    """
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor()
        sql = _normalizar_parametros_sql(sql)
        cursor.execute(sql, parametros)
        return cursor.fetchall()
    except MySQLError as e:
        _mostrar_error_db(e, f"obtener_todos ({sql[:40]}...)")
        return []
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


def obtener_uno(sql: str, parametros: Tuple = ()) -> Optional[Any]:
    """
    Ejecuta un SELECT y devuelve UNA sola fila (fetchone).
    """
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor()
        sql = _normalizar_parametros_sql(sql)
        cursor.execute(sql, parametros)
        return cursor.fetchone()
    except MySQLError as e:
        _mostrar_error_db(e, f"obtener_uno ({sql[:40]}...)")
        return None
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


def obtener_diccionarios(sql: str, parametros: Tuple = ()) -> List[Dict[str, Any]]:
    """
    Ejecuta un SELECT y devuelve TODAS las filas como lista de diccionarios.
    """
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor(dictionary=True)  # mysql-connector devuelve dicts directamente
        sql = _normalizar_parametros_sql(sql)
        cursor.execute(sql, parametros)
        resultado = cursor.fetchall()
        return resultado if resultado else []
    except MySQLError as e:
        _mostrar_error_db(e, f"obtener_diccionarios ({sql[:40]}...)")
        return []
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


# -------------------------------------------------------------------
# FUNCIONES ESPECÍFICAS DE NEGOCIO
# -------------------------------------------------------------------

def contar_pagos_pendientes() -> int:
    """Cuenta el número de VentaPendiente con estadoDeuda = 'Pendiente'."""
    sql = "SELECT COUNT(idVenta) FROM VentaPendiente WHERE estadoDeuda = 'Pendiente'"
    resultado = obtener_uno(sql)
    return resultado[0] if resultado else 0


def obtener_deudas_pendientes_db() -> List[Dict[str, Any]]:
    """
    Obtiene todas las ventas en VentaPendiente con estado 'Pendiente',
    con JOIN a Venta y Usuario.
    """
    sql = """
        SELECT
            VP.idVenta,
            VP.fechaRegistro,
            VP.montoPendiente,
            V.fechaHora  AS fechaVenta,
            U.nombre     AS nombreVendedor
        FROM VentaPendiente AS VP
        JOIN Venta    AS V ON VP.idVenta  = V.idVenta
        JOIN Usuario  AS U ON V.idUsuario = U.idUsuario
        WHERE VP.estadoDeuda = 'Pendiente'
        ORDER BY VP.fechaRegistro ASC
    """
    return obtener_diccionarios(sql)


def obtener_productos_con_stock() -> List[Dict[str, Any]]:
    """
    Obtiene todos los productos (incluso sin stock) para dropdowns de mermas/ajustes.
    """
    sql = "SELECT idProducto, nombre, stockEnGramos FROM Producto ORDER BY nombre ASC"
    return obtener_diccionarios(sql)

def registrar_merma_db(id_usuario: int, id_producto: int, cantidad_gramos: float, motivo: str) -> bool:
    from datetime import datetime
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor()

        cursor.execute(
            "UPDATE Producto SET stockEnGramos = stockEnGramos - %s WHERE idProducto = %s",
            (cantidad_gramos, id_producto)
        )
        cursor.execute(
            "INSERT INTO Merma (idProducto, idUsuario, fechaHora, cantidadGramos, motivo) VALUES (%s, %s, %s, %s, %s)",
            (id_producto, id_usuario, fecha_actual, cantidad_gramos, motivo)
        )

        con.commit()
        messagebox.showinfo("Éxito", "La merma ha sido registrada y el stock actualizado.")
        return True

    except MySQLError as e:
        if con:
            con.rollback()
        messagebox.showerror("Error en Transacción", f"No se pudo registrar la merma.\nDetalle: {e.msg}")
        return False
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

def registrar_abono_db(id_venta: int, id_usuario_cobro: int, metodo_cobro: str, monto_abonado: float, monto_pendiente_final: float) -> bool:
    """
    Registra un abono sobre una VentaPendiente en una transacción atómica:
    - Inserta en TransaccionPago
    - Actualiza montoPendiente / estadoDeuda en VentaPendiente
    - Si queda en 0, actualiza metodoPago en Venta a 'Crédito Liquidado'
    Devuelve True si tiene éxito, False si falla (con rollback).
    """
    from datetime import datetime
    fecha_cobro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor()

        # 1. Registrar el abono en TransaccionPago
        cursor.execute(
            "INSERT INTO TransaccionPago (idVenta, montoAbonado, metodo, fechaHora) VALUES (%s, %s, %s, %s)",
            (id_venta, monto_abonado, metodo_cobro, fecha_cobro)
        )

        # 2. Actualizar VentaPendiente
        if monto_pendiente_final <= 0.01:
            cursor.execute(
                "UPDATE VentaPendiente SET estadoDeuda = 'Pagada', montoPendiente = 0.00, idUsuarioCobro = %s, fechaCobro = %s WHERE idVenta = %s",
                (id_usuario_cobro, fecha_cobro, id_venta)
            )
            # 3. Marcar la Venta como liquidada
            cursor.execute(
                "UPDATE Venta SET metodoPago = 'Crédito Liquidado' WHERE idVenta = %s",
                (id_venta,)
            )
            estado = 'Pagada'
        else:
            cursor.execute(
                "UPDATE VentaPendiente SET montoPendiente = %s WHERE idVenta = %s",
                (monto_pendiente_final, id_venta)
            )
            estado = 'Pendiente'

        con.commit()

        if estado == 'Pagada':
            messagebox.showinfo("Éxito", f"Venta #{id_venta} LIQUIDADA con abono de ${monto_abonado:,.2f} ({metodo_cobro}).")
        else:
            messagebox.showinfo("Éxito", f"Abono de ${monto_abonado:,.2f} registrado. Pendiente restante: ${monto_pendiente_final:,.2f}")

        return True

    except MySQLError as e:
        if con:
            con.rollback()
        messagebox.showerror("Error de Abono", f"No se pudo registrar el abono.\nDetalle: {e.msg}")
        return False
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


def finalizar_venta_db(
    id_usuario: int,
    metodo_pago_final: str,
    carro_compras_agrupado: List[Dict[str, Any]],
    monto_total: float,
    pagos_registrados: List[Dict[str, Any]]
) -> bool:
    """
    Registra la venta completa en una única transacción atómica:
    - Inserta en Venta
    - Inserta DetalleVenta y descuenta stock de Producto
    - Inserta TransaccionPago por cada abono
    - Inserta en VentaPendiente si el método es 'Pendiente'
    Devuelve True si tiene éxito, False si falla (con rollback).
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = None
    cursor = None
    try:
        con = _obtener_conexion()
        cursor = con.cursor()

        # 1. Registrar la Venta
        cursor.execute(
            "INSERT INTO Venta (idUsuario, fechaHora, montoTotal, metodoPago) VALUES (%s, %s, %s, %s)",
            (id_usuario, fecha_actual, monto_total, metodo_pago_final)
        )
        id_venta_generado = cursor.lastrowid

        # 2. DetalleVenta + descuento de stock
        for item in carro_compras_agrupado:
            cursor.execute(
                "INSERT INTO DetalleVenta (idVenta, idProducto, pesoVendido, subtotal) VALUES (%s, %s, %s, %s)",
                (id_venta_generado, item['id'], item['peso'], item['subtotal'])
            )
            cursor.execute(
                "UPDATE Producto SET stockEnGramos = stockEnGramos - %s WHERE idProducto = %s",
                (item['peso'], item['id'])
            )

        # 3. TransaccionesPago
        for pago in pagos_registrados:
            cursor.execute(
                "INSERT INTO TransaccionPago (idVenta, montoAbonado, metodo, fechaHora) VALUES (%s, %s, %s, %s)",
                (id_venta_generado, pago['monto'], pago['metodo'], fecha_actual)
            )

        # 4. VentaPendiente si aplica
        if metodo_pago_final == "Pendiente":
            monto_abonado = sum(p['monto'] for p in pagos_registrados)
            monto_pendiente_restante = monto_total - monto_abonado
            if monto_pendiente_restante > 0.01:
                cursor.execute(
                    "INSERT INTO VentaPendiente (idVenta, fechaRegistro, montoPendiente, estadoDeuda) VALUES (%s, %s, %s, 'Pendiente')",
                    (id_venta_generado, fecha_actual, monto_pendiente_restante)
                )

        con.commit()
        return True

    except MySQLError as e:
        if con:
            con.rollback()
        messagebox.showerror(
            "Error de Transacción",
            f"No se pudo completar la venta. Se revirtieron los cambios.\nDetalle: {e.msg}"
        )
        return False
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


def obtener_detalle_venta_para_reporte(fecha_inicio: str, fecha_fin: str) -> List[Dict[str, Any]]:
    """
    Obtiene el detalle de productos vendidos para un reporte,
    agrupado por producto, fecha e ID Venta.
    """
    sql = """
        SELECT
            P.nombre,
            SUM(DV.pesoVendido)                    AS TotalPeso,
            SUM(DV.subtotal)                        AS TotalSubtotal,
            SUM(DV.pesoVendido * P.costoPorGramo)   AS TotalCostoProducto,
            DATE(V.fechaHora)                       AS FechaVenta,
            V.idVenta                               AS IDVenta
        FROM DetalleVenta AS DV
        JOIN Producto AS P ON DV.idProducto = P.idProducto
        JOIN Venta    AS V ON DV.idVenta    = V.idVenta
        WHERE DATE(V.fechaHora) BETWEEN %s AND %s
        GROUP BY P.nombre, DATE(V.fechaHora), V.idVenta
        ORDER BY FechaVenta ASC, TotalSubtotal DESC
    """
    return obtener_diccionarios(sql, (fecha_inicio, fecha_fin))