import concurrent.futures
import subprocess
import os

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"Command '{command}' executed successfully. Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error while executing command '{command}'. Error:\n{e.stderr}")

if __name__ == "__main__":
    # Pfad zum Input-Ordner mit den TIF-Bildern
    input_folder = "./input_folder"
    tif_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]

    # Liste der Befehle, die parallel ausgeführt werden sollen
    commands = [
        f"marinederbisdetector --device="cuda" --input {os.path.join(input_folder, tif_file)}" for tif_file in tif_files
    ]

    # Nutze ThreadPoolExecutor, um die Befehle parallel auszuführen
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_command, cmd) for cmd in commands]
        concurrent.futures.wait(futures)

    print("All commands have been executed.")
