from __future__ import annotations

import re

from app.core.models import Category, Classification, EmailEntity, Priority

SECURITY_TERMS = ("login", "senha", "acesso", "2fa", "verificacao", "fraude", "codigo de seguranca")
FINANCE_TERMS = ("boleto", "fatura", "pagamento", "pix", "nota fiscal", "nf-e", "vencimento")
DELIVERY_TERMS = ("entrega", "rastreio", "enviado", "transportadora", "saiu para entrega")
PURCHASE_TERMS = ("pedido", "compra", "recibo", "confirmacao de compra")
PROMO_TERMS = ("desconto", "oferta", "promocao", "cupom", "black friday", "% off", "24h")
NEWSLETTER_TERMS = ("newsletter", "unsubscribe", "descadastrar", "boletim", "tutorial", "guia", "artigo")
EVENT_TERMS = ("convite", "reuniao", "evento", "webinar", "agenda", "meet", "teams", "zoom", "entrevista")
WORK_TERMS = ("cliente", "suporte", "projeto", "reuniao", "prazo", "proposta", "contrato")
JOB_OFFER_TERMS = ("vaga", "emprego", "oportunidade", "recrutamento", "processo seletivo")
JOB_URGENT_TERMS = ("entrevista", "prazo", "convite", "resposta", "retorno")
SOCIAL_TERMS = ("comentou", "curtiu", "seguiu", "mencao", "mensagem no linkedin", "facebook", "instagram")
EDUCATION_TERMS = ("curso", "aula", "certificado", "matricula", "treinamento")
TRAVEL_TERMS = ("voo", "hotel", "reserva", "check-in", "embarque", "passagem")
HEALTH_TERMS = ("consulta", "exame", "medico", "laboratorio", "receita")


class RuleBasedClassifier:
    def classify(self, email: EmailEntity) -> Classification:
        text = _text(email)

        if _contains_any(text, SECURITY_TERMS):
            return Classification(Category.SEGURANCA, Priority.CRITICA, "Aviso de seguranca ou acesso detectado.", 0.92)

        if _contains_any(text, FINANCE_TERMS):
            return Classification(Category.FINANCEIRO, Priority.ALTA, "Termos financeiros detectados.", 0.88)

        if _contains_any(text, DELIVERY_TERMS):
            return Classification(Category.ENTREGA, Priority.NORMAL, "Possivel entrega ou rastreio.", 0.82)

        if _contains_any(text, PURCHASE_TERMS):
            return Classification(Category.COMPRA, Priority.NORMAL, "Possivel compra ou pedido.", 0.78)

        if _contains_any(text, JOB_OFFER_TERMS):
            if _contains_any(text, JOB_URGENT_TERMS):
                return Classification(Category.TRABALHO, Priority.ALTA, "Oferta de trabalho com convite, prazo ou resposta direta.", 0.84)
            return Classification(Category.TRABALHO, Priority.NORMAL, "Oferta de trabalho ou recrutamento.", 0.76)

        if _contains_any(text, PROMO_TERMS):
            return Classification(Category.PROMOCAO, Priority.RUIDO, "Promocao, desconto ou oferta detectada.", 0.86)

        if _contains_any(text, NEWSLETTER_TERMS):
            return Classification(Category.NEWSLETTER, Priority.RUIDO, "Newsletter, tutorial ou conteudo recorrente.", 0.84)

        if _contains_any(text, TRAVEL_TERMS):
            return Classification(Category.VIAGEM, Priority.NORMAL, "Possivel viagem ou reserva.", 0.8)

        if _contains_any(text, HEALTH_TERMS):
            return Classification(Category.SAUDE, Priority.ALTA, "Possivel assunto de saude.", 0.8)

        if _contains_any(text, EDUCATION_TERMS):
            return Classification(Category.EDUCACAO, Priority.NORMAL, "Possivel curso, aula ou treinamento.", 0.75)

        if _contains_any(text, SOCIAL_TERMS):
            return Classification(Category.SOCIAL, Priority.BAIXA, "Notificacao social detectada.", 0.72)

        if _contains_any(text, EVENT_TERMS) or _contains_date_hint(text):
            return Classification(Category.EVENTO, Priority.ALTA, "Possivel compromisso ou evento.", 0.78)

        if _contains_any(text, WORK_TERMS):
            return Classification(Category.TRABALHO, Priority.NORMAL, "Possivel assunto de trabalho.", 0.72)

        return Classification(Category.OUTROS, Priority.NORMAL, "Sem regra especifica.", 0.45)


def classify_email(email: EmailEntity) -> Classification:
    return RuleBasedClassifier().classify(email)


def _text(email: EmailEntity) -> str:
    return f"{email.sender} {email.subject} {email.snippet}".lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _contains_date_hint(text: str) -> bool:
    patterns = [
        r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
        r"\b\d{1,2}h\d{0,2}\b",
        r"\b\d{1,2}:\d{2}\b",
        r"\bamanh[aa]\b",
        r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)
