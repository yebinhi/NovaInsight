"""Question bank, metrics, and report suggestions for one diagnostic project."""

STAGES = (
    "discovery",
    "fit",
    "comparison",
    "decision",
    "verification",
)

STAGE_LABELS = {
    "discovery": "产品发现",
    "fit": "需求匹配",
    "comparison": "产品比较",
    "decision": "购买决策",
    "verification": "品牌核验",
}

CHANNEL_LABELS = {
    "api": "API 测试",
    "consumer": "消费者聊天界面",
}


def contains_brand(text, brand):
    return bool(brand) and brand.casefold() in text.casefold()


def _add(bank, text, stage, brand):
    cleaned = " ".join(text.split())
    if not cleaned or any(item["text"] == cleaned for item in bank):
        return
    bank.append({
        "stage": stage,
        "branded": contains_brand(cleaned, brand),
        "text": cleaned,
    })


def generate_questions(project, competitors, limit=50):
    brand = project["brand_name"].strip()
    product = project["products"].strip()
    country = project["country"].strip()
    audience = project["audience"].strip()
    english = project["language"] == "en"
    names = [item["name"].strip() for item in competitors if item["name"].strip()]
    rival = names[0] if names else ""
    bank = []

    hoped = []
    for line in project.get("hoped_questions", "").splitlines():
        for piece in line.split(" / "):
            text = " ".join(piece.split())
            if text:
                hoped.append(text)
    for text in hoped:
        stage = "verification" if contains_brand(text, brand) else "discovery"
        _add(bank, text, stage, brand)

    if english:
        templates = [
            ("discovery", f"Which {product} brands are suitable for {audience} in {country}?"),
            ("discovery", f"What are the main {product} brands in {country}?"),
            ("discovery", f"Which brands should a first-time buyer of {product} look at in {country}?"),
            ("discovery", f"Which {product} brands are commonly compared in {country}?"),
            ("discovery", f"What reliable {product} options are available in {country}?"),
            ("discovery", f"Which {product} brands do {audience} usually consider?"),
            ("discovery", f"What {product} brands appear most often in buying guides for {country}?"),
            ("discovery", f"If I live in {country}, which {product} brands are worth learning about?"),
            ("fit", f"Which {product} fits the everyday needs of {audience}?"),
            ("fit", f"Which {product} suits a limited budget in {country}?"),
            ("fit", f"Which {product} works in a small home?"),
            ("fit", f"Which specifications matter most when choosing {product}?"),
            ("fit", f"What do {audience} usually need from {product}?"),
            ("fit", f"Which {product} works alongside equipment people already own?"),
            ("fit", f"What should someone in {country} check before installing {product}?"),
            ("fit", f"Which {product} is meant for long-term use rather than a short trial?"),
            ("comparison", f"How do people usually compare {product} brands?"),
            ("comparison", f"How should price and performance be weighed for {product}?"),
            ("comparison", f"How do {product} brands in {country} differ on service?"),
            ("comparison", f"How do warranty and support differ between {product} brands?"),
            ("comparison", f"Which {product} brands suit {audience}, and which do not?"),
            ("comparison", f"What are the tradeoffs among the usual {product} choices in {country}?"),
            ("decision", f"How should a limited budget change the {product} choice in {country}?"),
            ("decision", f"What should {audience} prioritise when buying {product}?"),
            ("decision", f"When is {product} the wrong purchase?"),
            ("decision", f"What conditions should be confirmed before buying {product} in {country}?"),
            ("decision", f"What does a suitable {product} setup for {audience} include?"),
            ("decision", f"How do you avoid buying the wrong {product} specification?"),
            ("decision", f"Which factors decide a {product} purchase for {audience} today?"),
            ("decision", f"If only one {product} option can be chosen, how should it be screened?"),
            ("verification", f"Is {brand} reliable, and what are its drawbacks?"),
            ("verification", f"Does {brand} {product} suit {audience}?"),
            ("verification", f"Is the information on the {brand} website clear?"),
            ("verification", f"Can {brand} be bought in {country}?"),
            ("verification", f"What should someone check before choosing {brand}?"),
            ("verification", f"Which situations suit {brand}, and which do not?"),
            ("verification", f"What complaints or limits are commonly mentioned about {brand}?"),
            ("verification", f"What does {brand} publish about its {product} specifications?"),
        ]
        if rival:
            templates.extend([
                ("comparison", f"How does {rival} differ from other {product} choices?"),
                ("comparison", f"Who is {rival} for, and who should look elsewhere?"),
                ("comparison", f"If someone is already considering {rival}, what are the nearby alternatives?"),
                ("verification", f"How do {brand} and {rival} differ?"),
            ])
    else:
        templates = [
            ("discovery", f"{country}有哪些适合{audience}的{product}？"),
            ("discovery", f"{country}有哪些主要的{product}品牌？"),
            ("discovery", f"第一次购买{product}，在{country}应该看哪些品牌？"),
            ("discovery", f"{country}的{product}里，哪些品牌经常被放在一起比较？"),
            ("discovery", f"{country}有哪些比较可靠的{product}选择？"),
            ("discovery", f"{audience}通常会考虑哪些{product}品牌？"),
            ("discovery", f"面向{country}的选购指南里，常见哪些{product}品牌？"),
            ("discovery", f"如果人在{country}，有哪些{product}品牌值得先了解？"),
            ("fit", f"哪些{product}适合{audience}的日常使用？"),
            ("fit", f"预算有限时，{country}有哪些{product}更合适？"),
            ("fit", f"哪些{product}适合空间有限的家庭？"),
            ("fit", f"选择{product}时，哪些规格最重要？"),
            ("fit", f"{audience}使用{product}时，最常见的需求是什么？"),
            ("fit", f"哪些{product}适合和已经在用的设备一起工作？"),
            ("fit", f"在{country}安装{product}之前，通常要确认什么？"),
            ("fit", f"哪些{product}适合长期使用，而不是短期试用？"),
            ("comparison", f"大家通常怎么比较不同的{product}品牌？"),
            ("comparison", f"选择{product}时，价格和性能应该怎么权衡？"),
            ("comparison", f"{country}的{product}品牌在服务上有什么差别？"),
            ("comparison", f"不同{product}品牌的质保和售后有什么差别？"),
            ("comparison", f"哪些{product}品牌更适合{audience}，哪些不适合？"),
            ("comparison", f"在{country}选{product}，常见方案之间的取舍是什么？"),
            ("decision", f"在{country}预算有限时，应该怎么选{product}？"),
            ("decision", f"{audience}购买{product}时，应该优先看什么？"),
            ("decision", f"什么情况下不该买{product}？"),
            ("decision", f"在{country}购买{product}之前，应该确认哪些条件？"),
            ("decision", f"一套适合{audience}的{product}通常包含什么？"),
            ("decision", f"怎样避免买到规格不合适的{product}？"),
            ("decision", f"现在给{audience}买{product}，哪些因素最影响决定？"),
            ("decision", f"如果只能选一个{product}方案，应该怎么筛选？"),
            ("verification", f"{brand}靠谱吗？有哪些缺点？"),
            ("verification", f"{brand}的{product}适合{audience}吗？"),
            ("verification", f"{brand}官网上的信息清楚吗？"),
            ("verification", f"{brand}在{country}能买到吗？"),
            ("verification", f"选择{brand}之前应该注意什么？"),
            ("verification", f"{brand}适合什么场景，不适合什么场景？"),
            ("verification", f"关于{brand}，常见的投诉或限制有哪些？"),
            ("verification", f"{brand}公开的{product}规格写了什么？"),
        ]
        if rival:
            templates.extend([
                ("comparison", f"{rival}和其他{product}有什么区别？"),
                ("comparison", f"{rival}适合什么人，不适合什么人？"),
                ("comparison", f"如果已经在看{rival}，还有哪些相近的选择？"),
                ("verification", f"{brand}和{rival}有什么区别？"),
            ])

    for stage, text in templates:
        if len(bank) >= limit:
            break
        _add(bank, text, stage, brand)

    for index, item in enumerate(bank, start=1):
        item["position"] = index
    return bank


