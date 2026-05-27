import argparse
import base64
import csv
import io
import json
import re
import unicodedata
from pathlib import Path

import segno
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description="Gera certificados a partir de alunos.csv")
parser.add_argument(
    "--keep-tmp",
    action="store_true",
    help="Mantém os HTMLs temporários em tmp/ após a geração (padrão: apagar)",
)
parser.add_argument(
    "--format",
    choices=["pdf", "png", "jpg", "webp"],
    default="pdf",
    help="Formato do arquivo de saída (padrão: pdf)",
)
parser.add_argument(
    "--scale",
    type=float,
    default=None,
    help=(
        "Fator de escala de saída. "
        "Raster (png/jpg/webp): device_scale_factor inteiro, padrão 3 (~300 DPI). "
        "PDF: multiplica papel e conteúdo, entre 0.1 e 2.0, padrão 1.0."
    ),
)
args = parser.parse_args()

ROOT = Path(__file__).parent.resolve()
TMP = ROOT / "tmp"
OUT = ROOT / "out"
TMP.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

with open(ROOT / "config.json", encoding="utf-8") as f:
    config = json.load(f)

with open(ROOT / "alunos.csv", newline="", encoding="utf-8") as f:
    alunos = [row["nome"].strip() for row in csv.DictReader(f) if row["nome"].strip()]

env = Environment(loader=FileSystemLoader(str(ROOT)), autoescape=True)
template = env.get_template("certificado-curso-mlcti.html")

assets_url = ROOT / "assets"


def make_qr_src(payload: str) -> str:
    qr = segno.make(payload, encoding="utf-8", error="l")
    buf = io.BytesIO()
    qr.save(buf, kind="png", dark="black", light="white", scale=10, border=2)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


ano = config["ano_certificado"]
numero_inicial = config["numero_inicial"]

html_files: list[tuple[Path, str, str, int]] = []

for i, aluno_nome in enumerate(alunos):
    seq = numero_inicial + i
    certificado_numero = f"{ano}/{seq:03d}"

    qr_payload = json.dumps(
        {
            "id": certificado_numero,
            "n": strip_accents(aluno_nome),
            "d": config["data_curso"],
            "e": config["emissor_nome"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    qr_code_src = make_qr_src(qr_payload)

    rendered = template.render(
        aluno_nome=aluno_nome,
        curso_nome=config["curso_nome"],
        data_curso=config["data_curso"],
        carga_horaria=config["carga_horaria"],
        professor1_nome=config["professor1_nome"],
        professor1_cargo=config["professor1_cargo"],
        professor1_cpf=config["professor1_cpf"],
        professor2_nome=config["professor2_nome"],
        professor2_cargo=config["professor2_cargo"],
        professor2_cpf=config["professor2_cpf"],
        certificado_numero=certificado_numero,
        qr_code_src=qr_code_src,
        emissor_nome=config["emissor_nome"],
        emissor_local=config["emissor_local"],
        data_emissao=config["data_emissao"],
    )

    rendered = rendered.replace('src="assets/', f'src="file://{assets_url}/')

    tmp_file = TMP / f"cert-{seq:03d}.html"
    tmp_file.write_text(rendered, encoding="utf-8")

    slug = slugify(aluno_nome)
    out_name = f"certificado-{ano}-{seq:03d}-{slug}.{args.format}"
    out_path = OUT / out_name

    html_files.append((tmp_file, aluno_nome, certificado_numero, out_path))

is_pdf = args.format == "pdf"

if is_pdf:
    pdf_scale = args.scale if args.scale is not None else 1.0
    if not (0.1 <= pdf_scale <= 2.0):
        parser.error(f"--scale para PDF deve ser entre 0.1 e 2.0 (recebido: {pdf_scale})")
else:
    raster_scale = int(args.scale) if args.scale is not None else 3

with sync_playwright() as p:
    browser = p.chromium.launch()
    for tmp_file, aluno_nome, certificado_numero, out_path in html_files:
        page_kwargs = {"viewport": {"width": 1123, "height": 794}}
        if not is_pdf:
            page_kwargs["device_scale_factor"] = raster_scale
        page = browser.new_page(**page_kwargs)
        page.goto(f"file://{tmp_file.resolve()}")
        page.wait_for_load_state("networkidle")
        if is_pdf:
            # body tem padding:24px e min-height:100vh para exibição no browser;
            # sem esse reset o conteúdo fica 842px e estoura para uma segunda página.
            page.add_style_tag(content=(
                "@page{margin:0}"
                "@media print{body{padding:0;margin:0;min-height:0;display:block}}"
            ))
            page.pdf(
                path=str(out_path),
                width=f"{round(1123 * pdf_scale)}px",
                height=f"{round(794 * pdf_scale)}px",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                scale=pdf_scale,
            )
        else:
            playwright_type = "jpeg" if args.format == "jpg" else args.format
            page.locator(".page").screenshot(path=str(out_path), type=playwright_type)
        page.close()
        print(f"✓ {certificado_numero} — {aluno_nome} → {out_path.relative_to(ROOT)}")
    browser.close()

if not args.keep_tmp:
    for tmp_file, *_ in html_files:
        tmp_file.unlink(missing_ok=True)

print(f"\n{len(html_files)} certificado(s) gerado(s) em out/")
