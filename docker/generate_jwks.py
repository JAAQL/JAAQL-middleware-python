import json
import uuid
from jwcrypto import jwk

# Define file names
KEY_FILE = "/tmp/client_key.pem"     # To store the private key (JWK format)
ENCRYPTION_KEY_FILE = "/tmp/client_encryption_key.pem"
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
    public_jwk['use'] = 'sig'

    encryption_key = jwk.JWK.generate(kty='RSA', size=2048)
    # Export the private encryption key (PEM format) and save it (for your use)
    pem_encryption = encryption_key.export_to_pem(private_key=True, password=None)
    with open(ENCRYPTION_KEY_FILE, "wb") as f:
        f.write(pem_encryption)
    # Export the public portion as a JWK dictionary
    public_encryption = encryption_key.export_public(as_dict=True)
    # Generate a unique key ID for the encryption key
    kid_encryption = uuid.uuid4().hex
    public_encryption['kid'] = kid_encryption
    public_encryption['alg'] = 'RSA-OAEP-256'  # Key management algorithm for encryption
    public_encryption['use'] = 'enc'  # Key usage: encryption

    # Build a JWKS structure (a dict with a "keys" field)
    jwks = {"keys": [public_jwk, public_encryption]}
    with open(JWKS_FILE, "w") as f:
        json.dump(jwks, f)


if __name__ == '__main__':
    generate_and_store_keys()
