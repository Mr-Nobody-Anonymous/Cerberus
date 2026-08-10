# Cryptographic Algorithms Quick Reference

## Algorithm Status Guide

### Legend
- ✅ **Recommended**: Use in new deployments
- ⚠️ **Transitional**: Plan to migrate away
- ❌ **Deprecated**: Do not use for new systems
- 🔮 **Post-Quantum**: Quantum-resistant

## Symmetric Encryption

### Block Ciphers

| Algorithm | Key Size | Status | Notes |
|-----------|----------|--------|-------|
| AES-256 | 256-bit | ✅ | Industry standard, hardware accelerated |
| AES-192 | 192-bit | ✅ | Good balance of security and performance |
| AES-128 | 128-bit | ⚠️ | Quantum vulnerable (64-bit effective security) |
| ChaCha20 | 256-bit | ✅ | Excellent for software-only implementations |
| 3DES | 168-bit | ❌ | Deprecated, only for legacy systems |
| DES | 56-bit | ❌ | Broken, never use |
| Blowfish | Variable | ⚠️ | Legacy, prefer AES |
| Twofish | Variable | ✅ | Alternative to AES |

### Modes of Operation

| Mode | Use Case | Status | Security |
|------|----------|--------|----------|
| GCM (Galois/Counter) | Authenticated encryption | ✅ | High - provides confidentiality and integrity |
| CCM (Counter with CBC-MAC) | Constrained environments | ✅ | High - similar to GCM |
| ChaCha20-Poly1305 | Modern AEAD | ✅ | High - authenticated encryption |
| CTR (Counter) | Parallelizable encryption | ⚠️ | Medium - requires authentication |
| CBC (Cipher Block Chaining) | Legacy systems | ⚠️ | Medium - padding oracle attacks possible |
| ECB (Electronic Codebook) | Never | ❌ | Low - reveals patterns, never use |

**Recommendation**: Use authenticated encryption (AEAD) modes: GCM, CCM, or ChaCha20-Poly1305.

## Hash Functions

### Cryptographic Hashes

| Algorithm | Output Size | Status | Notes |
|-----------|-------------|--------|-------|
| SHA-512 | 512-bit | ✅ | Recommended for new systems |
| SHA-384 | 384-bit | ✅ | Truncated SHA-512 |
| SHA-256 | 256-bit | ✅ | Minimum recommended |
| SHA-3-512 | 512-bit | ✅ | Alternative to SHA-2 |
| SHA-3-256 | 256-bit | ✅ | Alternative to SHA-2 |
| BLAKE3 | Variable | ✅ | Very fast, modern |
| BLAKE2 | Variable | ✅ | Fast alternative to SHA-2 |
| SHA-1 | 160-bit | ❌ | Broken, collision attacks |
| MD5 | 128-bit | ❌ | Broken, never use |

**Quantum Note**: Double hash output size for post-quantum security (SHA-256 → SHA-512)

### Password Hashing (KDF)

| Algorithm | Status | Parameters | Notes |
|-----------|--------|------------|-------|
| Argon2id | ✅ | Memory, iterations, parallelism | PHC winner, best choice |
| Argon2i | ✅ | Memory, iterations, parallelism | Side-channel resistant |
| scrypt | ✅ | N, r, p | Memory-hard function |
| bcrypt | ⚠️ | Cost factor | Good, but limited to 72 bytes |
| PBKDF2 | ⚠️ | Iterations | Widely supported, but weaker |

**Recommended Settings**:
- Argon2id: memory=64MB, iterations=3, parallelism=4
- scrypt: N=2^15, r=8, p=1
- bcrypt: cost=12

## Public Key Cryptography

### Key Exchange / Encryption

| Algorithm | Key Size | Status | Notes |
|-----------|----------|--------|-------|
| ML-KEM-768 (Kyber) | N/A | 🔮 ✅ | NIST PQC standard (FIPS 203) |
| ML-KEM-1024 (Kyber) | N/A | 🔮 ✅ | Higher security |
| ECDH (X25519) | 256-bit | ⚠️ | Quantum vulnerable, use in hybrid |
| ECDH (P-256) | 256-bit | ⚠️ | Quantum vulnerable, use in hybrid |
| ECDH (P-384) | 384-bit | ⚠️ | Quantum vulnerable, use in hybrid |
| RSA | 3072-bit | ⚠️ | Quantum vulnerable, migrate |
| RSA | 2048-bit | ❌ | Too weak, deprecated |
| DH | 3072-bit | ⚠️ | Quantum vulnerable, migrate |

