from pathlib import Path

START_NUMBER = 1

def main():
    current_dir = Path.cwd()
    tml_files = sorted(current_dir.glob("*.tml"))

    counter = START_NUMBER

    for file_path in tml_files:
        new_name = f"survey{counter:03d}.clear.tml"
        new_path = current_dir / new_name

        # Skip if the target filename already exists
        if new_path.exists():
            raise FileExistsError(f"Target file already exists: {new_name}")

        file_path.rename(new_path)
        print(f"{file_path.name} -> {new_name}")

        counter += 1

if __name__ == "__main__":
    main()
