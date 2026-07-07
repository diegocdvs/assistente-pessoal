from __future__ import annotations

import re

from app.core.models import Category, Classification, EmailItem, Priority

PROMO_SENDERS = ("newsletter", "marketing", "promocao", "promo", "ofertas", "no-reply")
NEWSLETTER_TERMS = ("unsubscribe", "descadastrar", "boletim", "newsletter")
FINANCE_TERMS = ("boleto", "fatura", "pagamento", "pix", "nota fiscal", "nf-e", "vencimento")
EVENT_TERMS = ("convite", "reuniao", "evento", "webinar", "agenda", "meet", "teams", "zoom")
WORK_TERMS = ("allpost", "bling", "tray", "cliente", "suporte", "projeto")
SECURITY_TERMS = ("login", "senha", "acesso", "2fa", "verificacao", "fraude")
PURCHASE_TERMS = ("pedido", "compra", "entrega", "rastreio", "nota do pedido")


def classify_email(email: EmailItem) -> Classification:
    text = f"{email.sender} {email.subject} {email.snippet}".lower()

    if any(term in text for term in SECURITY_TERMS):
        return Classification(Category.SECURITY, Priority.CRITICA, "Possivel aviso de acesso/seguranca.", False, False)

    if any(term in text for term in FINANCE_TERMS):
        return Classification(Category.FINANCEIRO, Priority.IMPORTANTE, "Termos financeiros detectados.", False, False)

    if any(term in text for term in EVENT_TERMS) or _contains_date_hint(text):
        return Classification(Category.EVENTO, Priority.IMPORTANTE, "Possivel compromisso ou evento.", False, True)

    if any(term in text for term in WORK_TERMS):
        return Classification(Category.TRABALHO, Priority.IMPORTANTE, "Possivel assunto de trabalho.", False, False)

    if any(term in text for term in PURCHASE_TERMS):
        return Classification(Category.COMPRA, Priority.INFORMATIVA, "Possivel compra ou entrega.", False, False)

    if any(term in text for term in NEWSLETTER_TERMS):
        return Classification(Category.NEWSLETTER, Priority.RUIDO, "Padrao de newsletter detectado.", False, False)

    if any(term in text for term in PROMO_SENDERS):
        return Classification(Category.PROMOCOES, Priority.RUIDO, "Remetente ou texto com padrao promocional.", False, False)

    return Classification(Category.OUTROS, Priority.INFORMATIVA, "Sem regra especifica; revisar no relatorio.", False, False)


def _contains_date_hint(text: str) -> bool:
    patterns = [
        r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
        r"\b\d{1,2}h\d{0,2}\b",
        r"\b\d{1,2}:\d{2}\b",
        r"\bamanh[aa]\b",
        r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)
