# Gerador de Certificados — Núcleo TI / MLC

Script Python que gera certificados de conclusão em PNG a partir de uma lista de alunos em CSV, renderizando um template HTML com Jinja2 e exportando via Playwright.

## Pré-requisitos

- Python 3.10+
- Conexão com a internet na primeira execução (fontes Google Fonts carregadas pelo Playwright)

## Instalação

```bash
pip install jinja2 segno playwright
playwright install chromium
```

## Estrutura do projeto

```
.
├── certificado-curso-mlcti.html   # template HTML/Jinja2
├── assets/
│   ├── luta-de-classes-full.png   # logo MLC
│   └── tux-engrenagem.svg         # logo Núcleo TI
├── alunos.csv                     # lista de alunos (coluna: nome)
├── config.json                    # dados do curso e emissor
└── gerar_certificados.py          # script principal
```

## Configuração

### `config.json`

Preencha os campos antes de gerar os certificados:

```json
{
  "curso_nome": "Nome do Curso",
  "data_curso": "DD/MM/AAAA",
  "carga_horaria": "X (extenso) horas",

  "professor1_nome": "Nome Completo",
  "professor1_cargo": "CARGO · NÚCLEO TI",
  "professor1_cpf": "000.000.000-00",

  "professor2_nome": "Nome Completo",
  "professor2_cargo": "CARGO · NÚCLEO TI",
  "professor2_cpf": "000.000.000-00",

  "emissor_nome": "Movimento Luta de Classes",
  "emissor_local": "Cidade / UF",
  "data_emissao": "DD.MM.AAAA",

  "ano_certificado": 2026,
  "numero_inicial": 1
}
```

### `alunos.csv`

Uma linha por aluno, com cabeçalho `nome`:

```csv
nome
Camarada Joana da Silva Pereira
Camarada João da Silva
```

## Uso

```bash
python gerar_certificados.py
```

Por padrão, os HTMLs intermediários em `tmp/` são apagados ao final. Para preservá-los:

```bash
python gerar_certificados.py --keep-tmp
```

Os certificados são salvos em `out/` com o formato:

```
out/certificado-2026-001-camarada-joana-da-silva-pereira.png
```

Cada certificado inclui um QR code com os dados básicos do aluno para verificação offline.

## Numeração

Os certificados são numerados sequencialmente a partir de `numero_inicial` definido no `config.json`, no formato `{ano}/{seq:03d}` (ex.: `2026/001`, `2026/002`).