### Digital Signatures

| Algorithm | Key Size | Status | Notes |
|-----------|----------|--------|-------|
| ML-DSA-65 (Dilithium) | N/A | 🔮 ✅ | NIST PQC standard (FIPS 204) |
| SLH-DSA (SPHINCS+) | N/A | 🔮 ✅ | Hash-based, conservative (FIPS 205) |
| FALCON | N/A | 🔮 ✅ | Compact signatures, selected for standardization |
| Ed25519 | 256-bit | ⚠️ | Quantum vulnerable, use in hybrid |
| ECDSA P-256 | 256-bit | ⚠️ | Quantum vulnerable, migrate |
| ECDSA P-384 | 384-bit | ⚠️ | Quantum vulnerable, migrate |
| RSA-PSS | 3072-bit | ⚠️ | Quantum vulnerable, migrate |
| RSA-PKCS#1 v1.5 | 3072-bit | ⚠️ | Legacy, prefer RSA-PSS |
| DSA | 3072-bit | ❌ | Deprecated |

## Post-Quantum Cryptography (PQC)

### NIST Selected Algorithms

#### Key Encapsulation Mechanisms (KEM)

| Algorithm | Type | Security Level | Public Key | Ciphertext | Status |
|-----------|------|----------------|------------|------------|--------|
| ML-KEM-512 (Kyber512) | Lattice | AES-128 | 800 B | 768 B | ✅ |
| ML-KEM-768 (Kyber768) | Lattice | AES-192 | 1184 B | 1088 B | ✅ Recommended |
| ML-KEM-1024 (Kyber1024) | Lattice | AES-256 | 1568 B | 1568 B | ✅ |

#### Digital Signatures

| Algorithm | Type | Security Level | Public Key | Signature | Sign Speed |
|-----------|------|----------------|------------|-----------|------------|
| ML-DSA-44 (Dilithium2) | Lattice | AES-128 | 1312 B | 2420 B | Fast |
| ML-DSA-65 (Dilithium3) | Lattice | AES-192 | 1952 B | 3293 B | Fast ✅ |
| ML-DSA-87 (Dilithium5) | Lattice | AES-256 | 2592 B | 4595 B | Fast |
| SLH-DSA-128s | Hash | AES-128 | 32 B | 7856 B | Slow |
| SLH-DSA-128f | Hash | AES-128 | 32 B | 17088 B | Very Slow |
| FALCON-512 | Lattice | AES-128 | 897 B | 666 B | Fast |
| FALCON-1024 | Lattice | AES-256 | 1793 B | 1280 B | Fast |

### Hybrid Approaches

Combine classical and post-quantum algorithms for defense-in-depth:

| Hybrid Scheme | Components | Status |
|---------------|------------|--------|
| X25519Kyber768 | X25519 + ML-KEM-768 | ✅ Recommended |
| ECDSA+Dilithium | ECDSA P-256 + ML-DSA-65 | ✅ Recommended |
| RSA+SPHINCS+ | RSA-3072 + SLH-DSA | ✅ Conservative |

## MAC (Message Authentication Codes)

| Algorithm | Based On | Status | Notes |
|-----------|----------|--------|-------|
| HMAC-SHA256 | SHA-256 | ✅ | Standard choice |
| HMAC-SHA512 | SHA-512 | ✅ | Higher security |
| HMAC-SHA3 | SHA-3 | ✅ | Alternative to SHA-2 |
| Poly1305 | ChaCha20 | ✅ | Used with ChaCha20 |
| CMAC-AES | AES | ✅ | Block cipher based |
| HMAC-SHA1 | SHA-1 | ❌ | Deprecated |
| HMAC-MD5 | MD5 | ❌ | Never use |

## Key Sizes and Security Levels

### Security Levels (Bits)

