import os
from datetime import datetime

output_doc = "DOKUMENTASI_KODE_LENGKAP.txt"
target_extensions = ['.py', '.html', '.css', '.js']
ignored_folders = ['venv', '.git', '__pycache__', 'instance', '.vscode']

with open(output_doc, 'w', encoding='utf-8') as outfile:
    outfile.write(f"DOKUMENTASI KODE PROGRAM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    outfile.write("="*60 + "\n\n")

    for root, dirs, files in os.walk("."):
        # Abaikan folder yang tidak perlu
        dirs[:] = [d for d in dirs if d not in ignored_folders]

        for file in files:
            # Jangan masukkan file script ini sendiri ke dalam hasil
            if file == "gabung_kode.py": continue

            if any(file.endswith(ext) for ext in target_extensions):
                file_path = os.path.join(root, file)
                outfile.write(f"\n\n{'#'*60}\n")
                outfile.write(f" FILE: {file_path}\n")
                outfile.write(f"{'#'*60}\n\n")

                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"<< Error membaca file: {str(e)} >>")

print(f"Sukses! Semua isi file sudah digabung ke: {output_doc}")