"""Document template registry for automatic classification and mapping.

This module stores predefined fields and anchor keywords for common Indonesian documents.
"""

from typing import Any, Dict, List

DOCUMENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ktp": {
        "name": "KTP (Indonesian ID Card)",
        "anchors": ["PROVINSI", "NIK", "NIK :", "TEMPAT/TGL LAHIR"],
        # These labels exist on the card but are NOT fields - used to exclude their regions from value mapping
        "extra_labels": ["Gol. Darah", "Gol Darah"],
        # Patterns to strip from extracted values (regex)
        "exclude_value_patterns": [
            r'Gol[\.\/]?\s*[Dd]arah\s*[:\-]?\s*[A-B]?[ABO]?\+?\-?',  # blood type
        ],
        "fields": [
            "NIK", 
            "Nama", 
            "Tempat/Tgl Lahir", 
            "Jenis Kelamin", 
            "Alamat", 
            "RT/RW",
            "Kel/Desa",
            "Kecamatan",
            "Agama", 
            "Status Perkawinan", 
            "Pekerjaan", 
            "Kewarganegaraan", 
            "Berlaku Hingga"
        ],
        "tables": []
    },
    "kk": {
        "name": "Kartu Keluarga",
        # exclusive_anchors: if ANY of these are found, classify immediately - no scoring
        "exclusive_anchors": ["KARTU KELUARGA"],
        "anchors": ["KARTU KELUARGA", "Nama Kepala Keluarga"],
        "fields": [
            "Nomor KK",
            "Nama Kepala Keluarga",
            "Alamat", 
            "RT/RW", 
            "Kode Pos", 
            "Desa/Kelurahan", 
            "Kecamatan", 
            "Kabupaten/Kota", 
            "Provinsi"
        ],
        "tables": [
            {
                "name": "anggota_keluarga",
                "columns": [
                    "Nama Lengkap", 
                    "NIK", 
                    "Jenis Kelamin", 
                    "Tempat Lahir", 
                    "Tanggal Lahir", 
                    "Agama", 
                    "Pendidikan", 
                    "Jenis Pekerjaan",
                    "Status Perkawinan",
                    "Status Hubungan"
                ]
            }
        ]
    },
    "bpjs": {
        "name": "BPJS Kesehatan",
        "anchors": ["BPJS", "BPJS KESEHATAN", "PEMBERI KERJA", "NOMOR PESERTA"],
        "fields": [
            "Nomor Peserta", 
            "Nama", 
            "Tanggal Lahir", 
            "NIK", 
            "Faskes Tingkat I"
        ],
        "tables": []
    },
    "bpjs_tk": {
        "name": "BPJS Ketenagakerjaan",
        "anchors": ["KARTU PESERTA", "KETENAGAKERJAAN"],
        "fields": [
            "Nomor Kartu", 
            "Nomor KPJ", 
            "Nama", 
            "Tgl Terdaftar"
        ],
        "mapping_strategy": "sequential",
        "tables": []
    }
}
