package trajectory

import "encoding/hex"

// hexLeaf exposes the leaf hash of a step for the vector test.
func hexLeaf(s Step) string { return hex.EncodeToString(leafHash(s.canonical())) }
