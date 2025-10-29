import os
import subprocess
import json
import glob
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from InquirerPy import inquirer

console = Console()


# =====================
# UTILITAS CLI
# =====================

def run_command(command, description):
    console.print(Panel.fit(f"[bold cyan]Menjalankan {description}[/bold cyan]", border_style="cyan"))
    with Progress() as progress:
        task = progress.add_task(f"[green]Eksekusi {description}...", total=None)
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        progress.remove_task(task)

    if result.returncode == 0:
        console.print("[bold green]✓ Selesai[/bold green]\n")
    else:
        console.print(f"[bold red]✗ Gagal: {result.stderr}[/bold red]\n")
    return result


# =====================
# FILE & FOLDER PICKER
# =====================

def file_explorer(start_path=".", file_types=None, title="Pilih file"):
    """Single file picker"""
    current_path = os.path.abspath(start_path)
    while True:
        try:
            entries = os.listdir(current_path)
        except FileNotFoundError:
            console.print(f"[red]Folder tidak ditemukan: {current_path}[/red]")
            current_path = os.path.dirname(current_path)
            continue

        dirs = [d for d in entries if os.path.isdir(os.path.join(current_path, d))]
        files = [f for f in entries if os.path.isfile(os.path.join(current_path, f))]

        if file_types:
            files = [f for f in files if any(f.endswith(ext) for ext in file_types)]

        choices = ["[..] Kembali ke atas"] + [f"[📁] {d}" for d in dirs] + [f"[📄] {f}" for f in files]
        choice = inquirer.select(message=f"{title}\n{current_path}", choices=choices).execute()

        if choice.startswith("[..]"):
            current_path = os.path.dirname(current_path)
        elif choice.startswith("[📁] "):  # diperbaiki agar tidak salah potong
            folder_name = choice.replace("[📁] ", "")
            current_path = os.path.join(current_path, folder_name)
        else:
            file_name = choice.replace("[📄] ", "")
            return os.path.join(current_path, file_name)


def file_explorer_multi(start_path=".", file_types=None, title="Pilih beberapa file"):
    """Multi file picker dengan pemilihan folder terlebih dahulu"""
    # Biarkan pengguna pilih folder dulu
    base_folder = folder_explorer(start_path=start_path, title=f"{title} - Pilih folder asal file")
    if not base_folder:
        console.print("[red]Tidak ada folder yang dipilih[/red]")
        return []

    # Ambil semua file dari folder tersebut dan subfoldernya
    all_files = []
    for root, dirs, files in os.walk(base_folder):
        for f in files:
            if not file_types or any(f.endswith(ext) for ext in file_types):
                all_files.append(os.path.join(root, f))

    if not all_files:
        console.print(f"[yellow]⚠ Tidak ditemukan file yang sesuai di {base_folder}[/yellow]")
        return []

    # Biarkan user pilih satu atau lebih file
    selected_files = inquirer.fuzzy(
        message=title,
        choices=all_files,
        multiselect=True,
        transformer=lambda result: f"{len(result)} file dipilih"
    ).execute()

    return selected_files



def folder_explorer(start_path=".", title="Pilih folder"):
    """Folder picker"""
    current_path = os.path.abspath(start_path)
    while True:
        try:
            entries = os.listdir(current_path)
        except FileNotFoundError:
            console.print(f"[red]Folder tidak ditemukan: {current_path}[/red]")
            current_path = os.path.dirname(current_path)
            continue

        dirs = [d for d in entries if os.path.isdir(os.path.join(current_path, d))]

        choices = ["[..] Kembali ke atas", "[✔️] Gunakan folder ini"] + [f"[📁] {d}" for d in dirs]
        choice = inquirer.select(message=f"{title}\n{current_path}", choices=choices).execute()

        if choice.startswith("[..]"):
            current_path = os.path.dirname(current_path)
        elif choice.startswith("[📁] "):
            folder_name = choice.replace("[📁] ", "")
            current_path = os.path.join(current_path, folder_name)
        elif choice.startswith("[✔️]"):
            return current_path


# =====================
# PARSER & SOLVER LOGIC
# =====================

