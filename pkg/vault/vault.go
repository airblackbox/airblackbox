// Package vault provides encrypted, S3-compatible blob storage for
// prompt/response content. Content is AES-256-GCM encrypted before upload
// so data is protected at rest even if the storage backend is compromised.
package vault

import (
	"bytes"
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"io"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// Config holds S3-compatible storage configuration.
type Config struct {
	Endpoint      string
	AccessKey     string
	SecretKey     string
	Bucket        string
	UseSSL        bool
	EncryptionKey string // 32-byte hex key for AES-256-GCM (empty = no encryption)
}

// Client wraps an S3-compatible object store with optional AES-256-GCM encryption.
type Client struct {
	mc     *minio.Client
	bucket string
	gcm    cipher.AEAD // nil if encryption disabled
}

// Ref is a vault reference returned after storing content.
type Ref struct {
	URI       string // vault://bucket/key
	Checksum  string // sha256:hex (of plaintext, before encryption)
	Size      int64
	Encrypted bool // true if AES-256-GCM encrypted at rest
}

// New creates a vault client and ensures the bucket exists.
// If cfg.EncryptionKey is set, all stored data is AES-256-GCM encrypted.
func New(ctx context.Context, cfg Config) (*Client, error) {
	mc, err := minio.New(cfg.Endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
		Secure: cfg.UseSSL,
	})
	if err != nil {
		return nil, fmt.Errorf("vault: connect: %w", err)
	}

	exists, err := mc.BucketExists(ctx, cfg.Bucket)
	if err != nil {
		return nil, fmt.Errorf("vault: check bucket: %w", err)
	}
	if !exists {
		if err := mc.MakeBucket(ctx, cfg.Bucket, minio.MakeBucketOptions{}); err != nil {
			return nil, fmt.Errorf("vault: create bucket: %w", err)
		}
	}

	client := &Client{mc: mc, bucket: cfg.Bucket}

	// Initialize AES-256-GCM if encryption key is provided.
	if cfg.EncryptionKey != "" {
		gcm, err := newGCM(cfg.EncryptionKey)
		if err != nil {
			return nil, fmt.Errorf("vault: encryption init: %w", err)
		}
		client.gcm = gcm
	}

	return client, nil
}

// Store writes data to the vault and returns a reference with checksum.
// If encryption is configured, data is AES-256-GCM encrypted before upload.
// The checksum is computed on the plaintext so verification works after decryption.
func (c *Client) Store(ctx context.Context, key string, data []byte) (Ref, error) {
	// Checksum is always computed on plaintext.
	h := sha256.Sum256(data)
	checksum := fmt.Sprintf("sha256:%x", h)

	encrypted := false
	payload := data

	// Encrypt if AES-256-GCM is configured.
	if c.gcm != nil {
		var err error
		payload, err = encrypt(c.gcm, data)
		if err != nil {
			return Ref{}, fmt.Errorf("vault: encrypt %s: %w", key, err)
		}
		encrypted = true
	}

	info, err := c.mc.PutObject(ctx, c.bucket, key, bytes.NewReader(payload), int64(len(payload)),
		minio.PutObjectOptions{ContentType: "application/octet-stream"})
	if err != nil {
		return Ref{}, fmt.Errorf("vault: store %s: %w", key, err)
	}

	return Ref{
		URI:       fmt.Sprintf("vault://%s/%s", c.bucket, key),
		Checksum:  checksum,
		Size:      info.Size,
		Encrypted: encrypted,
	}, nil
}

// Fetch retrieves content from the vault by key.
// If encryption is configured, data is decrypted after download.
func (c *Client) Fetch(ctx context.Context, key string) ([]byte, error) {
	obj, err := c.mc.GetObject(ctx, c.bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("vault: fetch %s: %w", key, err)
	}
	defer obj.Close()

	raw, err := io.ReadAll(obj)
	if err != nil {
		return nil, fmt.Errorf("vault: read %s: %w", key, err)
	}

	// Decrypt if encryption is configured.
	if c.gcm != nil {
		decrypted, err := decrypt(c.gcm, raw)
		if err != nil {
			// Fall back to returning raw data for unencrypted legacy records.
			return raw, nil
		}
		return decrypted, nil
	}

	return raw, nil
}

// VerifyChecksum re-computes sha256 of data and compares against expected.
func VerifyChecksum(data []byte, expected string) bool {
	h := sha256.Sum256(data)
	got := fmt.Sprintf("sha256:%x", h)
	return got == expected
}

// --- AES-256-GCM helpers ---

// newGCM creates an AES-256-GCM cipher from a key string.
// The key is SHA-256 hashed to produce a fixed 32-byte key, so any
// length passphrase works.
func newGCM(keyStr string) (cipher.AEAD, error) {
	// Derive a 32-byte key via SHA-256 so any passphrase length works.
	h := sha256.Sum256([]byte(keyStr))
	block, err := aes.NewCipher(h[:])
	if err != nil {
		return nil, err
	}
	return cipher.NewGCM(block)
}

// encrypt encrypts plaintext with AES-256-GCM.
// Returns: nonce (12 bytes) || ciphertext || tag (16 bytes).
func encrypt(gcm cipher.AEAD, plaintext []byte) ([]byte, error) {
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("generate nonce: %w", err)
	}
	// Seal appends ciphertext+tag to nonce.
	return gcm.Seal(nonce, nonce, plaintext, nil), nil
}

// decrypt decrypts AES-256-GCM ciphertext.
// Expects: nonce (12 bytes) || ciphertext || tag (16 bytes).
func decrypt(gcm cipher.AEAD, ciphertext []byte) ([]byte, error) {
	nonceSize := gcm.NonceSize()
	if len(ciphertext) < nonceSize {
		return nil, fmt.Errorf("ciphertext too short")
	}
	nonce, ct := ciphertext[:nonceSize], ciphertext[nonceSize:]
	return gcm.Open(nil, nonce, ct, nil)
}
