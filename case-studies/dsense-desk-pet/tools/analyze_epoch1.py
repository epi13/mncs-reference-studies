#!/usr/bin/env python3
"""Reproduce the dSense epoch-1 findings from the canonical telemetry extract."""
from __future__ import annotations
import argparse, base64, hashlib, json, statistics, zlib
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT=ROOT/'evidence/results/epoch-1-analysis.json'
def decode_extract()->dict[str,Any]:
 path=ROOT/'artifacts/epoch-1-canonical.json.zlib.b85'
 encoded=''.join(path.read_text(encoding='ascii').split())
 return json.loads(zlib.decompress(base64.b85decode(encoded.encode('ascii'))))
def build_summary(extract:dict[str,Any])->dict[str,Any]:
 data=[{'ms':r[0],'events':r[1],'mic_env':r[2],'mic_ext':r[3],'mic_nf':r[4],'novelty':r[5]} for r in extract['data']]
 events=[{'ms':r[0],'code':r[1]} for r in extract['events']]
 markers=[{'host_elapsed_seconds':r[0],'label':r[1]} for r in extract['markers']]
 start_ms=int(data[0]['ms']);end_ms=int(data[-1]['ms']);duration=(end_ms-start_ms)/1000
 acoustic=[r for r in events if int(r['code'])==1];counter=int(data[-1]['events'])-int(data[0]['events'])
 def mean(rows,field):return statistics.fmean(float(r[field]) for r in rows)
 segments=[]
 for i,m in enumerate(markers):
  s=m['host_elapsed_seconds']*1000;e=markers[i+1]['host_elapsed_seconds']*1000 if i+1<len(markers) else float(end_ms)
  ds=[r for r in data if s<=float(r['ms'])<e];es=[r for r in acoustic if s<=float(r['ms'])<e]
  if not ds or e<=s:continue
  sec=(e-s)/1000
  segments.append({'label':m['label'],'duration_seconds':round(sec,3),'acoustic_events':len(es),'event_rate_hz':round(len(es)/sec,6),'mic_envelope_mean':round(mean(ds,'mic_env'),6),'mic_envelope_max':max(int(r['mic_env']) for r in ds),'external_energy_mean':round(mean(ds,'mic_ext'),6),'novelty_mean':round(mean(ds,'novelty'),6)})
 env=[int(r['mic_env']) for r in data];nf=[int(r['mic_nf']) for r in data];nov=[int(r['novelty']) for r in data]
 return {'schema_version':'1.0','study_id':'dsense.desk-pet.calibration.epoch-1','source':{'path':'artifacts/epoch-1-canonical.json.zlib.b85','original_capture_sha256':extract['source_capture_sha256'],'encoding':'canonical JSON + zlib + base85','telemetry_protocol':extract['source_telemetry_protocol']},'capture':{'device_ms_start':start_ms,'device_ms_end':end_ms,'duration_seconds':round(duration,3),'record_counts':extract['source_record_counts']},'observations':{'acoustic_event_records':len(acoustic),'acoustic_counter_delta':counter,'acoustic_event_rate_hz':round(counter/duration,6),'microphone_envelope':{'minimum':min(env),'maximum':max(env),'mean':round(statistics.fmean(env),6),'median':statistics.median(env)},'learned_noise_floor':{'minimum':min(nf),'maximum':max(nf),'mean':round(statistics.fmean(nf),6),'median':statistics.median(nf)},'novelty':{'minimum':min(nov),'maximum':max(nov),'mean':round(statistics.fmean(nov),6),'fraction_at_or_above_1000':round(sum(v>=1000 for v in nov)/len(nov),9)},'segments':segments},'derived_findings':['The acoustic detector retriggered at approximately its refractory limit across quiet, voice, desk-tap, and direct-contact segments.','The learned microphone noise floor remained fixed at four ADC-deviation units while the observed envelope stayed between 187 and 592.','Novelty was at or above 1000 for more than 99 percent of operating snapshots, so acoustic activity had saturated the cognitive signal.','Direct piezo contact was measurably stronger than the quiet baseline, showing usable dynamic range even though event classification failed.','The light-cover segment coincided with a persistent microphone rise, motivating ADC multiplexer settling and cross-channel isolation.'],'result':{'development_status':'FAIL','reason':'The epoch-1 detector did not distinguish quiet periods from intentional acoustic or mechanical stimuli.','formal_mncs_status':'UNKNOWN','formal_mncds_status':'UNKNOWN','promotion_authorized':False}}
def canonical_json(v):return json.dumps(v,indent=2,sort_keys=True)+'\n'
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);p.add_argument('--check',action='store_true');a=p.parse_args();rendered=canonical_json(build_summary(decode_extract()))
 if a.check:
  if not a.output.exists() or a.output.read_text()!=rendered:print(f'Evidence mismatch: regenerate {a.output}');return 1
  print('epoch-1 telemetry evidence matches the checked-in result');return 0
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered);print(a.output);return 0
if __name__=='__main__':raise SystemExit(main())
