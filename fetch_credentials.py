#!/usr/bin/env python3
"""
Decrypt printer configuration data using AES-256-CBC

This script decrypts encrypted printer configuration data from a 3D printer using AES-256-CBC. 
The method was reverse engineered from the vue project embedded in libWorkbench.so, 
which is part of Anycubic Slicer Next. 
The decryption key is derived from the device token, 
and the IV is obtained from the response token in the encrypted data.

- Algorithm: AES-256-CBC
- Key: Characters 16-32 of the token from info.json
- IV: The response token from ctrl.json
- Mode: CBC with PKCS7 padding

Usage:
    python3 fetch_credentials.py --ip 192.168.2.32
    python3 fetch_credentials.py --ip 192.168.2.32 --port 18910
    python3 fetch_credentials.py --ctrl ctrl.json --info info.json --output config.json
"""

import json
import sys
import base64
import hashlib
import argparse
import time
import random
import string
import requests
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def evp_bytes_to_key(password, salt, key_len, iv_len):
    """
    Derive key and IV from password and salt using OpenSSL EVP_BytesToKey
    This mimics the CryptoJS default key derivation
    """
    m = []
    i = 0
    while len(b''.join(m)) < (key_len + iv_len):
        md5 = hashlib.md5()
        data = password + salt
        if i > 0:
            data = m[i - 1] + password + salt
        md5.update(data)
        m.append(md5.digest())
        i += 1
    ms = b''.join(m)
    return ms[:key_len], ms[key_len:key_len + iv_len]


def generate_signature(token, ts, nonce):
    """
    Generate MD5 signature for /ctrl endpoint
    Signature = md5(md5(token[0:16]) + ts + nonce)
    """
    # First MD5: token.slice(0, 16)
    first_md5 = hashlib.md5(token[:16].encode('utf-8')).hexdigest()
    # Second MD5: first_md5 + ts + nonce
    signature_data = first_md5 + str(ts) + nonce
    signature = hashlib.md5(signature_data.encode('utf-8')).hexdigest()
    return signature