def collect_route_files(route_dir):
    route_files = glob.glob(os.path.join(route_dir, "**", "routes.py"), recursive=True)
    if not route_files:
        console.print("[yellow]⚠ Tidak ditemukan file routes.py pada direktori yang diberikan[/yellow]")
    else:
        console.print(f"[cyan]Ditemukan {len(route_files)} file routes.py[/cyan]")
    return route_files


def run_main_parser(output_dir):
    compose_path = file_explorer(file_types=[".yml", ".yaml"], title="Pilih file docker-compose.yml")
    openapi_paths = file_explorer_multi(file_types=[".yaml", ".yml", ".json"], title="Pilih satu atau lebih file OpenAPI/Swagger")

    system_spec_path = os.path.join(output_dir, "system_spec.json")

    openapi_args = " ".join([f'--openapi "{p}"' for p in openapi_paths])
    cmd = f'python main_parser.py --compose "{compose_path}" {openapi_args} --output "{system_spec_path}"'

    run_command(cmd, "Main Parser (System Spec)")
    return system_spec_path


def run_routes_parser(output_dir):
    routes_dir = folder_explorer(title="Pilih folder routes (berisi routes.py)")
    route_files = collect_route_files(routes_dir)
    if not route_files:
        return None

    routes_output_path = os.path.join(output_dir, "routes.json")
    route_files_str = " ".join(f'"{rf}"' for rf in route_files)
    cmd = f'python routes_parser.py --files {route_files_str} --output "{routes_output_path}"'
    run_command(cmd, "Routes Parser")
    return routes_output_path


def run_main_solver(output_dir, system_spec_path, routes_output_path):
    solver_output_path = os.path.join(output_dir, "verification_result.json")
    cmd = f'python main_solver.py --specs "{system_spec_path}" --routes "{routes_output_path}" --output "{solver_output_path}"'
    run_command(cmd, "Main Solver (Z3 Verification)")
    return solver_output_path


def show_result_summary(result_path):
    if not os.path.exists(result_path):
        console.print("[red]File hasil solver tidak ditemukan.[/red]")
        return

    with open(result_path, "r") as f:
        result = json.load(f)

    table = Table(title="Ringkasan Hasil Verifikasi", show_lines=True)
    table.add_column("Aspek", justify="left", style="cyan")
    table.add_column("Nilai", justify="center", style="magenta")
    table.add_row("Satisfiable", str(result.get("is_satisfiable", "Unknown")))
    table.add_row("Errors", str(len(result.get("errors", []))))
    table.add_row("Warnings", str(len(result.get("warnings", []))))
    table.add_row("Suggestions", str(len(result.get("suggestions", []))))
    console.print(table)


# =====================
# MAIN MENU
# =====================

def main_menu():
    console.print(Panel("[bold magenta]HelioVerify CLI[/bold magenta]\nPilih operasi yang ingin dijalankan",
                        border_style="magenta"))
    choices = [
        "1. Jalankan semua (Parser + Routes + Solver)",
        "2. Jalankan Parser saja",
        "3. Jalankan Routes Parser saja",
        "4. Jalankan Solver saja",
        "5. Keluar"
    ]
    choice = inquirer.select(message="Pilih menu:", choices=choices).execute()
    return choice


def main():
    console.print(Panel("[bold magenta]HelioVerify CLI - Interactive Menu[/bold magenta]", border_style="magenta"))

    output_dir = folder_explorer(title="Pilih folder output hasil verifikasi")
    os.makedirs(output_dir, exist_ok=True)

    while True:
        choice = main_menu()

        if choice.startswith("1"):
            system_spec = run_main_parser(output_dir)
            routes_json = run_routes_parser(output_dir)
            if routes_json:
                solver_result = run_main_solver(output_dir, system_spec, routes_json)
                show_result_summary(solver_result)

        elif choice.startswith("2"):
            run_main_parser(output_dir)

        elif choice.startswith("3"):
            run_routes_parser(output_dir)

        elif choice.startswith("4"):
            system_spec = file_explorer(file_types=[".json"], title="Pilih file system_spec.json")
            routes_json = file_explorer(file_types=[".json"], title="Pilih file routes.json")
            solver_result = run_main_solver(output_dir, system_spec, routes_json)
            show_result_summary(solver_result)

        elif choice.startswith("5"):
            console.print("[bold green]Keluar dari HelioVerify CLI[/bold green]")
            break


if __name__ == "__main__":
    main()
