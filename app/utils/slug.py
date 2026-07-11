import re
import secrets


def slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "folder"


def unique_bucket_name(folder_name: str) -> str:
    """Supabase bucket names must be unique project-wide and are
    conventionally lowercase/hyphenated. Appending a short random suffix
    avoids collisions between folders that slugify to the same name (e.g.
    two folders both named "Invoices")."""
    return f"folder-{slugify(folder_name)}-{secrets.token_hex(3)}"
