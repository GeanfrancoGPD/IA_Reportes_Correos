import os
import requests

API_URL = "http://127.0.0.1:8000"
TEST_FILE = "factura_prueba.jpg"  # puedes cambiarlo por fact.pdf


def run_demo():
    print("=== DEMO: Proceso Completo de Factura ===\n")

    print("1) Subiendo factura de prueba...")

    # --- NUEVO: Verificar que el archivo existe ---
    if not os.path.exists(TEST_FILE):
        print(f"❌ ERROR: No se encontró el archivo '{TEST_FILE}'.")
        print("Colócalo en la misma carpeta o cambia TEST_FILE en este script.")
        return

    try:
        with open(TEST_FILE, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{API_URL}/invoice", files=files)

        print("Respuesta del servidor:")
        print(response.status_code, response.text)

    except Exception as e:
        print("❌ Ocurrió un error al intentar subir la factura:", e)
        return

    print("\n=== DEMO FINALIZADO ===")


if __name__ == "__main__":
    run_demo()
