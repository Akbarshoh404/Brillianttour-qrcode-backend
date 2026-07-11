from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """Resolve the real client IP, honoring reverse-proxy forwarding headers."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else None


def get_primary_language(request: Request) -> str | None:
    """First language tag from the Accept-Language header, e.g. 'en-US'."""
    accept_language = request.headers.get("accept-language")
    if not accept_language:
        return None
    return accept_language.split(",")[0].split(";")[0].strip() or None
