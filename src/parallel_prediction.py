import concurrent.futures
import subprocess
import os
import time

def run_command(command):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            print(line, end='')  # Zeigt den Fortschritt in Echtzeit an
        process.wait()
        if process.returncode != 0:
            print(f"Error while executing command '{command}'. Error:\n{process.stderr.read()}")
    except Exception as e:
        print(f"An unexpected error occurred while executing command '{command}': {e}")

def show_progress(futures):
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        print(f"Progress: {done_count}/{total} completed, {running_count} running.", end='\r')
        if done_count == total:
            break
        time.sleep(1)

if __name__ == "__main__":
    # Pfad zum Input-Ordner mit den TIF-Bildern
    input_folder = "./input_folder"
    tif_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]

    # Liste der Befehle, die parallel ausgeführt werden sollen
    commands = [
        f"marinedebrisdetector --device='cuda' {os.path.join(input_folder, tif_file)}" for tif_file in tif_files
    ]

    # Nutze ThreadPoolExecutor mit max_workers=3, um nur 3 Befehle gleichzeitig auszuführen
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_command, cmd) for cmd in commands]
        
        # Starte eine parallele Task, um den Fortschritt anzuzeigen
        show_progress(futures)

    print("\nAll commands have been executed.")
