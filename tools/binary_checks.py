"""Static signature and chained-fixup validation, adapted from Ning SIMControl."""
import hashlib,plistlib,struct

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def signature(thin, offset, length, require_adhoc=False):
    """Validate CodeDirectory page hashes, including the unmodified helper."""
    blob = thin[offset:offset + length]
    require(len(blob) == length and length >= 12, 'truncated code signature')
    magic, total, count = struct.unpack_from('>III', blob)
    require(magic == 0xfade0cc0 and 12 + 8*count <= total <= length, 'bad signature SuperBlob')
    slots = {}
    for i in range(count):
        slot, pos = struct.unpack_from('>II', blob, 12 + 8*i)
        require(slot not in slots and 12 + 8*count <= pos <= total - 8, 'bad signature index')
        kind, size = struct.unpack_from('>II', blob, pos)
        require(size >= 8 and pos + size <= total, 'signature blob out of range')
        slots[slot] = (kind, blob[pos:pos + size])
    directories = []
    for slot, (kind, cd) in slots.items():
        if slot != 0 and not 0x1000 <= slot <= 0x1005:
            continue
        require(kind == 0xfade0c02 and len(cd) >= 44, 'bad CodeDirectory')
        _, _, version, flags, hashes, ident, special, pages, limit = struct.unpack_from('>9I', cd)
        size, algorithm, _, shift = struct.unpack_from('4B', cd, 36)
        algorithms = {1: ('sha1', 20), 2: ('sha256', 32), 3: ('sha256', 20), 4: ('sha384', 48)}
        require(algorithm in algorithms and size == algorithms[algorithm][1], 'unsupported code hash')
        require(0 < shift <= 16 and 0 < limit <= offset, 'invalid signed range')
        if version >= 0x20300 and len(cd) >= 64:
            require(struct.unpack_from('>Q', cd, 56)[0] in (0, limit), 'unexpected 64-bit code limit')
        page_size = 1 << shift
        require(pages == (limit + page_size - 1)//page_size, 'CodeDirectory page count mismatch')
        require(hashes - special*size >= 44 and hashes + pages*size <= len(cd), 'code hash table out of range')
        require(44 <= ident < len(cd) and b'\0' in cd[ident:], 'missing signing identifier')
        if require_adhoc:
            require(flags & 2, 'module must have its own ad-hoc signature')
        for page in range(pages):
            content = thin[page*page_size:min((page + 1)*page_size, limit)]
            digest = hashlib.new(algorithms[algorithm][0], content).digest()[:size]
            require(digest == cd[hashes + page*size:hashes + (page + 1)*size], 'code page hash mismatch')
        for special_slot in (2, 5, 7):
            if special_slot in slots:
                require(special_slot <= special, 'signature special slot is not hashed')
                digest = hashlib.new(algorithms[algorithm][0], slots[special_slot][1]).digest()[:size]
                require(digest == cd[hashes - special_slot*size:hashes - (special_slot - 1)*size], 'signature special-slot hash mismatch')
        directories.append({'slot': slot, 'identifier': cd[ident:].split(b'\0')[0].decode(),
                            'flags': hex(flags), 'hash_type': algorithm, 'code_pages': pages})
    require(any(item['slot'] == 0 for item in directories), 'missing primary CodeDirectory')
    entitlements = None
    if 5 in slots:
        require(slots[5][0] == 0xfade7171, 'bad XML entitlement blob')
        entitlements = plistlib.loads(slots[5][1][8:])
        require(isinstance(entitlements, dict), 'invalid helper entitlement dictionary')
    return {'sha256': sha256(blob), 'slots': sorted(slots), 'directories': directories,
            'entitlement_keys': sorted(entitlements or {})}

def chained_formats(thin, offset, length, subtype):
    blob = thin[offset:offset + length]
    require(len(blob) == length and length >= 28, 'truncated chained fixups')
    version, starts, imports, symbols, count, import_format, symbol_format = struct.unpack_from('<7I', blob)
    require(version == 0 and 28 <= starts <= length - 4, 'bad chained fixups header')
    require(0 <= imports <= length and 0 <= symbols <= length and symbol_format == 0, 'bad chained data offsets')
    widths = {1: 4, 2: 8, 3: 16}
    require(import_format in widths and imports + count*widths[import_format] <= length, 'bad chained imports table')
    segments = struct.unpack_from('<I', blob, starts)[0]
    require(starts + 4 + 4*segments <= length, 'bad chained segment table')
    formats = set()
    for i in range(segments):
        relative = struct.unpack_from('<I', blob, starts + 4 + 4*i)[0]
        if not relative:
            continue
        pos = starts + relative
        require(starts + 4 + 4*segments <= pos <= length - 22, 'bad chained segment offset')
        size, page_size, pointer_format, _, _, pages = struct.unpack_from('<IHHQIH', blob, pos)
        require(22 + 2*pages <= size and pos + size <= length, 'bad chained page table')
        require(page_size in (4096, 16384), 'unsupported chained page size')
        allowed = {1, 9, 12} if subtype == 0x80000002 else {2, 6}
        require(pointer_format in allowed, f'unsupported iOS 16/17 chained pointer format {pointer_format}')
        formats.add(pointer_format)
    require(formats, 'empty chained fixups')
    return {'formats': sorted(formats), 'import_format': import_format, 'imports': count}
