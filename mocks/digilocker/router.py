from fastapi import APIRouter, HTTPException

from synthetic_data import get_student

router = APIRouter()


@router.get("/issued/{aadhaar_ref}")
def get_issued_document(aadhaar_ref: str, doc_type: str):
    """An issuer-pushed document from the person's DigiLocker. 404 when absent."""
    student = get_student(aadhaar_ref)
    docs = student["sources"].get("digilocker", {}) if student else {}
    if doc_type not in docs:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    doc = docs[doc_type]
    return {"doc_type": doc_type, "holder_dob": student["dob"], "gender": student["gender"],
            "district": student["district"], **doc}


def _pdf(lines: list[str]) -> bytes:
    """A minimal, valid one-page PDF standing in for the issuer's signed document."""
    text = " ".join(f"({line.replace('(', '[').replace(')', ']')}) Tj T*" for line in lines)
    stream = f"BT /F1 12 Tf 14 TL 72 760 Td {text} ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


@router.get("/issued/{aadhaar_ref}/file")
def get_issued_file(aadhaar_ref: str, doc_type: str):
    from fastapi.responses import Response
    doc = get_issued_document(aadhaar_ref, doc_type)
    lines = [f"{doc['issuer']}", f"{doc_type} {doc['doc_id']}", f"Holder: {doc['holder_name']}"]
    lines += [f"{k}: {v}" for k, v in doc.get("data", {}).items()]
    return Response(content=_pdf(lines), media_type="application/pdf")
