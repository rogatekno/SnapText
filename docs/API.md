# SnapText API Reference

Complete API documentation for the hybrid SnapText OCR service.

## Base URL
`http://localhost:8000/api/v1`

## Endpoints

### 1. Document Scanning
#### `POST /ocr/scan`
Extract structured data from documents (KTP, Family Cards/KK, Invoices, Receipts).

**Parameters**:
- `file` (required): Image file.
- `use_llm` (optional): `true` (default) or `false`. Uses the local SLM for dynamic mapping.
- `fields` (optional): Specific fields to target (e.g., "Nama, NIK").
- `lang` (optional): OCR language, default `"id"`.
- `debug` (optional): `true` for base64 annotated image in response.

**Response (Hybrid Mode)**:
```json
{
  "success": true,
  "document_type": "ktp",
  "data": {
    "nik": "3171...",
    "nama": "Budi Utomo",
    "alamat": "Jl. Mawar No. 123",
    "pekerjaan": "Pegawai Swasta"
  },
  "processing_time_ms": 2540.5
}
```

**Response (Complex/Complex Data)**:
```json
{
  "success": true,
  "data": {
    "invoice_no": "INV/2026/001",
    "items": [
      { "name": "Produk A", "qty": 2, "price": 50000 },
      { "name": "Produk B", "qty": 1, "price": 120000 }
    ],
    "total": 220000
  }
}
```

---

### 2. Visualization
#### `POST /ocr/visualize`
Returns a binary PNG image with bounding boxes marked around detected text.

**Parameters**:
- `file` (required): Image file.

**Response Headers**:
- `X-Regions-Count`: Number of regions detected.
- `X-Processing-Time-Ms`: Time taken.

---

### 3. Health & Status
#### `GET /health`
Returns the status of the service, OCR model, and environment.

#### `GET /ocr/info`
Returns configuration limits (Max upload size, supported formats, model state).

## Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `VALIDATION_ERROR` | 400 | File too large or invalid format. |
| `OCR_ERROR` | 400 | Engine failed to process image. |
| `INTERNAL_ERROR` | 500 | Unexpected server error. |