| Security Level | Symmetric | Hash Output | RSA | ECC | Post-Quantum |
|----------------|-----------|-------------|-----|-----|--------------|
| 128-bit | AES-128 | SHA-256 | 3072 | 256 | ML-KEM-512, ML-DSA-44 |
| 192-bit | AES-192 | SHA-384 | 7680 | 384 | ML-KEM-768, ML-DSA-65 |
| 256-bit | AES-256 | SHA-512 | 15360 | 521 | ML-KEM-1024, ML-DSA-87 |

### Quantum Impact on Security Levels

| Classical | Grover's Algorithm | Effective Quantum Security |
|-----------|-------------------|----------------------------|
| AES-128 | Yes | 64-bit (Insecure) |
| AES-256 | Yes | 128-bit (Secure) |
| SHA-256 | Yes | 128-bit collision resistance |
| RSA-3072 | Shor's Algorithm | Broken |
| ECC-256 | Shor's Algorithm | Broken |

**Recommendation**: Use AES-256 minimum, SHA-512 minimum for post-quantum security.

## Algorithm Selection Guide

### For TLS 1.3 (Current)

**Key Exchange**:
- ✅ X25519 (hybrid with ML-KEM-768 when available)
- ✅ P-256 (hybrid with ML-KEM-768 when available)

**Ciphers**:
- ✅ AES-256-GCM
- ✅ AES-128-GCM
- ✅ ChaCha20-Poly1305

**Signatures**:
- ✅ ECDSA P-256 (hybrid with ML-DSA when available)
- ⚠️ RSA-PSS (plan migration)

### For New Protocols (Future-Proof)

**Key Exchange**:
- 🔮 ML-KEM-768 standalone or hybrid

**Ciphers**:
- ✅ AES-256-GCM
- ✅ ChaCha20-Poly1305

**Signatures**:
- 🔮 ML-DSA-65 or FALCON-1024

**Hash**:
- ✅ SHA-512 or BLAKE3

### For Passwords

**Always use a proper KDF**:
1. ✅ Argon2id (best choice)
2. ✅ scrypt
3. ⚠️ bcrypt (acceptable)
4. ❌ Never use plain hash (SHA-256, MD5, etc.)

### For Signatures

**Document Signing**:
- ✅ RSA-PSS 3072-bit + SHA-256 (current)
- 🔮 ML-DSA-65 or FALCON-1024 (future)

**Code Signing**:
- ✅ RSA 3072-bit + SHA-256 (current)
- 🔮 Hybrid: RSA + ML-DSA-65 (transition)
- 🔮 ML-DSA-65 (future)

**Certificate Signatures**:
- ✅ ECDSA P-256 + SHA-256 (current)
- 🔮 Hybrid: ECDSA + ML-DSA (transition)
- 🔮 ML-DSA-65 (future)

## Migration Timeline

### 2025-2026 (NOW)
- Begin PQC testing
- Deploy hybrid solutions
- Inventory cryptographic assets

### 2027-2028
- Migrate high-priority systems to PQC
- Support hybrid mode widely
- Begin deprecating RSA/ECC

### 2029-2030
- Complete migration to PQC
- Deprecate classical algorithms
- Full post-quantum infrastructure

### 2035+
- Only PQC in use
- Monitor for new threats
- Stay current with standards

## Quick Decision Tree

```
Need encryption?
├─ Data at rest? → AES-256-GCM
├─ Data in transit? → TLS 1.3 (AES-256-GCM or ChaCha20-Poly1305)
└─ Passwords? → Argon2id

Need key exchange?
├─ Current? → ECDH X25519
└─ Future-proof? → ML-KEM-768 or hybrid

Need signatures?
├─ Current? → ECDSA P-256 or RSA-PSS 3072
└─ Future-proof? → ML-DSA-65 or hybrid

Need hashing?
├─ General purpose? → SHA-256 (min), SHA-512 (recommended)
├─ Passwords? → Argon2id
└─ Fast hashing? → BLAKE3
```

## See Also
- [NIST Post-Quantum Cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [RFC 8439 - ChaCha20 and Poly1305](https://tools.ietf.org/html/rfc8439)
- [RFC 9180 - Hybrid Public Key Encryption](https://www.rfc-editor.org/rfc/rfc9180.html)

