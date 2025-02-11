import json
import uuid
from jwcrypto import jwk

# Define file names
KEY_FILE = "/tmp/client_key.pem"     # To store the private key (JWK format)
JWKS_FILE = "/tmp/jwks.json"   # To store the public key as a JWKS document


def generate_and_store_keys():
    # Generate a new RSA key (2048 bits)
    pkey = jwk.JWK.generate(kty='RSA', size=2048)

    # Export the private key (include private parts) as JSON
    pem_key = pkey.export_to_pem(private_key=True, password=None)
    with open(KEY_FILE, "wb") as f:
        f.write(pem_key)
    # Also, export the public key portion as a JWK dict
    public_jwk = pkey.export_public(as_dict=True)

    kid = uuid.uuid4().hex
    public_jwk['kid'] = kid
    public_jwk['alg'] = 'PS256'

    # Build a JWKS structure (a dict with a "keys" field)
    jwks = {"keys": [public_jwk]}
    with open(JWKS_FILE, "w") as f:
        json.dump(jwks, f)


if __name__ == '__main__':
    generate_and_store_keys()
