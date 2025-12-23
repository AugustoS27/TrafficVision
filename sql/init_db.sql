-- ---------------------------------------------------------
-- Script de Inicialización de Base de Datos - TrafficVision
-- ---------------------------------------------------------

-- 1. (Opcional) Borrar la tabla si ya existe para empezar de cero
DROP TABLE IF EXISTS traffic_logs CASCADE;

-- 2. Crear la tabla MAESTRA particionada

CREATE TABLE traffic_logs (
    record_timestamp TIMESTAMP WITHOUT TIME ZONE, -- Fecha y hora exacta (para ordenar)
    record_date DATE NOT NULL,                    -- La llave para el particionamiento
    record_time TIME WITHOUT TIME ZONE,           -- Hora sola (para filtrar picos de tráfico)
    tracker_id INTEGER,                           -- ID del vehículo (del Tracker ByteTrack)
    vehicle_class VARCHAR(50),                    -- Auto, Camión, Moto, etc.
    speed_kmh INTEGER,                            -- Velocidad calculada
    direction VARCHAR(50)                         -- Incoming / Outgoing
) PARTITION BY RANGE (record_date);

-- 3. Índices (Opcional pero recomendado para rendimiento en Power BI)
-- Se crean sobre la columna de tiempo para acelerar los gráficos de líneas.
CREATE INDEX ON traffic_logs (record_timestamp);

-- NOTA: No es necesario crear las particiones aquí (ej: traffic_logs_y2025m12).
-- El script 'postgres_logger.py' detectará el mes actual y creará la partición automáticamente.