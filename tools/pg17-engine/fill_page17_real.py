#!/usr/bin/env python3
"""
Fill page 17 escrow holder acknowledgment fields (image-preserving overlay mode).

Anchor-mode strategy (default):
- OCR full page
- Find semantic anchor words (deposit / advised / escrow# / address / phone / license / department)
- Compute write coordinates relative to anchors
- Overlay only target text/check marks, keep original PDF image unchanged

Dependencies:
  pip install pypdf reportlab pymupdf pytesseract pillow
System dependency:
  tesseract binary (brew install tesseract)
"""

import argparse
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


@dataclass
class FillData:
    deposit_amount: str | None = None
    seller_agent: str | None = None
    escrow_number: str | None = None
    acceptance_date: str | None = None
    second_date: str | None = None


FIXED = {
    "counter_offer_numbers": "one",
    "escrow_company": "Culture Escrow Inc.",
    "by_name": "Kevin Hsu",
    "address": "2060 Huntington Dr. #3, San Marino, CA 91108",
    "phone": "626-308-3088",
    "license": "963-1739",
}

# Fallback coords if anchors fail.
FALLBACK_COORDS: Dict[str, Tuple[float, float]] = {
    "checkbox_deposit": (353, 351),
    "deposit_amount": (465, 350),
    "counter_offer_numbers": (105, 342),
    "seller_agent": (150, 316),
    "escrow_company": (105, 303),
    "by_name": (72, 290),
    "subject_terms": (40, 330),
    "escrow_number": (450, 303),
    "acceptance_date": (370, 316),
    "second_date": (490, 290),
    "address": (72, 277),
    "phone": (110, 263),
    "license": (215, 251),
    "checkbox_dfpi": (37, 237),
}

# Fine-tune offsets (points) after anchor placement.
FIELD_OFFSETS: Dict[str, Tuple[float, float]] = {
    "checkbox_deposit": (-12, -6),
    "checkbox_dfpi": (-6, -6),
    "deposit_amount": (19, -6),
    "counter_offer_numbers": (25, -3),
    "seller_agent": (48, -4),
    "escrow_company": (54, -4),
    "by_name": (20, -5),
    "subject_terms": (0, -2),
    "escrow_number": (10, -5),
    "acceptance_date": (66, -6),
    "second_date": (0, -4),
    "address": (0, -5),
    "phone": (30, -5),
    "license": (48, -5),
}

FIELD_FONT_SIZES: Dict[str, float] = {
    "seller_agent": 9.0,
}


def default_output_path(source_pdf: str) -> str:
    src = Path(source_pdf)
    return str(src.with_name(f"{src.stem}-done.pdf"))


def resolve_page_index(total_pages: int, preferred_index: int = 16) -> int:
    if total_pages <= 0:
        raise ValueError("empty PDF")
    return preferred_index if preferred_index < total_pages else total_pages - 1


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def render_page_rgb(path: str, page_index: int, dpi: int = 300):
    import fitz
    from PIL import Image

    doc = fitz.open(path)
    page_index = resolve_page_index(len(doc), page_index)
    page = doc[page_index]
    scale = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img, page.rect.height, scale


def ocr_words(img):
    import pytesseract

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 6")
    words = []
    n = len(data["text"])
    for i in range(n):
        t = normalize_text(data["text"][i])
        if not t:
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1
        words.append(
            {
                "text": t,
                "lower": t.lower(),
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "w": int(data["width"][i]),
                "h": int(data["height"][i]),
                "conf": conf,
            }
        )
    return words


def img_to_pdf(x_img: float, y_img_top: float, h_img: float, page_height: float, scale: float):
    x_pdf = x_img / scale
    y_pdf = page_height - ((y_img_top + h_img * 0.15) / scale)
    return x_pdf, y_pdf


def find_word(words, needle: str, min_y: int = 0):
    needle = needle.lower()
    cands = [w for w in words if needle in w["lower"] and w["y"] >= min_y]
    if not cands:
        return None
    cands.sort(key=lambda w: (w["y"], w["x"]))
    return cands[0]