def _rate(numerator, denominator):
    if not denominator:
        return None
    return numerator / denominator


def _client_flags(answer):
    flags = {"mentioned": False, "recommended": False, "negative": False}
    for brand in answer["brands"]:
        if brand["role"] == "client":
            flags = {
                "mentioned": brand["mentioned"],
                "recommended": brand["recommended"],
                "negative": brand["negative"],
            }
    return flags


def _competitor_flag(answer, name, field):
    for brand in answer["brands"]:
        if brand["role"] == "competitor" and brand["name"] == name:
            return brand[field]
    return False


def compute_metrics(answers):
    """Metrics for one channel. Answers already belong to that channel."""
    total = len(answers)
    unbranded = [item for item in answers if not item["branded"]]
    client_mentions = [item for item in unbranded if _client_flags(item)["mentioned"]]
    recommended = [item for item in answers if _client_flags(item)["recommended"]]
    negative = [item for item in answers if _client_flags(item)["negative"]]
    cited = [item for item in answers if item["cited_official"]]
    involved = [item for item in answers if _client_flags(item)["mentioned"] or item["branded"]]
    errors = [item for item in involved if item["factual_error"]]

    competitor_names = []
    for item in answers:
        for brand in item["brands"]:
            if brand["role"] == "competitor" and brand["name"] not in competitor_names:
                competitor_names.append(brand["name"])

    gaps = []
    client_rate = _rate(len(client_mentions), len(unbranded))
    for name in competitor_names:
        theirs = [item for item in unbranded if _competitor_flag(item, name, "mentioned")]
        their_rate = _rate(len(theirs), len(unbranded))
        gaps.append({
            "name": name,
            "num": len(theirs),
            "den": len(unbranded),
            "rate": their_rate,
            "client_rate": client_rate,
            "answer_ids": [item["id"] for item in theirs],
        })

    unstable = []
    grouped = {}
    for item in answers:
        grouped.setdefault(item["question_id"], []).append(_client_flags(item)["mentioned"])
    for question_id, mentions in grouped.items():
        if len(mentions) > 1 and len(set(mentions)) > 1:
            unstable.append(question_id)

    return {
        "total": total,
        "natural": {
            "num": len(client_mentions),
            "den": len(unbranded),
            "rate": _rate(len(client_mentions), len(unbranded)),
            "answer_ids": [item["id"] for item in client_mentions],
        },
        "recommended": {
            "num": len(recommended),
            "den": total,
            "rate": _rate(len(recommended), total),
            "answer_ids": [item["id"] for item in recommended],
        },
        "cited": {
            "num": len(cited),
            "den": total,
            "rate": _rate(len(cited), total),
            "answer_ids": [item["id"] for item in cited],
        },
        "errors": {
            "num": len(errors),
            "den": len(involved),
            "rate": _rate(len(errors), len(involved)),
            "answer_ids": [item["id"] for item in errors],
        },
        "negative": {
            "num": len(negative),
            "den": total,
            "answer_ids": [item["id"] for item in negative],
        },
        "gaps": gaps,
        "unstable_question_ids": unstable,
    }


