import psycopg2
from psycopg2 import extras
import time
from threading import Thread
from queue import Queue, Empty
from datetime import datetime, date
import re

class PostgresLogger:
    def __init__(self, db_config, batch_size=50, flush_interval=1.0, retention_months=3):
        self.db_config = db_config
        self.queue = Queue(maxsize=2000)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.retention_months = retention_months
        
        self.checked_partitions = set() 
        self.stopped = False

        try:
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            print("[INFO] DB: Conexión PostgreSQL Exitosa.")
        except Exception as e:
            print(f"[ERROR CRÍTICO] No se pudo conectar a la DB: {e}")
            raise e

        Thread(target=self.cleanup_old_data, daemon=True).start()
        self.thread = Thread(target=self.loop, daemon=True)
        self.thread.start()

    def log(self, tracker_id, class_name, speed, direction):
        if not self.stopped:
            now = datetime.now()
            
            try:
                tracker_id_native = int(tracker_id)
                speed_native = int(speed)
                class_name_native = str(class_name)
                direction_native = str(direction)
            except:
                tracker_id_native = -1
                speed_native = 0
                class_name_native = "Unknown"
                direction_native = "Unknown"

            data = (
                now,            
                now.date(),     
                now.time(),     
                tracker_id_native, 
                class_name_native,
                speed_native,      
                direction_native
            )
            try:
                self.queue.put_nowait(data)
            except:
                pass 

    def ensure_partition(self, cursor, date_obj):
        year = date_obj.year
        month = date_obj.month
        
        if (year, month) in self.checked_partitions:
            return

        table_name = f"traffic_logs_y{year}m{month:02d}"
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} 
            PARTITION OF traffic_logs
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """
        
        try:
            cursor.execute(query)
            self.checked_partitions.add((year, month))
        except Exception as e:
            print(f"[ERROR DB] Fallo creando partición {table_name}: {e}")

    def cleanup_old_data(self):
        print("[MANTENIMIENTO] Verificando retención de datos...")
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = True
            cursor = conn.cursor()
            
            today = date.today()
            cutoff_year = today.year
            cutoff_month = today.month - self.retention_months
            
            while cutoff_month <= 0:
                cutoff_month += 12
                cutoff_year -= 1
            
            print(f"[MANTENIMIENTO] Borrando datos anteriores a: {cutoff_year}-{cutoff_month:02d}")

            cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename LIKE 'traffic_logs_y%'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                match = re.search(r"y(\d{4})m(\d{2})", table_name)
                if match:
                    t_year = int(match.group(1))
                    t_month = int(match.group(2))
                    
                    is_old = False
                    if t_year < cutoff_year: is_old = True
                    elif t_year == cutoff_year and t_month < cutoff_month: is_old = True
                    
                    if is_old:
                        print(f"[LIMPIEZA] Eliminando tabla: {table_name}")
                        cursor.execute(f"DROP TABLE {table_name}")
            
            conn.close()
        except Exception as e:
            print(f"[ERROR MANTENIMIENTO] {e}")

    def loop(self):
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = True
            cursor = conn.cursor()
        except:
            return

        buffer = []
        last_flush = time.time()

        while True:
            if self.stopped and self.queue.empty() and not buffer:
                break

            try:
                item = self.queue.get(timeout=0.1)
                buffer.append(item)
                self.queue.task_done()
            except Empty:
                pass

            current_time = time.time()
            is_full = len(buffer) >= self.batch_size
            is_timeout = (current_time - last_flush) >= self.flush_interval

            if buffer and (is_full or is_timeout):
                try:
                    first_record_date = buffer[0][1]
                    self.ensure_partition(cursor, first_record_date)
                    
                    query = """
                        INSERT INTO traffic_logs 
                        (record_timestamp, record_date, record_time, tracker_id, vehicle_class, speed_kmh, direction)
                        VALUES %s
                    """
                    extras.execute_values(cursor, query, buffer)
                    
                    buffer = []
                    last_flush = current_time
                    
                except Exception as e:
                    print(f"[ERROR SQL] {e}")
                    try:
                        conn.close()
                        conn = psycopg2.connect(**self.db_config)
                        conn.autocommit = True
                        cursor = conn.cursor()
                        self.checked_partitions.clear()
                    except:
                        pass

        if conn: conn.close()
        print("[INFO] PostgresLogger finalizado.")

    def stop(self):
        self.stopped = True
        self.thread.join()