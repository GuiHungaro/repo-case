import json
import os
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
PROMPT_FILE = BASE_DIR / "prompt.txt"
DATA_FILE = BASE_DIR.parent / "data" / "conversas_prevendas.json"
OUTPUT_DIR = BASE_DIR / "output"
MAX_RETRIES = 3
TIMEOUT = 120
RESPONSE_FIELDS = {"sinais", "proxima_acao", "resumo_para_o_vendedor"}
WEIGHTS = {
    "projeto_real": 3,
    "interesse_declarado": 1,
    "verba_definida": 3,
    "verba_proxy": 1,
    "prazo_curto": 3,
    "prazo_medio": 2,
    "prazo_longo": -2,
    "passo_agendado": 2,
    "intencao_fechamento": 2,
    "lead_retorno": 1,
    "objecao_preco": -1,
}
EXCLUSIVE_GROUPS = (
    ("prazo_curto", "prazo_medio", "prazo_longo"),
    ("verba_definida", "verba_proxy"),
)


def call_model(session, url, api_key, model, messages):
    try:
        response = session.post(
            url,
            json={"model": model, "temperature": 0, "messages": messages},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return "", f"falha de conexao ({exc})", False
    if response.status_code == 200:
        try:
            data = json.loads(response.content.decode("utf-8"))
            return data["choices"][0]["message"]["content"], "", False
        except (KeyError, IndexError, ValueError, UnicodeDecodeError):
            return "", "resposta da api em formato inesperado", False
    if response.status_code in (429, 500, 502, 503, 504):
        return "", f"HTTP {response.status_code}", False
    return "", f"HTTP {response.status_code} na chamada do modelo", True


def extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != RESPONSE_FIELDS:
        return "estrutura de resposta inesperada"
    sinais = payload["sinais"]
    if not isinstance(sinais, list) or not all(isinstance(tag, str) for tag in sinais):
        return "sinais deve ser uma lista de tags"
    if len(set(sinais)) != len(sinais):
        return "tag repetida em sinais"
    for group in EXCLUSIVE_GROUPS:
        active = [tag for tag in sinais if tag in group]
        if len(active) > 1:
            return f"tags conflitantes: {', '.join(active)}"
    unknown = [tag for tag in sinais if tag not in WEIGHTS and tag != "fora_do_servico"]
    if unknown:
        return f"tag desconhecida: {unknown[0]}"
    for field in ("proxima_acao", "resumo_para_o_vendedor"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            return f"{field} deve ser texto nao vazio"
    return ""


def score_lead(sinais):
    if "fora_do_servico" in sinais:
        return "fora_do_perfil", 3, None
    total = sum(WEIGHTS[tag] for tag in sinais)
    if total >= 7:
        classification = "quente"
    elif total >= 1:
        classification = "morno"
    else:
        classification = "frio"
    if classification == "quente" and {"passo_agendado", "intencao_fechamento"} & set(sinais):
        priority = 1
    elif classification == "quente":
        priority = 2
    elif classification == "morno" and {"verba_definida", "verba_proxy"} & set(sinais):
        priority = 2
    else:
        priority = 3
    return classification, priority, total


def render_conversation(conversation):
    lines = [
        f"{'LEAD' if message['de'] == 'lead' else 'ATENDENTE'}: {message['texto']}"
        for message in conversation["mensagens"]
    ]
    return f"Conversa {conversation['conversa_id']}:\n" + "\n".join(lines)


def build_result(conversation, payload):
    classification, priority, total = score_lead(payload["sinais"])
    return {
        "conversa_id": conversation["conversa_id"],
        "classificacao": classification,
        "prioridade": priority,
        "score": total,
        "sinais": payload["sinais"],
        "proxima_acao": payload["proxima_acao"],
        "resumo_para_o_vendedor": payload["resumo_para_o_vendedor"],
    }


def build_failure(conversation, error):
    return {
        "conversa_id": conversation["conversa_id"],
        "classificacao": "nao_classificado",
        "prioridade": 3,
        "score": None,
        "sinais": [],
        "proxima_acao": "",
        "resumo_para_o_vendedor": "",
        "erro": error,
    }


def process_conversation(session, url, api_key, model, prompt, conversation):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": render_conversation(conversation)},
    ]
    error = "erro desconhecido"
    for attempt in range(1, MAX_RETRIES + 1):
        fatal = False
        content, error, fatal = call_model(session, url, api_key, model, messages)
        if not error:
            payload = extract_json(content)
            if payload is None:
                error = "resposta do modelo nao e json valido"
            else:
                error = validate(payload)
                if not error:
                    return build_result(conversation, payload)
        if fatal or attempt == MAX_RETRIES:
            break
        wait = 2**attempt
        print(
            f"aviso: {conversation['conversa_id']} tentativa {attempt} falhou "
            f"({error}), repetindo em {wait}s"
        )
        time.sleep(wait)
    return build_failure(conversation, error)


def main():
    start = time.monotonic()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("LLM_MODEL", "").strip()
    if not api_key or not base_url or not model:
        sys.exit("erro: defina LLM_API_KEY, LLM_BASE_URL e LLM_MODEL no ambiente")
    prompt = PROMPT_FILE.read_text(encoding="utf-8")
    conversations = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    url = f"{base_url}/chat/completions"
    counts = {"quente": 0, "morno": 0, "frio": 0, "fora_do_perfil": 0}
    for conversation in conversations:
        result = process_conversation(session, url, api_key, model, prompt, conversation)
        (OUTPUT_DIR / f"{conversation['conversa_id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        classification = result["classificacao"]
        if classification == "nao_classificado":
            print(f"erro: {conversation['conversa_id']} sem classificacao ({result['erro']})")
        else:
            counts[classification] += 1
            print(
                f"{conversation['conversa_id']}: {classification} "
                f"(prioridade {result['prioridade']}, score {result['score']})"
            )
    duration = int(time.monotonic() - start)
    print(" | ".join(f"{name}: {count}" for name, count in counts.items()))
    print(f"duracao: {duration}s")
    if sum(counts.values()) < len(conversations):
        print("status: falha parcial")
        return 1
    print("status: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
