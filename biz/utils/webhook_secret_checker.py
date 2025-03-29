import hashlib
import hmac
from http.client import HTTPException


# from https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries#python-example
def verify_github_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    # 仅当设置了环境变量时才验证秘密令牌
    if not secret_token:
        return True
    if not signature_header:
        raise HTTPException(status_code=403, detail="x-hub-signature-256 header is missing!")
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Request signatures didn't match!")
    return True


def verify_gitlab_webhook_secret_token(secret_token_env, secret_token_request):
    # 仅当设置了环境变量时才验证秘密令牌
    if secret_token_env:
        if secret_token_env != secret_token_request:
            return False
    return True
