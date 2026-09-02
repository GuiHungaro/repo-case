import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests

GITHUB_ORG = "microsoft"
PER_PAGE = 100
MAX_RETRIES = 3
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
COLUMNS = [
    "nome",
    "descricao",
    "linguagem_principal",
    "estrelas",
    "forks",
    "criado_em",
    "atualizado_em",
]


def get_token():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        sys.exit("erro: GITHUB_TOKEN nao definido no ambiente")
    return token


def request_with_retry(session, url, params, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        error = None
        response = None
        try:
            response = session.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:
            error = str(exc)
        if response is not None and response.status_code == 200:
            return response.json()
        if response is not None and response.status_code not in (429, 500, 502, 503, 504):
            sys.exit(f"erro: HTTP {response.status_code} ao acessar {url}")
        if attempt == MAX_RETRIES:
            detail = error or f"HTTP {response.status_code}"
            sys.exit(f"erro: {url} falhou apos {MAX_RETRIES} tentativas ({detail})")
        wait = 2 ** attempt
        if response is not None and response.headers.get("Retry-After"):
            wait = int(response.headers["Retry-After"])
        print(f"aviso: tentativa {attempt} falhou, repetindo em {wait}s")
        time.sleep(wait)


def collect_repositories(session, token):
    repositories = []
    page = 1
    while True:
        data = request_with_retry(
            session,
            f"https://api.github.com/orgs/{GITHUB_ORG}/repos",
            {"per_page": PER_PAGE, "page": page, "type": "public", "sort": "full_name"},
            token,
        )
        if not data:
            return repositories
        repositories.extend(data)
        page += 1


def to_record(repository):
    return {
        "nome": repository.get("name") or "",
        "descricao": repository.get("description") or "",
        "linguagem_principal": repository.get("language") or "",
        "estrelas": repository.get("stargazers_count", 0),
        "forks": repository.get("forks_count", 0),
        "criado_em": repository.get("created_at") or "",
        "atualizado_em": repository.get("updated_at") or "",
    }


def write_csv(path, records):
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def main():
    start = time.monotonic()
    token = get_token()
    session = requests.Session()
    organization = request_with_retry(
        session, f"https://api.github.com/orgs/{GITHUB_ORG}", {}, token
    )
    declared = organization.get("public_repos", 0)
    repositories = collect_repositories(session, token)
    if len(repositories) != declared:
        sys.exit(
            f"erro: coletados {len(repositories)} repositorios, "
            f"a organizacao declara {declared}; arquivo nao gravado"
        )
    records = [to_record(r) for r in repositories]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history_dir = OUTPUT_DIR / "history"
    history_dir.mkdir(exist_ok=True)
    snapshot = OUTPUT_DIR / f"repos_{GITHUB_ORG}.csv"
    archive = history_dir / f"repos_{GITHUB_ORG}_{date.today().isoformat()}.csv"
    write_csv(snapshot, records)
    write_csv(archive, records)
    duration = int(time.monotonic() - start)
    print(f"organizacao: {GITHUB_ORG}")
    print(f"coletados {len(records)} de {declared} repositorios publicos declarados")
    print(f"snapshot: {snapshot}")
    print(f"historico: {archive}")
    print(f"erros: 0 | duracao: {duration}s")
    print("status: ok")


if __name__ == "__main__":
    main()
