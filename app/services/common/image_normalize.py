def normalize_image_paths(paths: list[str | None] | None, single_path: str | None = None) -> list[str]:
    result: list[str] = []
    if paths:
        for item in paths:
            if not item:
                continue
            stripped = item.strip()
            if stripped and stripped not in result:
                result.append(stripped)
    if single_path and single_path.strip():
        stripped = single_path.strip()
        if stripped not in result:
            result.append(stripped)
    return result


def normalize_match_mode(match_mode: str | None) -> str:
    value = (match_mode or 'or').strip().lower()
    if value in {'and', 'all', '和'}:
        return 'and'
    if value in {'or', 'any', '或'}:
        return 'or'
    raise ValueError(f'matchMode仅支持 or/any/或 或 and/all/和，当前值: {match_mode}')
