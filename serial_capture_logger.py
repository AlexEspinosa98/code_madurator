import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import serial

from serial_parser import SerialDataParser
from storage import DataStorage


def now_cot_text():
    return datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S")


def open_serial_port(port, baudrate, timeout):
    while True:
        try:
            serial_port = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            print(f"[{now_cot_text()}] Puerto serial abierto: {port} @ {baudrate}")
            return serial_port
        except serial.SerialException as exc:
            print(f"[{now_cot_text()}] Error abriendo puerto {port}: {exc}. Reintentando en 2s...")
            time.sleep(2)


def run_capture(port, baudrate, timeout, db_path, log_dir):
    parser = SerialDataParser()
    storage = DataStorage(db_path=db_path, log_dir=log_dir)
    serial_port = open_serial_port(port, baudrate, timeout)

    print(f"[{now_cot_text()}] Iniciando captura continua. Presiona Ctrl+C para detener.")

    while True:
        try:
            raw_line = serial_port.readline().decode("utf-8", errors="ignore").strip()
            if not raw_line:
                continue

            storage.save_raw_serial_line(raw_line)
            parsed_frames = parser.feed(raw_line)

            if not parsed_frames:
                print(f"[{now_cot_text()}] RAW sin trama completa: {raw_line}")
                continue

            for frame in parsed_frames:
                storage.save_reading(frame)
                print(
                    f"[{now_cot_text()}] Guardado {frame.get('esp')} "
                    f"TMP={frame.get('TMP')} HUM={frame.get('HUM')} "
                    f"PRS={frame.get('PRS')} ET={frame.get('ET')} O3={frame.get('O3')}"
                )

        except KeyboardInterrupt:
            print(f"\n[{now_cot_text()}] Captura detenida por usuario.")
            break
        except serial.SerialException as exc:
            print(f"[{now_cot_text()}] Error serial: {exc}. Reconectando...")
            try:
                serial_port.close()
            except Exception:
                pass
            serial_port = open_serial_port(port, baudrate, timeout)
        except Exception as exc:
            print(f"[{now_cot_text()}] Error general: {exc}")
            time.sleep(1)

    try:
        serial_port.close()
    except Exception:
        pass


def main():
    arg_parser = argparse.ArgumentParser(
        description="Captura datos de /dev/serial0, guarda en SQLite y en logs TXT con hora de Colombia."
    )
    arg_parser.add_argument("--port", default="/dev/serial0", help="Puerto serial, por ejemplo /dev/serial0")
    arg_parser.add_argument("--baudrate", type=int, default=115200, help="Baudrate del puerto serial")
    arg_parser.add_argument("--timeout", type=float, default=1.0, help="Timeout de lectura serial en segundos")
    arg_parser.add_argument("--db", default="counters.db", help="Ruta de la base SQLite")
    arg_parser.add_argument("--log-dir", default="serial_logs", help="Directorio para logs txt")
    args = arg_parser.parse_args()

    run_capture(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        db_path=args.db,
        log_dir=args.log_dir,
    )


if __name__ == "__main__":
    main()
