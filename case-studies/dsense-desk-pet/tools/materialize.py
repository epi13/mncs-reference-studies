#!/usr/bin/env python3
"""Restore byte-identical dSense firmware and canonical evidence artifacts."""
from __future__ import annotations
import argparse, base64, hashlib, json, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ARTIFACTS=ROOT/'artifacts'
DEFAULT_OUTPUT=ROOT/'.materialized'
BASELINE_NAME='DeskPet_dSense_Interface_Telemetry_MNCS.ino'
TELEMETRY_NAME='DeskPet_dSense_UnoMax_Binary_MNCS.ino'
PRODUCTION_NAME='DeskPet_dSense_UnoMax_MNCS.ino'
EVIDENCE_NAME='epoch-1-canonical.json'
EXPECTED_SHA256={
 BASELINE_NAME:'3b55e368310f957d55588bd82afcbc905043e302634ef44ce478f2ced57abaca',
 TELEMETRY_NAME:'8c413fb12cc5ff3333175ff20ff5093b7cf98d297983b1472aa71ece53411808',
 PRODUCTION_NAME:'bcaa5bb03a3d7b86001d45f7890003f6d82a8e982ebdc38163a84baa460fa74e',
}
def decode_text_artifact(name:str)->bytes:
 parts=sorted(ARTIFACTS.glob(f'{name}.part*'))
 if not parts:
  path=ARTIFACTS/name
  if path.is_file(): parts=[path]
 if not parts: raise ValueError(f'no artifact parts found for {name}')
 encoded=''.join(token for part in parts for token in part.read_text(encoding='ascii').split())
 return zlib.decompress(base64.b85decode(encoded.encode('ascii')))
def apply_delta(base:bytes)->bytes:
 payload=json.loads(decode_text_artifact('firmware-v5-from-v4.delta.zlib.b85'))
 if hashlib.sha256(base).hexdigest()!=payload['base_sha256']: raise ValueError('delta base identity mismatch')
 lines=base.decode('utf-8').splitlines(True); out=[]; pos=0
 for i1,i2,text in payload['operations']:
  if i1<pos or i2<i1: raise ValueError('invalid delta ordering')
  out.extend(lines[pos:i1]); out.append(text); pos=i2
 out.extend(lines[pos:]); result=''.join(out).encode()
 if hashlib.sha256(result).hexdigest()!=payload['result_sha256']: raise ValueError('delta result identity mismatch')
 return result
def production_from_telemetry(source:bytes)->bytes:
 before=b'constexpr bool DEBUG_SERIAL = true;'; after=b'constexpr bool DEBUG_SERIAL = false;'
 if source.count(before)!=1: raise ValueError('telemetry source does not contain one DEBUG_SERIAL=true declaration')
 return source.replace(before,after,1)
def materialized_artifacts()->dict[str,bytes]:
 baseline=decode_text_artifact('baseline-v4.ino.zlib.b85')
 telemetry=apply_delta(baseline)
 return {BASELINE_NAME:baseline,TELEMETRY_NAME:telemetry,PRODUCTION_NAME:production_from_telemetry(telemetry),EVIDENCE_NAME:decode_text_artifact('epoch-1-canonical.json.zlib.b85')}
def verify_identity(name:str,content:bytes)->None:
 if name not in EXPECTED_SHA256:return
 actual=hashlib.sha256(content).hexdigest(); expected=EXPECTED_SHA256[name]
 if actual!=expected: raise ValueError(f'identity mismatch for {name}: {actual} != {expected}')
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);p.add_argument('--check',action='store_true');a=p.parse_args()
 artifacts=materialized_artifacts()
 for n,c in artifacts.items():verify_identity(n,c)
 if a.check: print('materialized artifact identities match');return 0
 a.output.mkdir(parents=True,exist_ok=True)
 for n,c in artifacts.items():(a.output/n).write_bytes(c);print(a.output/n)
 return 0
if __name__=='__main__':raise SystemExit(main())
