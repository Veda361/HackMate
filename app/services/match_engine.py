def calculate_match(skills1: str, skills2: str):
    """
    Advanced matching algorithm:
    - Case insensitive
    - Removes duplicates
    - Supports partial matches
    - Weighted scoring
    """

    if not skills1 or not skills2:
        return 0

    # 🔹 Normalize skills
    set1 = set(skill.strip().lower() for skill in skills1.split(",") if skill.strip())
    set2 = set(skill.strip().lower() for skill in skills2.split(",") if skill.strip())

    if not set1 or not set2:
        return 0

    # 🔹 Exact matches
    exact_matches = set1.intersection(set2)

    # 🔹 Partial matches (e.g. "react" vs "reactjs")
    partial_matches = set()
    for s1 in set1:
        for s2 in set2:
            if s1 in s2 or s2 in s1:
                partial_matches.add((s1, s2))

    # 🔹 Score calculation
    exact_score = len(exact_matches) * 2       # weight = 2
    partial_score = len(partial_matches) * 1   # weight = 1

    total_possible = max(len(set1), len(set2)) * 2

    final_score = (exact_score + partial_score) / total_possible

    return round(final_score * 100)