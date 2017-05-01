import construct

header = construct.BitStruct(
    'magic' / construct.Nibble,
    'packet_type' / construct.BitsInteger(2),
    'seq_id' / construct.BitsInteger(10),
    'init' / construct.Flag,
    'frame_begin' / construct.Flag,
    'chunk_end' / construct.Flag,
    'frame_end' / construct.Flag,
    'has_timestamp' / construct.Flag,
    'payload_size' / construct.BitsInteger(11),
    'timestamp' / construct.BitsInteger(32)
)
