import os
from services.omr_detection import process_omr_file


def get_score_for_question(q_num, is_correct, is_empty, is_multiple, scoring_rules):
    for rule in scoring_rules:
        if rule["from"] <= q_num <= rule["to"]:
            if is_empty or is_multiple:
                return float(rule.get("empty", 0))
            elif is_correct:
                return float(rule.get("correct", 1))
            else:
                return float(rule.get("wrong", 0))
    return 0.0


def compute_max_marks(scoring_rules, total_questions=40):
    if not scoring_rules:
        return float(total_questions)
    total = 0.0
    for q in range(1, total_questions + 1):
        for rule in scoring_rules:
            if rule["from"] <= q <= rule["to"]:
                total += float(rule.get("correct", 1))
                break
    return total


def process_single_file(filepath, key_dict, batch_id, scoring_rules_by_level=None):
    try:
        result = process_omr_file(filepath)

        if not result or "error" in result:
            return None

        answers = result.get("answers")
        if not isinstance(answers, dict):
            answers = {}

        DEFAULT_LEVEL = "intermediate"

        raw_level = result.get("level")
        detected_level = raw_level.strip().lower()
        level = DEFAULT_LEVEL

        scoring_rules = None
        if scoring_rules_by_level and isinstance(scoring_rules_by_level, dict):
            scoring_rules = (
                scoring_rules_by_level.get(level) or
                scoring_rules_by_level.get(level.replace("_", " "))
            )

        if not scoring_rules:
            scoring_rules = [{"from": 1, "to": 40, "correct": 1, "wrong": 0, "empty": 0}]

        answers_json = {}
        verify_json = {}
        final_answers = []

        total_score = 0.0
        correct_count = 0
        wrong_count = 0
        empty_count = 0

        for q, ans in answers.items():
            try:
                q_num = int(str(q).replace("Q", "").strip())
            except (ValueError, AttributeError):
                continue

            if q_num < 1 or q_num > 40:
                continue

            q_no = f"Q{str(q_num).zfill(2)}"

            correct_raw = (
                key_dict.get((level, q_num)) or
                key_dict.get((level.replace("_", " "), q_num))
            )

            try:
                ans = str(ans).strip().upper() if ans not in [None, "", "-"] else ans
            except Exception:
                ans = None

            correct = str(correct_raw).strip().upper() if correct_raw not in [None, ""] else None

            is_empty = ans in [None, "-", "", "Empty"]
            is_multiple = not is_empty and isinstance(ans, str) and "&" in ans

            if is_empty:
                selected = "Empty"
                is_correct = False
                empty_count += 1
            elif is_multiple:
                selected = "Multiple"
                is_correct = False
                wrong_count += 1
            else:
                selected = ans
                is_correct = (ans == correct) if correct is not None else False
                if is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1

            score = get_score_for_question(q_num, is_correct, is_empty, is_multiple, scoring_rules)
            total_score += score

            answers_json[q_no] = selected
            verify_json[q_no] = {
                "selected": selected,
                "correct": correct,
                "is_correct": is_correct,
                "score": score,
            }
            final_answers.append({
                "question": q_no,
                "value": selected,
                "correct_answer": correct,
                "is_correct": is_correct,
                "score": score,
            })

        max_marks = compute_max_marks(scoring_rules)
        percentage = round((total_score / max_marks) * 100, 2) if max_marks else 0

        return {
            "db_data": {
                "name": result.get("name") or "",
                "level": detected_level,
                "centre_number": result.get("centre_number") or "",
                "dob": result.get("dob") or "",
                "answers": answers_json,
                "verify_ans": verify_json,
                "score": round(total_score, 2),
                "batch_id": batch_id,
                "file_name": os.path.basename(filepath),
            },
            "row_data": {
                "name": result.get("name") or "",
                "centre_number": result.get("centre_number") or "",
                "level": detected_level,
                "answers": final_answers,
                "dob": result.get("dob") or "",
                "total_score": round(total_score, 2),
                "percentage": percentage,
                "correct": correct_count,
                "wrong": wrong_count,
                "empty": empty_count,
            },
        }

    except Exception as e:
        print(f"Worker Error [{filepath}]: {e}")
        return None