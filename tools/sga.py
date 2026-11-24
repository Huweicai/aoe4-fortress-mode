"""Lists and extracts files from AoE4 SGA v10 archives.

Usage: python3 tools/sga.py <archive.sga> <out_dir> [regex]   (needs the brotli package)
"""
import re
import struct
import sys
import zlib
from pathlib import Path

FOLDER = struct.Struct("<5I")
# name offset, hash offset, data offset, compressed size, size, verification, storage, crc
FILE = struct.Struct("<IIQIIBBI")


def read(path):
    data = Path(path).read_bytes()
    header_offset, header_length, data_offset, _ = struct.unpack_from("<QIQQ", data, 0x8C)
    header = data[header_offset:header_offset + header_length]
    (_, _, folder_offset, folder_count, file_offset, file_count, string_offset, string_length) = struct.unpack_from("<8I", header, 0)
    strings = header[string_offset:string_offset + string_length]

    def name(offset):
        return strings[offset:strings.index(b"\0", offset)].decode("utf-8")

    folders = [FOLDER.unpack_from(header, folder_offset + i * FOLDER.size) for i in range(folder_count)]
    files = [FILE.unpack_from(header, file_offset + i * FILE.size) for i in range(file_count)]
    entries = []
    for name_offset, _, _, file_start, file_end in folders:
        folder = name(name_offset).replace("\\", "/")
        for index in range(file_start, file_end):
            entry = files[index]
            entries.append((f"{folder}/{name(entry[0])}".lstrip("/"), entry))
    return data, data_offset, entries


def content(data, data_offset, entry):
    _, _, offset, compressed, size, _, storage, _ = entry
    raw = data[data_offset + offset:data_offset + offset + compressed]
    if storage == 0 or compressed == size:
        return raw
    try:
        return zlib.decompress(raw)
    except zlib.error:
        import brotli
        return brotli.decompress(raw)


def main():
    archive, out_dir = sys.argv[1], Path(sys.argv[2])
    pattern = re.compile(sys.argv[3]) if len(sys.argv) > 3 else None
    data, data_offset, entries = read(archive)
    count, failed = 0, []
    for path, entry in entries:
        if pattern is None or pattern.search(path):
            try:
                body = content(data, data_offset, entry)
            except Exception:
                failed.append(path)
                continue
            target = out_dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            count += 1
    print(f"{count} of {len(entries)} files extracted, {len(failed)} could not be decoded")
    for path in failed[:10]:
        print("  undecoded:", path)


if __name__ == "__main__":
    main()