def find_nearby(words, primary: str, secondary: str, max_dy: int = 30, min_y: int = 0):
    p = find_word(words, primary, min_y=min_y)
    if not p:
        return None, None
    cands = [w for w in words if secondary in w["lower"] and abs(w["y"] - p["y"]) <= max_dy]
    if not cands:
        return p, None
    cands.sort(key=lambda w: abs(w["x"] - p["x"]))
    return p, cands[0]


def locate_coords_by_anchors(source_pdf: str, page_index: int = 16, dpi: int = 300):
    img, page_h, scale = render_page_rgb(source_pdf, page_index, dpi=dpi)
    words = ocr_words(img)
    if not words:
        return FALLBACK_COORDS.copy(), {"mode": "fallback:no_ocr_words"}

    # Focus lower half where escrow block is.
    min_y = int(img.height * 0.50)

    coords = FALLBACK_COORDS.copy()
    debug = {"mode": "anchor"}

    deposit = find_word(words, "deposit", min_y=min_y)
    amount = find_word(words, "amount", min_y=min_y)
    numbers = find_word(words, "numbers", min_y=min_y)
    advised = find_word(words, "advised", min_y=min_y)
    subject = find_word(words, "subject", min_y=min_y)
    acceptance = find_word(words, "acceptance", min_y=min_y)
    address = find_word(words, "address", min_y=min_y)
    by_candidates = [w for w in words if w["lower"] == "by" and w["y"] >= min_y]
    by_word = None
    phone = find_word(words, "phone", min_y=min_y)
    license_w = find_word(words, "license", min_y=min_y)
    dept = find_word(words, "department", min_y=min_y)
    escrow_word = find_word(words, "escrow", min_y=min_y)
    date_w = find_word(words, "date", min_y=min_y)

    # Prefer anchors inside escrow block body (below "advised" line)
    advised_y = advised["y"] if advised else min_y
    escrow_line_words = [w for w in words if "escrow" in w["lower"] and advised_y + 10 <= w["y"] <= advised_y + 80]
    escrow_num_words = [w for w in words if ("#" in w["text"] or "escrow#" in w["lower"]) and advised_y + 10 <= w["y"] <= advised_y + 90]

    if deposit:
        coords["checkbox_deposit"] = img_to_pdf(deposit["x"] - 14, deposit["y"], deposit["h"], page_h, scale)
    if amount:
        coords["deposit_amount"] = img_to_pdf(amount["x"] + amount["w"] + 18, amount["y"], amount["h"], page_h, scale)
    if numbers:
        coords["counter_offer_numbers"] = img_to_pdf(numbers["x"] + numbers["w"] + 10, numbers["y"], numbers["h"], page_h, scale)

    # Terms sentence should sit just above "Escrow Holder is advised by".
    if advised:
        _, sy = img_to_pdf(70, max(advised["y"] - 12, 0), advised["h"], page_h, scale)
        coords["subject_terms"] = (40.0, sy)
    elif numbers:
        _, cy = coords["counter_offer_numbers"]
        coords["subject_terms"] = (40.0, cy)

    if advised:
        coords["seller_agent"] = img_to_pdf(advised["x"] + advised["w"] + 18, advised["y"], advised["h"], page_h, scale)

    if acceptance:
        coords["acceptance_date"] = img_to_pdf(acceptance["x"] + acceptance["w"] + 98, acceptance["y"], acceptance["h"], page_h, scale)

    # Escrow Holder / Escrow# line
    if escrow_line_words:
        escrow_line_words.sort(key=lambda w: (abs(w["x"] - 70), w["y"]))
        ew = escrow_line_words[0]
        coords["escrow_company"] = img_to_pdf(ew["x"] + 96, ew["y"], ew["h"], page_h, scale)

        if escrow_num_words:
            escrow_num_words.sort(key=lambda w: (w["y"], -w["x"]))
            enw = escrow_num_words[0]
            coords["escrow_number"] = img_to_pdf(enw["x"] + 22, enw["y"], enw["h"], page_h, scale)
        else:
            coords["escrow_number"] = img_to_pdf(ew["x"] + 395, ew["y"], ew["h"], page_h, scale)
    elif escrow_word:
        coords["escrow_company"] = img_to_pdf(escrow_word["x"] + 96, escrow_word["y"] + 20, escrow_word["h"], page_h, scale)
        coords["escrow_number"] = img_to_pdf(escrow_word["x"] + 395, escrow_word["y"] + 20, escrow_word["h"], page_h, scale)

    # second date = Date on line below escrow# in escrow section
    section_dates = [w for w in words if "date" in w["lower"] and advised_y + 20 <= w["y"] <= advised_y + 120]
    if section_dates:
        section_dates.sort(key=lambda w: (w["y"], -w["x"]))
        d2 = section_dates[-1]
        coords["second_date"] = img_to_pdf(d2["x"] + d2["w"] + 8, d2["y"], d2["h"], page_h, scale)
    elif date_w:
        coords["second_date"] = img_to_pdf(date_w["x"] + date_w["w"] + 8, date_w["y"], date_w["h"], page_h, scale)

    if address:
        coords["address"] = img_to_pdf(address["x"] + address["w"] + 8, address["y"], address["h"], page_h, scale)
        coords["by_name"] = img_to_pdf(address["x"] + 18, max(address["y"] - 22, 0), address["h"], page_h, scale)
    if by_candidates:
        if address:
            target_y = max(address["y"] - 22, 0)
            by_candidates.sort(key=lambda w: abs(w["y"] - target_y))
        elif advised:
            by_candidates.sort(key=lambda w: abs(w["y"] - (advised["y"] + 52)))
        by_word = by_candidates[0]
        coords["by_name"] = img_to_pdf(by_word["x"] + by_word["w"] + 10, by_word["y"], by_word["h"], page_h, scale)

    if phone:
        coords["phone"] = img_to_pdf(phone["x"] + phone["w"] + 8, phone["y"], phone["h"], page_h, scale)
    if license_w:
        coords["license"] = img_to_pdf(license_w["x"] + license_w["w"] + 65, license_w["y"], license_w["h"], page_h, scale)
    if dept:
        coords["checkbox_dfpi"] = img_to_pdf(dept["x"] - 12, dept["y"], dept["h"], page_h, scale)

    debug["anchors_found"] = {
        "deposit": bool(deposit),
        "amount": bool(amount),
        "numbers": bool(numbers),
        "advised": bool(advised),
        "subject": bool(subject),
        "acceptance": bool(acceptance),
        "address": bool(address),
        "by": bool(by_word),
        "phone": bool(phone),
        "license": bool(license_w),
        "department": bool(dept),
        "escrow": bool(escrow_word),
        "date": bool(date_w),
    }
    return coords, debug