def build_findings(answers, language="zh"):
    findings = []
    if not answers:
        return findings
    english = language == "en"

    errors = [item for item in answers if item["factual_error"] and (_client_flags(item)["mentioned"] or item["branded"])]
    if errors:
        count = len(errors)
        findings.append({
            "basis": "fact",
            "observation": (
                f"{count} answers involving the client brand were marked as factual errors."
                if english else
                f"有 {count} 条涉及客户品牌的回答被标为事实错误。"
            ),
            "action": (
                "Hypothesis: complete the official specification pages and make the numbers consistent. Whether the recommendation rate rises has to be retested with the same questions."
                if english else
                "假设：完善官方规格页，并统一各页面上的参数。补上之后推荐率是否上升，需要用同一组问题再测一次。"
            ),
            "answer_ids": [item["id"] for item in errors],
        })

    fit = [item for item in answers if item["stage"] == "fit" and not item["branded"]]
    missed = [item for item in fit if not _client_flags(item)["mentioned"]]
    if fit and len(missed) == len(fit):
        count = len(fit)
        findings.append({
            "basis": "fact",
            "observation": (
                f"All {count} unbranded need-match answers missed the client brand."
                if english else
                f"需求匹配类的 {count} 条无品牌回答都没有提到客户品牌。"
            ),
            "action": (
                "Hypothesis: add scenario pages that state the conditions and the limits. Whether that raises natural mention has to be retested."
                if english else
                "假设：补充对应使用场景页面，写明适用条件和限制。这是否提高自然提及，需要再测一次。"
            ),
            "answer_ids": [item["id"] for item in fit],
        })

    mentioned = [item for item in answers if _client_flags(item)["mentioned"] and not item["cited_official"]]
    if mentioned:
        count = len(mentioned)
        findings.append({
            "basis": "fact",
            "observation": (
                f"{count} answers mention the client brand and do not cite the client site."
                if english else
                f"有 {count} 条回答提到了客户品牌，但没有引用客户官网。"
            ),
            "action": (
                "Hypothesis: check whether those pages can be reached, indexed, and verified against the stated specifications and limits."
                if english else
                "假设：检查这些页面能否访问、能否被索引，以及规格和限制是否写得可以被核对。"
            ),
            "answer_ids": [item["id"] for item in mentioned],
        })

    rival_citations = []
    client_hosts = set()
    for item in answers:
        for citation in item["citations"]:
            if citation["is_client_site"]:
                client_hosts.add(citation["url"])
            elif citation["competitor_mentioned"]:
                rival_citations.append(item)
    rival_ids = []
    seen = set()
    for item in rival_citations:
        if item["id"] not in seen:
            seen.add(item["id"])
            rival_ids.append(item["id"])
    if rival_ids and not client_hosts:
        count = len(rival_ids)
        findings.append({
            "basis": "fact",
            "observation": (
                f"{count} answers cite an external source, mention a competitor, and do not cite the client site."
                if english else
                f"有 {count} 条回答引用了外部来源，并且同时提到竞争对手；这些回答没有引用客户官网。"
            ),
            "action": (
                "Hypothesis: look for real reviews and directory coverage. One set of answers cannot show that adding those sources would raise the recommendation rate."
                if english else
                "假设：寻找真实评测和行业目录里的曝光。不能从这一次回答断定补上来源就会提高推荐率。"
            ),
            "answer_ids": rival_ids,
        })
    return findings