def generate_nonce(length=6):
    """Generate a random alphanumeric nonce"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def fetch_from_http(ip, port, endpoint, token=None, did="random", verbose=False):
    """
    Fetch data from HTTP endpoint on the printer
    
    Args:
        ip (str): IP address of the printer
        port (int): Port number (default 18910)
        endpoint (str): Either 'info' or 'ctrl'
        token (str): Device token (required for /ctrl endpoint)
        did (str): Device ID (required for /ctrl endpoint)
        verbose (bool): Print debug information
    
    Returns:
        dict: JSON response data
    """
    try:
        if endpoint == 'info':
            url = f"http://{ip}:{port}/info"
            if verbose:
                print(f"Fetching: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        
        elif endpoint == 'ctrl':
            if not token:
                raise ValueError("Token is required for /ctrl endpoint")
            
            # Generate signature parameters
            ts = int(time.time() * 1000)  # Current timestamp in ms
            nonce = generate_nonce(6)
            signature = generate_signature(token, ts, nonce)
            
            url = f"http://{ip}:{port}/ctrl"
            params = {
                'ts': ts,
                'nonce': nonce,
                'sign': signature,
                'did': did
            }
            
            if verbose:
                print(f"Fetching: {url}")
                print(f"  Parameters:")
                print(f"    ts: {ts}")
                print(f"    nonce: {nonce}")
                print(f"    sign: {signature}")
                print(f"    did: {did}")
            
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        
        else:
            raise ValueError(f"Unknown endpoint: {endpoint}")
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"HTTP request failed for {endpoint}: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response from {endpoint}: {e}")


def decrypt_text(encrypted_data, key, iv):
    """
    Decrypt data using AES-256-CBC
    Handles CryptoJS-style encrypted data (OpenSSL format with salt)
    
    Args:
        encrypted_data (str): Encrypted data string (CryptoJS format)
        key (str): Decryption key string
        iv (str): Initialization vector string
    
    Returns:
        dict: Decrypted JSON data
    """
    try:
        # Convert key and IV to bytes
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        
        # Decrypt using direct key and IV (as per the original code)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        
        # The encrypted_data might be base64 or hex encoded
        # Try base64 first
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
        except:
            try:
                # Try as hex
                encrypted_bytes = bytes.fromhex(encrypted_data)
            except:
                # If all else fails, encode as UTF-8
                encrypted_bytes = encrypted_data.encode('utf-8')
        
        # Decrypt
        decrypted = cipher.decrypt(encrypted_bytes)
        
        # Try to unpad
        try:
            unpadded = unpad(decrypted, AES.block_size)
        except ValueError:
            # If unpadding fails, use as-is
            unpadded = decrypted
        
        plaintext = unpadded.decode('utf-8')
        
        # Parse JSON
        return json.loads(plaintext)
    
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


def main():
    """Main function to decrypt printer data"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Decrypt Anycubic printer configuration data',
    )
    # HTTP mode
    parser.add_argument('--ip', help='IP address of the printer (fetch via HTTP)')
    parser.add_argument('--port', type=int, default=18910, help='Printer port (default: 18910)')
    
    # File mode
    parser.add_argument('--ctrl', default='ctrl.json', help='Path to ctrl.json (default: ctrl.json)')
    parser.add_argument('--info', default='info.json', help='Path to info.json (default: info.json)')
    parser.add_argument('--output', default='decrypted_printer_config.json', help='Output file (default: decrypted_printer_config.json)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine mode: HTTP or file
    if args.ip:
        # HTTP mode: fetch from printer
        if args.verbose:
            print("=" * 70)
            print("Fetching configuration from printer via HTTP")
            print("=" * 70)
            print(f"Printer IP: {args.ip}:{args.port}")
            print()
        
        try:
            # Fetch info.json
            if args.verbose:
                print("Step 1: Fetching device info...")
            info = fetch_from_http(args.ip, args.port, 'info', verbose=args.verbose)
            
            # Get token from info
            token = info.get('token')
            if not token:
                print("Error: No token found in /info response", file=sys.stderr)
                return 1
            
            # Fetch data.json (encrypted config) from /ctrl endpoint
            if args.verbose:
                print("\nStep 2: Fetching encrypted configuration from /ctrl...")
            data = fetch_from_http(args.ip, args.port, 'ctrl', token=token, verbose=args.verbose)
            
            if args.verbose:
                print("\nData fetched successfully!")
            
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    else:
        # File mode: load from disk
        if args.verbose:
            print("=" * 70)
            print("Loading configuration from files")
            print("=" * 70)
        
        # Check if input files exist
        if not Path(args.ctrl).exists():
            print(f"Error: {args.ctrl} not found", file=sys.stderr)
            return 1
        if not Path(args.info).exists():
            print(f"Error: {args.info} not found", file=sys.stderr)
            return 1
        
        # Read data.json
        try:
            with open(args.data, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading {args.data}: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error reading {args.data}: {e}", file=sys.stderr)
            return 1
        
        # Read info.json
        try:
            with open(args.info, 'r') as f:
                info = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading {args.info}: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error reading {args.info}: {e}", file=sys.stderr)
            return 1
    
    # Extract values
    try:
        encrypted_info = data['data']['info']
        response_token = data['data']['token']
        full_token = info['token']
    except KeyError as e:
        print(f"Error: Missing required key {e}", file=sys.stderr)
        return 1
    
    # Generate decryption key and IV
    key_part = full_token[16:32]
    
    if args.verbose:
        print("=" * 70)
        print("Printer Configuration Decryption")
        print("=" * 70)
        print(f"Input data file: {args.ctrl}")
        print(f"Input info file: {args.info}")
        print(f"Output file: {args.output}")
        print()
        print("Decryption Parameters:")
        print(f"  Encrypted data length: {len(encrypted_info)} bytes")
        print(f"  Full token: {full_token}")
        print(f"  Full token length: {len(full_token)} characters")
        print(f"  Response token (IV): {response_token}")
        print(f"  Decryption key: {key_part}")
        print(f"  Key length: {len(key_part)} characters")
        print(f"  IV length: {len(response_token)} characters")
        print()
    
    # Decrypt
    if args.verbose:
        print("Decrypting...")
    
    result = decrypt_text(encrypted_info, key_part, response_token)
    
    if 'error' in result:
        print(f"Error during decryption: {result.get('error')}", file=sys.stderr)
        return 1
    
    # Pretty print result
    if args.verbose:
        print("=" * 70)
        print("Decrypted Configuration:")
        print("=" * 70)
        print(json.dumps(result, indent=2))
        print()
    
    # Save to file
    try:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        
        if args.verbose:
            print("=" * 70)
            print(f"Successfully saved decrypted config to: {args.output}")
            print("=" * 70)
        else:
            print(f"Decrypted config saved to: {args.output}")
    except Exception as e:
        print(f"Error writing to {args.output}: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
