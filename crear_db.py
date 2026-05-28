import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

def inicializar_base_datos():
    """Crea las tablas en MySQL para la aplicación."""
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        cursor = conexion.cursor()
        
        # Lista de tablas con sintaxis adaptada para MySQL
        tablas = [
            """
            CREATE TABLE IF NOT EXISTS Usuario (
                idUsuario INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                usuario VARCHAR(255) NOT NULL UNIQUE,
                contrasena VARCHAR(255) NOT NULL,
                rol VARCHAR(100) NOT NULL 
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Producto (
                idProducto INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL UNIQUE,
                precioPorGramo DOUBLE NOT NULL,
                costoPorGramo DOUBLE NOT NULL,
                stockEnGramos DOUBLE NOT NULL DEFAULT 0.0,
                umbralMinimoGramos DOUBLE NOT NULL DEFAULT 0.0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Compra (
                idCompra INT AUTO_INCREMENT PRIMARY KEY,
                nombreProveedor VARCHAR(255) NOT NULL,
                fecha DATETIME NOT NULL,
                costoTotal DOUBLE NOT NULL,
                estado VARCHAR(100) NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Venta (
                idVenta INT AUTO_INCREMENT PRIMARY KEY,
                idUsuario INT NOT NULL,
                fechaHora DATETIME NOT NULL,
                montoTotal DOUBLE NOT NULL,
                metodoPago VARCHAR(100) NOT NULL,
                FOREIGN KEY (idUsuario) REFERENCES Usuario(idUsuario)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS DetalleVenta (
                idVenta INT NOT NULL,
                idProducto INT NOT NULL,
                pesoVendido DOUBLE NOT NULL,
                subtotal DOUBLE NOT NULL,
                FOREIGN KEY (idVenta) REFERENCES Venta(idVenta) ON DELETE CASCADE,
                FOREIGN KEY (idProducto) REFERENCES Producto(idProducto) ON DELETE RESTRICT,
                PRIMARY KEY (idVenta, idProducto)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS TransaccionPago (
                idTransaccion INT AUTO_INCREMENT PRIMARY KEY,
                idVenta INT NOT NULL,
                montoAbonado DOUBLE NOT NULL,
                metodo VARCHAR(100) NOT NULL, 
                fechaHora DATETIME NOT NULL,
                FOREIGN KEY (idVenta) REFERENCES Venta(idVenta) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS DetalleCompra (
                idCompra INT NOT NULL,
                idProducto INT NOT NULL,
                cantidadCompradaGramos DOUBLE NOT NULL,
                costoUnitarioGramo DOUBLE NOT NULL,
                subtotal DOUBLE NOT NULL,
                unidadOriginal VARCHAR(50) DEFAULT 'Gramos', 
                FOREIGN KEY (idCompra) REFERENCES Compra(idCompra) ON DELETE CASCADE,
                FOREIGN KEY (idProducto) REFERENCES Producto(idProducto) ON DELETE RESTRICT,
                PRIMARY KEY (idCompra, idProducto)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS VentaPendiente (
                idVenta INT PRIMARY KEY,
                fechaRegistro DATETIME NOT NULL,
                montoPendiente DOUBLE NOT NULL,
                estadoDeuda VARCHAR(100) NOT NULL, 
                idUsuarioCobro INT,
                fechaCobro DATETIME,
                FOREIGN KEY (idVenta) REFERENCES Venta(idVenta) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Merma (
                idMerma INT AUTO_INCREMENT PRIMARY KEY,
                idProducto INT NOT NULL,
                idUsuario INT NOT NULL,
                fechaHora DATETIME NOT NULL,
                cantidadGramos DOUBLE NOT NULL,
                motivo VARCHAR(255),
                FOREIGN KEY (idProducto) REFERENCES Producto(idProducto) ON DELETE RESTRICT,
                FOREIGN KEY (idUsuario) REFERENCES Usuario(idUsuario)
            );
            """,
        ]
        
        for sql in tablas:
            cursor.execute(sql)
            
        conexion.commit()
        print("¡Base de datos creada exitosamente en MySQL!")
        
    except Error as e:
        print(f"Error al crear la BD: {e}")
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()

if __name__ == "__main__":
    inicializar_base_datos()