def decide_overlay(data: FillData):
    today = datetime.now().strftime("%m/%d/%Y")
    subject_line = f"subject to terms and conditions shown on Culture Escrow's escrow instruction dated {today}"

    to_write = {
        "checkbox_deposit": "X",
        "checkbox_dfpi": "X",
        "counter_offer_numbers": FIXED["counter_offer_numbers"],
        "escrow_company": FIXED["escrow_company"],
        "by_name": FIXED["by_name"],
        "subject_terms": subject_line,
        "address": FIXED["address"],
        "phone": FIXED["phone"],
        "license": FIXED["license"],
    }
    left_blank = []

    variable_map = {
        "deposit_amount": data.deposit_amount,
        "seller_agent": data.seller_agent,
        "escrow_number": data.escrow_number,
        "acceptance_date": data.acceptance_date,
        "second_date": data.second_date,
    }
    for k, v in variable_map.items():
        if v:
            to_write[k] = v
        else:
            left_blank.append(k)

    filled_fields = list(to_write.keys())
    return to_write, filled_fields, left_blank


def build_overlay(page_width: float, page_height: float, to_write: Dict[str, str], coords: Dict[str, Tuple[float, float]]) -> bytes:
    from reportlab.pdfgen import canvas

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    c.setFont("Helvetica", 10)

    for key, text in to_write.items():
        x, y = coords.get(key, FALLBACK_COORDS[key])
        dx, dy = FIELD_OFFSETS.get(key, (0, 0))
        if key == "subject_terms":
            c.setFont("Helvetica", 8)
        else:
            c.setFont("Helvetica", FIELD_FONT_SIZES.get(key, 10))
        c.drawString(float(x + dx), float(y + dy), text)

    c.save()
    return packet.getvalue()


