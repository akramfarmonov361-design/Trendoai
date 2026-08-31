
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64
from utils.logger import setup_logger
logger = setup_logger("generate_vapid")


def to_base64url(data):
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

# Generate keys
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Private Key (PEM)
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Public Key (Uncompressed Point for VAPID)
public_numbers = public_key.public_numbers()
x = public_numbers.x.to_bytes(32, byteorder='big')
y = public_numbers.y.to_bytes(32, byteorder='big')
# 0x04 prefix for uncompressed
public_bytes = b'\x04' + x + y
public_b64 = to_base64url(public_bytes)

logger.info("---------- VAPID KEYS ----------")
logger.info(f"VAPID_PUBLIC_KEY={public_b64}")
logger.info(f"VAPID_PRIVATE_KEY={private_pem.decode('utf-8').replace(chr(10), '')}") # Oneline for .env
logger.info("--------------------------------")

# Save detailed private key to file
with open("vapid_private.pem", "wb") as f:
    f.write(private_pem)

with open("vapid_public.txt", "w") as f:
    f.write(public_b64)
