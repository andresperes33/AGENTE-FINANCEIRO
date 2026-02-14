import os

def check_and_convert_to_utf8(file_path):
    print(f"Checking {file_path}")
    try:
        # Tentar ler como UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print("File is already UTF-8 valid")
    except UnicodeDecodeError:
        print("File is NOT UTF-8 valid. Converting from latin-1...")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Converted successfully")
        except Exception as e:
            print(f"Error converting: {e}")

base_dir = r"c:\Users\andre\OneDrive\Área de Trabalho\AGENTE FINANCEIRO\templates"
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".html"):
            check_and_convert_to_utf8(os.path.join(root, file))
