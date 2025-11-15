from pathlib import Path

from openspeleo_lib.interfaces.compass.models import MAKFile

if __name__ == "__main__":
    ff_json_fp = Path("Fulfords.json")

    obj = MAKFile.from_json(ff_json_fp)
    outfile_fp = Path("Fulfords.out.json")
    obj.to_json(outfile_fp)
