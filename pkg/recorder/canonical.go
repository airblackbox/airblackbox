package recorder

import (
	"bytes"
	"encoding/json"
	"fmt"
	"sort"
	"unicode/utf16"
)

// canonicalPythonJSON serializes a JSON document exactly as Python's
// json.dumps(value, sort_keys=True) would after the document has been parsed
// by json.loads. This is what makes AIR record chain hashes verifiable by the
// Python SDK: the verifier re-serializes the parsed record and recomputes the
// HMAC, so the writer must hash byte-identical output.
//
// Matched behaviors: sorted keys, ", " and ": " separators, ensure_ascii
// escaping (non-ASCII as lowercase \uXXXX, astral chars as surrogate pairs),
// short escapes for \b \t \n \f \r, and integer preservation via json.Number.
func canonicalPythonJSON(data []byte) ([]byte, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	var v interface{}
	if err := dec.Decode(&v); err != nil {
		return nil, fmt.Errorf("canonical: parse: %w", err)
	}

	return canonicalValue(v)
}

// canonicalValue serializes an already-parsed JSON value (maps, slices,
// json.Number, string, bool, nil) in Python's canonical form.
func canonicalValue(v interface{}) ([]byte, error) {
	var buf bytes.Buffer
	if err := writeCanonical(&buf, v); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func writeCanonical(buf *bytes.Buffer, v interface{}) error {
	switch val := v.(type) {
	case nil:
		buf.WriteString("null")
	case bool:
		if val {
			buf.WriteString("true")
		} else {
			buf.WriteString("false")
		}
	case json.Number:
		// Emit the number exactly as it appeared in the source JSON; both
		// sides round-trip integers and short decimals unchanged.
		buf.WriteString(string(val))
	case string:
		writePythonString(buf, val)
	case []interface{}:
		buf.WriteByte('[')
		for i, item := range val {
			if i > 0 {
				buf.WriteString(", ")
			}
			if err := writeCanonical(buf, item); err != nil {
				return err
			}
		}
		buf.WriteByte(']')
	case map[string]interface{}:
		keys := make([]string, 0, len(val))
		for k := range val {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		buf.WriteByte('{')
		for i, k := range keys {
			if i > 0 {
				buf.WriteString(", ")
			}
			writePythonString(buf, k)
			buf.WriteString(": ")
			if err := writeCanonical(buf, val[k]); err != nil {
				return err
			}
		}
		buf.WriteByte('}')
	default:
		return fmt.Errorf("canonical: unsupported type %T", v)
	}
	return nil
}

// writePythonString escapes a string the way Python's json.dumps does with
// its default ensure_ascii=True.
func writePythonString(buf *bytes.Buffer, s string) {
	buf.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"':
			buf.WriteString(`\"`)
		case '\\':
			buf.WriteString(`\\`)
		case '\b':
			buf.WriteString(`\b`)
		case '\t':
			buf.WriteString(`\t`)
		case '\n':
			buf.WriteString(`\n`)
		case '\f':
			buf.WriteString(`\f`)
		case '\r':
			buf.WriteString(`\r`)
		default:
			switch {
			case r < 0x20:
				fmt.Fprintf(buf, `\u%04x`, r)
			case r < 0x7f:
				buf.WriteRune(r)
			case r > 0xFFFF:
				hi, lo := utf16.EncodeRune(r)
				fmt.Fprintf(buf, `\u%04x\u%04x`, hi, lo)
			default:
				fmt.Fprintf(buf, `\u%04x`, r)
			}
		}
	}
	buf.WriteByte('"')
}
