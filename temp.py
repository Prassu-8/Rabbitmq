import os

OUTPUT_FILE = "project_dump.txt"
ALLOWED_EXTENSIONS = {".md", ".json", ".py", ".txt", ".env"}

def dump_project(root_dir, output_file):
    with open(output_file, "w", encoding="utf-8") as out:
        for root, dirs, files in os.walk(root_dir):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                filepath = os.path.join(root, filename)

                # Skip the output file itself
                if os.path.abspath(filepath) == os.path.abspath(output_file):
                    continue

                rel_path = os.path.relpath(filepath, root_dir)

                out.write("=" * 80 + "\n")
                out.write(f"FILE: {rel_path}\n")
                out.write("=" * 80 + "\n")

                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        out.write(f.read())
                except Exception as e:
                    out.write(f"[ERROR READING FILE: {e}]")

                out.write("\n\n")

if __name__ == "__main__":
    dump_project(".", OUTPUT_FILE)
    print(f"Project successfully written to {OUTPUT_FILE}")
