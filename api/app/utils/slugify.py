from slugify import slugify


def menu_slug(value: str, suffix: str | None = None) -> str:
    base = slugify(value)
    if suffix:
        return f"{base}-{slugify(suffix)}"
    return base