def apply_template_alignments(coords: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
    """
    Apply template-specific alignment constraints requested by user feedback.

    Rules:
    1) acceptance_date: same vertical line (x) as escrow_number; same horizontal line (y) as seller_agent.
    2) second_date: same vertical line (x) as acceptance_date (final rendered x);
       same horizontal line (y) as by_name / Kevin Hsu (final rendered y).
    """
    c = dict(coords)

    if "escrow_number" in c and "seller_agent" in c:
        esc_x, _ = c["escrow_number"]
        _, seller_y = c["seller_agent"]
        c["acceptance_date"] = (esc_x, seller_y)

    if "acceptance_date" in c and "by_name" in c:
        acc_dx, _ = FIELD_OFFSETS.get("acceptance_date", (0, 0))
        sec_dx, sec_dy = FIELD_OFFSETS.get("second_date", (0, 0))
        _, by_dy = FIELD_OFFSETS.get("by_name", (0, 0))

        acc_x, _ = c["acceptance_date"]
        _, by_y = c["by_name"]

        # convert from final-render target back to base coords used by build_overlay()
        second_x = (acc_x + acc_dx) - sec_dx
        second_y = (by_y + by_dy) - sec_dy
        c["second_date"] = (second_x, second_y)

    return c


def fill_pdf(source: str, output: str, data: FillData, page_index: int = 16, use_anchor_mode: bool = True):
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(source)
    writer = PdfWriter()

    page_index = resolve_page_index(len(reader.pages), page_index)
    target = reader.pages[page_index]
    width = float(target.mediabox.width)
    height = float(target.mediabox.height)

    coords, anchor_debug = (FALLBACK_COORDS.copy(), {"mode": "fallback"})
    if use_anchor_mode:
        coords, anchor_debug = locate_coords_by_anchors(source, page_index=page_index)

    coords = apply_template_alignments(coords)

    to_write, filled_fields, left_blank = decide_overlay(data)

    overlay_pdf = PdfReader(io.BytesIO(build_overlay(width, height, to_write, coords)))
    target.merge_page(overlay_pdf.pages[0])

    for i, p in enumerate(reader.pages):
        writer.add_page(target if i == page_index else p)

    with open(output, "wb") as f:
        writer.write(f)

    return filled_fields, left_blank, anchor_debug, coords


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output")
    ap.add_argument("--deposit-amount")
    ap.add_argument("--seller-agent")
    ap.add_argument("--escrow-number")
    ap.add_argument("--acceptance-date")
    ap.add_argument("--second-date")
    ap.add_argument("--no-anchor-mode", action="store_true")
    args = ap.parse_args()

    output = args.output or default_output_path(args.source)

    payload = FillData(
        deposit_amount=args.deposit_amount,
        seller_agent=args.seller_agent,
        escrow_number=args.escrow_number,
        acceptance_date=args.acceptance_date,
        second_date=args.second_date,
    )

    filled_fields, left_blank, anchor_debug, used_coords = fill_pdf(
        args.source,
        output,
        payload,
        use_anchor_mode=not args.no_anchor_mode,
    )

    missing_inputs = [
        k
        for k, v in {
            "deposit_amount": args.deposit_amount,
            "seller_agent_name": args.seller_agent,
            "escrow_number": args.escrow_number,
            "acceptance_date": args.acceptance_date,
            "second_date": args.second_date,
        }.items()
        if not v
    ]

    summary = {
        "output_pdf": output,
        "missing_inputs": missing_inputs,
        "filled_fields": filled_fields,
        "left_blank": left_blank,
        "already_filled_in_source": [],
        "anchor_debug": anchor_debug,
        "used_coords": {k: [round(v[0], 2), round(v[1], 2)] for k, v in used_coords.items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
