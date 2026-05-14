def validate_scoring_rules(rules, total_questions=40):
    errors = {
        "overlaps": [],
        "missing_ranges": [],
        "invalid_ranges": []
    }

    normalized = []

    for index, rule in enumerate(rules):
        start = int(rule["start_question"])
        end = int(rule["end_question"])

        if start < 1 or end > total_questions or start > end:
            errors["invalid_ranges"].append({
                "index": index,
                "start": start,
                "end": end
            })

        normalized.append({
            "index": index,
            "start": start,
            "end": end
        })

    normalized.sort(key=lambda x: x["start"])

    # overlap detection
    for i in range(1, len(normalized)):
        prev = normalized[i - 1]
        curr = normalized[i]

        if curr["start"] <= prev["end"]:
            errors["overlaps"].append({
                "rule1": prev["index"],
                "rule2": curr["index"]
            })

    # gap detection
    expected = 1

    for rule in normalized:
        if rule["start"] > expected:
            errors["missing_ranges"].append({
                "start": expected,
                "end": rule["start"] - 1
            })

        expected = max(expected, rule["end"] + 1)

    if expected <= total_questions:
        errors["missing_ranges"].append({
            "start": expected,
            "end": total_questions
        })

    return errors