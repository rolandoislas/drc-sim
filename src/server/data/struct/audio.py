import construct

header_base = construct.BitStruct(
    'fmt' / construct.BitsInteger(3),
    'channel' / construct.Bit,
    'vibrate' / construct.Flag,
    'packet_type' / construct.Bit,
    'seq_id' / construct.BitsInteger(10),
    'payload_size' / construct.BitsInteger(16)
)
header_aud = construct.Struct(
    'timestamp' / construct.Int32ul
)
header_msg = construct.Struct(
    # This is kind of a hack, (there are two timestamp fields, which one is used
    # depends on packet_type
    'timestamp_audio' / construct.Int32ul,
    'timestamp' / construct.Int32ul,
    construct.Array(2, 'freq_0' / construct.Int32ul),  # -> mc_video
    construct.Array(2, 'freq_1' / construct.Int32ul),  # -> mc_sync
    'vid_format' / construct.Int8ub,
    construct.Padding(3)
)
header = construct.Struct(
    construct.Embedded(header_base),
    construct.Embedded(
        construct.Switch(lambda ctx: ctx.packet_type,
                         {
                             0: header_aud,
                             1: header_msg
                         },
                         default=construct.Pass
                         )
    )
)
