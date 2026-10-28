#!/usr/bin/env python3
"""Offline, explicitly confirmed import of reviewed external feedback. No transcription or PII detector."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from functools import lru_cache
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

from lint_records import validate_claims

SCHEMAS = Path(__file__).resolve().parents[1] / 'schemas'
FILES = ('claims', 'sources', 'decisions', 'events')
MAX_BYTES = 20 * 1024 * 1024
LOCK = '.feedback-import.lock'
HUMAN = re.compile(r'\b(ki|ai|llm|gpt|chatgpt|claude|gemini|copilot|chatbot|bot|agent|assistant|assistent|model|modell)\b', re.I)
PREDICATES = {'customer_language', 'objection', 'pain_point', 'request'}
GENERATION = re.compile(r'gen-[a-f0-9]{32}')
LIBRARIES = {'.business-dna', '.suite', '.branding', '.nocrm', '.help', '.marketing',
             '.analytics', '.advertising', '.creative', '.e-commerce', '.social-media', '.nocms'}


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reject_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key] = item
    return value


def parse(data):
    return json.loads(data, object_pairs_hook=reject_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def read_bytes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or symlinked input')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Input exceeds size limit')
    return data


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Zoned timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Zoned timestamp required')
    return result


def now_string(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def shape(value, spec):
    """Bounded local schema checks for the bundled simple records, not a general JSON Schema engine."""
    if '$ref' in spec:
        reference = spec['$ref']
        if reference not in ('claim.schema.json', 'source.schema.json'):
            raise ValueError('Unsupported local schema reference')
        shape(value, record_schema(reference[:-len('.schema.json')]))
        return
    types = spec.get('type', [])
    types = [types] if isinstance(types, str) else types
    matches = {'object': isinstance(value, dict), 'array': isinstance(value, list),
               'string': isinstance(value, str), 'integer': type(value) is int,
               'boolean': type(value) is bool, 'null': value is None}
    if types and not any(matches.get(kind, False) for kind in types):
        raise ValueError('Invalid record field type')
    if 'const' in spec and value != spec['const']:
        raise ValueError('Invalid constant')
    if 'enum' in spec and value not in spec['enum']:
        raise ValueError('Invalid record enum')
    if isinstance(value, str):
        if not spec.get('minLength', 0) <= len(value) <= spec.get('maxLength', MAX_BYTES):
            raise ValueError('Invalid text length')
        if spec.get('minLength') and not value.strip():
            raise ValueError('Blank field')
        if 'pattern' in spec and re.fullmatch(spec['pattern'], value) is None:
            raise ValueError('Invalid record pattern')
        if spec.get('format') == 'date-time':
            timestamp(value)
        if spec.get('format') == 'date' and date.fromisoformat(value).isoformat() != value:
            raise ValueError('Invalid date')
    if type(value) is int and value < spec.get('minimum', value):
        raise ValueError('Integer below minimum')
    if isinstance(value, list):
        if not spec.get('minItems', 0) <= len(value) <= spec.get('maxItems', MAX_BYTES):
            raise ValueError('Invalid list length')
        if spec.get('uniqueItems') and len({sha(canonical(item)) for item in value}) != len(value):
            raise ValueError('Duplicate list item')
        for item in value:
            shape(item, spec.get('items', {}))
    if isinstance(value, dict):
        if not set(spec.get('required', [])) <= set(value):
            raise ValueError('Required record field missing')
        properties = spec.get('properties', {})
        for key, item in value.items():
            if key in properties:
                shape(item, properties[key])
            elif spec.get('additionalProperties') is False:
                raise ValueError('Unexpected record field')
            elif isinstance(spec.get('additionalProperties'), dict):
                shape(item, spec['additionalProperties'])


@lru_cache(maxsize=8)
def record_schema(kind):
    return parse((SCHEMAS / (kind + '.schema.json')).read_bytes())


def validate_record(record, kind):
    shape(record, record_schema(kind))


def check_state(state):
    for collection, kind, key in (('claims', 'claim', 'claim_id'), ('sources', 'source', 'source_id'),
                                  ('decisions', 'decision', 'decision_id'), ('events', 'event', 'event_id')):
        ids = set()
        for record in state[collection]:
            validate_record(record, kind)
            if record[key] in ids:
                raise ValueError('Duplicate record ID in store')
            ids.add(record[key])
    errors = validate_claims(state['claims'], state['sources'])
    if errors:
        raise ValueError('Invalid claim/source references in store')


def store_path(store):
    path = Path(store)
    if path.is_symlink() or (path.exists() and not path.is_dir()) or LIBRARIES.intersection(path.resolve().parts):
        raise ValueError('Store must be outside the methods library and not a symlink')
    return path.resolve()


def read_store(store, allow_empty=False, locked=False):
    root = store_path(store)
    if any((root / (name + '.jsonl')).is_symlink() for name in FILES):
        raise ValueError('Symlinked legacy records')
    if not locked and ((root / LOCK).exists() or (root / LOCK).is_symlink()):
        raise ValueError('Store is locked; inspect interrupted imports before retrying')
    pointer = root / 'CURRENT.json'
    reference = None
    if pointer.exists() or pointer.is_symlink():
        reference = parse(read_bytes(pointer))
        if (not isinstance(reference, dict) or set(reference) != {'generation', 'manifest_sha256'}
                or not isinstance(reference['generation'], str)
                or GENERATION.fullmatch(reference['generation']) is None):
            raise ValueError('Invalid store pointer')
        generations = root / 'generations'
        directory = generations / reference['generation']
        if generations.is_symlink() or directory.is_symlink():
            raise ValueError('Symlinked generation')
        manifest_bytes = read_bytes(directory / 'manifest.json')
        if sha(manifest_bytes) != reference['manifest_sha256']:
            raise ValueError('Changed generation manifest')
        manifest = parse(manifest_bytes)
        if not isinstance(manifest, dict):
            raise ValueError('Invalid generation manifest')
        if set(manifest.get('files', {})) != {name + '.jsonl' for name in FILES}:
            raise ValueError('Incomplete generation')
        state = {}
        for name in FILES:
            data = read_bytes(directory / (name + '.jsonl'))
            if sha(data) != manifest['files'][name + '.jsonl']:
                raise ValueError('Changed generation data')
            state[name] = [parse(line) for line in data.splitlines() if line.strip()]
    else:
        # First import may bootstrap existing flat JSONL; those originals are never changed.
        if not allow_empty and not (root / 'claims.jsonl').is_file():
            raise ValueError('Store is not initialized')
        if (root / 'claims.jsonl').exists() != (root / 'sources.jsonl').exists():
            raise ValueError('Legacy claims and sources must both exist')
        state = {name: [parse(line) for line in read_bytes(root / (name + '.jsonl')).splitlines() if line.strip()]
                 if (root / (name + '.jsonl')).exists() else [] for name in FILES}
    check_state(state)
    if not locked and ((root / LOCK).exists() or (root / LOCK).is_symlink()):
        raise ValueError('Store changed while reading')
    return state, reference


def validate_intake(intake):
    validate_record(intake, 'feedback-intake')
    if not isinstance(intake, dict) or set(intake) != {'origin', 'sources', 'claims'}:
        raise ValueError('Intake needs origin, sources and claims')
    origin = intake['origin']
    if not isinstance(origin, dict) or set(origin) != {'kind', 'usage_review_ref', 'deidentification_review_ref'}:
        raise ValueError('Explicit origin and review references required')
    if origin['kind'] not in ('conversation_note', 'recording_transcript', 'feedback_document'):
        raise ValueError('Unknown feedback origin')
    if any(not isinstance(origin[key], str) or not origin[key].strip() for key in origin):
        raise ValueError('Missing origin review reference')
    if not isinstance(intake['claims'], list) or not 1 <= len(intake['claims']) <= 5:
        raise ValueError('Feedback intake requires one to five claims')
    if not isinstance(intake['sources'], list) or not 1 <= len(intake['sources']) <= 10:
        raise ValueError('Feedback intake requires one to ten sources')
    for source in intake['sources']:
        validate_record(source, 'source')
        if source['kind'] not in ('human_statement', 'internal_record', 'external_publication') or source['visibility'] != 'restricted':
            raise ValueError('Feedback sources must be restricted, without truth certification')
    for claim in intake['claims']:
        validate_record(claim, 'claim')
        if claim['status'] != 'hypothesis' or claim['visibility'] != 'restricted' or claim['predicate'] not in PREDICATES:
            raise ValueError('Feedback claims must be restricted hypotheses with a supported predicate')
        if not claim['source_refs'] or len(set(claim['source_refs'])) != len(claim['source_refs']):
            raise ValueError('Explicit, distinct feedback source references required')
    for records, key in ((intake['claims'], 'claim_id'), (intake['sources'], 'source_id')):
        if len({row[key] for row in records}) != len(records):
            raise ValueError('Duplicate ID in intake')
    used = {ref for claim in intake['claims'] for ref in claim['source_refs']}
    if not {source['source_id'] for source in intake['sources']} <= used:
        raise ValueError('Unused feedback sources must not be imported')


def validate_proposal(proposal, state):
    validate_record(proposal, 'feedback-proposal')
    required = {'schema_version', 'proposal_id', 'created_at', 'origin', 'sources', 'claims',
                'base_claim_sha256', 'base_source_sha256'}
    if not isinstance(proposal, dict) or set(proposal) != required or proposal['schema_version'] != '0.1':
        raise ValueError('Invalid proposal envelope')
    if not isinstance(proposal['proposal_id'], str) or not proposal['proposal_id'].strip():
        raise ValueError('Proposal ID required')
    timestamp(proposal['created_at'])
    validate_intake({key: proposal[key] for key in ('origin', 'sources', 'claims')})
    for collection, id_key, base_key in (('claims', 'claim_id', 'base_claim_sha256'),
                                          ('sources', 'source_id', 'base_source_sha256')):
        old = {record[id_key]: record for record in state[collection]}
        proposed = proposal[collection]
        bases = proposal[base_key]
        required_ids = ({ref for claim in proposal['claims'] for ref in claim['source_refs']}
                        if collection == 'sources' else {record[id_key] for record in proposed})
        if not isinstance(bases, dict) or set(bases) != required_ids:
            raise ValueError('Complete base snapshot hashes required')
        for record_id in required_ids:
            previous = old.get(record_id)
            if bases[record_id] != (sha(canonical(previous)) if previous else None):
                raise ValueError('Stale proposal; referenced evidence changed')
        for record in proposed:
            previous = old.get(record[id_key])
            if bases[record[id_key]] != (sha(canonical(previous)) if previous else None):
                raise ValueError('Stale proposal; prepare and confirm a new version')
            if collection == 'sources' and previous and record != previous:
                raise ValueError('Existing sources are immutable; use a new source ID')
            if collection == 'claims':
                if record['version'] != (previous['version'] + 1 if previous else 1):
                    raise ValueError('Claim version must advance exactly once')
                if record['updated_at'] != proposal['created_at']:
                    raise ValueError('Claim timestamp must match the reviewed proposal')
                if previous and (previous['status'] != 'hypothesis' or previous['visibility'] != 'restricted'
                                 or previous['subject'] != record['subject'] or previous['predicate'] != record['predicate']
                                 or not set(previous['source_refs']) <= set(record['source_refs'])):
                    raise ValueError('Feedback import cannot promote facts, change identity or remove provenance')
    candidate = deepcopy(state)
    for collection, key in (('claims', 'claim_id'), ('sources', 'source_id')):
        by_id = {record[key]: record for record in candidate[collection]}
        by_id.update({record[key]: record for record in proposal[collection]})
        candidate[collection] = list(by_id.values())
    check_state(candidate)
    return candidate


def write_new(path, data):
    descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def sync_directory(path):
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def prepare(intake_path, store, out, now=None):
    intake = parse(read_bytes(intake_path))
    validate_intake(intake)
    state, reference = read_store(store, allow_empty=True)
    proposal = {'schema_version': '0.1', 'proposal_id': str(uuid.uuid4()), 'created_at': now_string(now), **deepcopy(intake)}
    for collection, key, base in (('claims', 'claim_id', 'base_claim_sha256'), ('sources', 'source_id', 'base_source_sha256')):
        old = {record[key]: record for record in state[collection]}
        required_ids = ({ref for claim in proposal['claims'] for ref in claim['source_refs']}
                        if collection == 'sources' else {record[key] for record in proposal[collection]})
        proposal[base] = {record_id: sha(canonical(old[record_id])) if record_id in old else None
                          for record_id in required_ids}
        if collection == 'claims':
            for record in proposal[collection]:
                record['version'] = old[record[key]]['version'] + 1 if record[key] in old else 1
                record['updated_at'] = proposal['created_at']
                record['tags'] = list(dict.fromkeys(record.get('tags', []) + ['customer_feedback']))
    validate_proposal(proposal, state)
    out = Path(out)
    if LIBRARIES.intersection(out.resolve().parts):
        raise ValueError('Proposal must be outside the methods library')
    data = canonical(proposal)
    if len(data) > MAX_BYTES:
        raise ValueError('Proposal exceeds size limit')
    write_new(out, data)
    return {'status': 'proposed', 'proposal': str(out), 'proposal_sha256': sha(data), 'claims': len(proposal['claims'])}


@contextmanager
def locked_store(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = root / LOCK
    descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink()


def publish(root, state, parent):
    generations = root / 'generations'
    if generations.is_symlink():
        raise ValueError('Symlinked generations directory')
    generations.mkdir(mode=0o700, exist_ok=True)
    generation = 'gen-' + uuid.uuid4().hex
    directory = generations / generation
    directory.mkdir(mode=0o700)
    hashes = {}
    for name in FILES:
        data = b''.join(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8') + b'\n' for record in state[name])
        if len(data) > MAX_BYTES:
            raise ValueError('Store generation exceeds size limit')
        write_new(directory / (name + '.jsonl'), data)
        hashes[name + '.jsonl'] = sha(data)
    manifest = canonical({'schema_version': '0.1', 'parent': parent, 'files': hashes})
    write_new(directory / 'manifest.json', manifest)
    sync_directory(directory)
    sync_directory(generations)
    pointer = {'generation': generation, 'manifest_sha256': sha(manifest)}
    temporary = root / ('CURRENT-' + uuid.uuid4().hex + '.tmp')
    try:
        write_new(temporary, canonical(pointer))
        os.replace(str(temporary), str(root / 'CURRENT.json'))
        sync_directory(root)
    finally:
        if temporary.exists():
            temporary.unlink()
    return pointer


def apply(proposal_path, decision_path, store, harness_authorized=False, now=None):
    if harness_authorized is not True:
        raise ValueError('Current human authorization must be checked by the harness')
    data = read_bytes(proposal_path)
    proposal = parse(data)
    decision = parse(read_bytes(decision_path))
    validate_record(decision, 'decision')
    if (decision['decision'] != 'approved' or decision.get('proposal_sha256') != sha(data)
            or not decision.get('confirmation_ref') or HUMAN.search(decision['decider'])):
        raise ValueError('A matching evidenced human approval is required')
    if not isinstance(proposal, dict) or not isinstance(proposal.get('claims'), list) or not isinstance(proposal.get('sources'), list):
        raise ValueError('Invalid proposal')
    if (set(decision['claim_refs']) != {claim['claim_id'] for claim in proposal['claims']}
            or set(decision.get('source_refs', [])) != {source['source_id'] for source in proposal['sources']}):
        raise ValueError('Decision scope does not match the proposal')
    decided = timestamp(decision['decided_at'])
    if not timestamp(proposal['created_at']) <= decided <= timestamp(now_string(now)):
        raise ValueError('Invalid decision time')
    root = store_path(store)
    with locked_store(root):
        state, reference = read_store(root, allow_empty=True, locked=True)
        previous = next((item for item in state['decisions'] if item.get('proposal_sha256') == sha(data)), None)
        if previous:
            if previous != decision:
                raise ValueError('Proposal was already applied with another decision')
            return {'status': 'already_applied', 'snapshot': reference}
        if any(item['decision_id'] == decision['decision_id'] for item in state['decisions']):
            raise ValueError('Decision ID is already used')
        candidate = validate_proposal(proposal, state)
        old_claims = {item['claim_id']: item for item in state['claims']}
        for claim in proposal['claims']:
            event = {'event_id': str(uuid.uuid4()), 'event_type': 'claim.revised' if claim['claim_id'] in old_claims else 'claim.created',
                     'occurred_at': decision['decided_at'], 'subject_ref': claim['claim_id'], 'actor': decision['decider'],
                     'after_ref': 'proposal-sha256:' + sha(data), 'reason': 'Confirmed external-feedback hypothesis'}
            if claim['claim_id'] in old_claims:
                event['before_ref'] = 'claim-sha256:' + sha(canonical(old_claims[claim['claim_id']]))
            candidate['events'].append(event)
        candidate['decisions'].append(decision)
        candidate['events'].append({'event_id': str(uuid.uuid4()), 'event_type': 'decision.recorded',
                                    'occurred_at': decision['decided_at'], 'subject_ref': decision['decision_id'],
                                    'actor': decision['decider'], 'after_ref': 'proposal-sha256:' + sha(data)})
        check_state(candidate)
        # Keep the exact reviewed proposal and its source origin recoverable, not raw conversations.
        root_archive = root / 'proposals'
        if root_archive.is_symlink():
            raise ValueError('Symlinked proposal archive')
        root_archive.mkdir(mode=0o700, exist_ok=True)
        archived = root_archive / (sha(data) + '.json')
        if archived.exists():
            if read_bytes(archived) != data:
                raise ValueError('Proposal archive collision')
        else:
            write_new(archived, data)
        sync_directory(root_archive)
        reference = publish(root, candidate, reference)
        return {'status': 'applied', 'snapshot': reference, 'claims': len(proposal['claims'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--intake', type=Path, required=True)
    prepare_parser.add_argument('--out', type=Path, required=True)
    prepare_parser.add_argument('--store', type=Path, required=True)
    check_parser = commands.add_parser('check')
    check_parser.add_argument('--proposal', type=Path, required=True)
    check_parser.add_argument('--store', type=Path, required=True)
    apply_parser = commands.add_parser('apply')
    apply_parser.add_argument('--proposal', type=Path, required=True)
    apply_parser.add_argument('--decision', type=Path, required=True)
    apply_parser.add_argument('--store', type=Path, required=True)
    apply_parser.add_argument('--harness-authorized', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            result = prepare(args.intake, args.store, args.out)
        elif args.command == 'check':
            data = read_bytes(args.proposal)
            state, reference = read_store(args.store, allow_empty=True)
            validate_proposal(parse(data), state)
            result = {'status': 'checked', 'proposal_sha256': sha(data), 'snapshot': reference}
        else:
            result = apply(args.proposal, args.decision, args.store, args.harness_authorized)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('FEEDBACK_BLOCKED:', type(error).__name__, 'Vorgang fehlgeschlagen oder Ausgang unklar; Store prüfen, keine neue ID als Wiederholungsumgehung verwenden.', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
