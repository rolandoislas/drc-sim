import construct

header_cmd0 = construct.Struct(
    'magic' / construct.Int8ub,
    'unk_0' / construct.Int8ub,
    'unk_1' / construct.Int8ub,
    'unk_2' / construct.Int8ub,
    'unk_3' / construct.Int8ub,
    'flags' / construct.Int8ub,
    'id_primary' / construct.Int8ub,
    'id_secondary' / construct.Int8ub,
    'error_code' / construct.Int16ub,
    'payload_size_cmd0' / construct.Int16ub
)
header_cmd1 = construct.Struct(
    "f1" / construct.Int8ub,
    "unknown_0" / construct.Int16ub,
    "f3" / construct.Int8ub,
    "mic_enabled" / construct.Int8ub,
    "mic_mute" / construct.Int8ub,
    "mic_volume" / construct.Int16ub,
    "mic_volume_2" / construct.Int16ub,
    "unknown_a" / construct.Int8ub,
    "unknown_b" / construct.Int8ub,
    "mic_freq" / construct.Int16ub,
    "cam_enable" / construct.Int8ub,
    "cam_power" / construct.Int8ub,
    "cam_power_freq" / construct.Int8ub,
    "cam_auto_expo" / construct.Int8ub,
    "cam_expo_abs" / construct.Int32ub,
    "cam_brightness" / construct.Int16ub,
    "cam_contrast" / construct.Int16ub,
    "cam_gain" / construct.Int16ub,
    "cam_hue" / construct.Int16ub,
    "cam_saturation" / construct.Int16ub,
    "cam_sharpness" / construct.Int16ub,
    "cam_gamma" / construct.Int16ub,
    "cam_key_frame" / construct.Int8ub,
    "cam_white_balance_auto" / construct.Int8ub,
    "cam_white_balance" / construct.Int32ub,
    "cam_multiplier" / construct.Int16ub,
    "cam_multiplier_limit" / construct.Int16ub,
    construct.Padding(2)
)
header_cmd2 = construct.Struct(
    'JDN_base' / construct.Int16ul,
    construct.Padding(2),
    'seconds' / construct.Int32ul
)
header = construct.Struct(
    'packet_type' / construct.Int16ul,
    'cmd_id' / construct.Int16ul,
    'payload_size' / construct.Int16ul,
    'seq_id' / construct.Int16ul,
    construct.Embedded(
        construct.Switch(lambda ctx: ctx.cmd_id,
                         {
                             0: construct.If(
                                 lambda ctx: ctx.payload_size >= header_cmd0.sizeof(),
                                 header_cmd0),
                             1: construct.If(
                                 lambda ctx: ctx.payload_size == header_cmd1.sizeof(),
                                 header_cmd1),
                             2: construct.If(
                                 lambda ctx: ctx.payload_size == header_cmd2.sizeof(),
                                 header_cmd2)
                         },
                         default=construct.Pass
                         )
    )
)
